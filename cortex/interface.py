import os
import datetime
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from zone import gemini_flash
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from cortex.state import WorkflowMessage, ToolExecution
from logger import agent_logger as logger
from services.workflow import WorkflowService, Workflow
from .graph import cortex
from typing import Annotated
from pydantic import Field
from langchain_core.messages import AIMessage

workflow_task = Annotated[str, Field(description="Detailed instructions for financial research workflow")]
workflow_name = Annotated[str, Field(description="Give a 4-5 word name to the workflow")]
@tool(return_direct=True)
async def workflow_tool(task: workflow_task, name: workflow_name, config : RunnableConfig):
    """Execute a financial research workflow based on the provided task description.
    
    Args:
        task: Detailed instructions for the financial research workflow
        config: Configuration for the workflow execution
        
    Returns:
        List of workflow messages generated during execution
    """
    workflow_id = config["configurable"]["workflow_id"]
    workflow_service = WorkflowService()
    workflow = workflow_service.get_workflow_by_id(workflow_id)
    workflow.name = name
    workflow_service.update_workflow(workflow)
    print(f"Workflow {workflow_id} updated with name {name}")
    inputs = {"input": task}
    config["recursion_limit"] = 50
    
    async for event in cortex.astream(inputs, config=config, stream_mode="custom"):
        for k, v in event.items():
            pass
    return f"Workflow completed"

workflow_agent_prompt = (
    "You are a conversational assistant designed to help users initiate financial research workflows.\n\n"

    "🛠 You only have access to: `workflow_tool`\n"
    "However, you are aware that `workflow_tool` can internally use the following tools to carry out detailed financial research:\n"
    "- analyze_balance_sheet\n"
    "- analyze_cash_flow\n"
    "- analyze_income_stmt\n"
    "- analyze_segment_stmt\n"
    "- income_summarization\n"
    "- get_risk_assessment\n"
    "- get_competitors_analysis\n"
    "- report_writer_tool\n\n"

    "🎯 Your responsibilities:\n"
    "1. Engage in natural conversation to identify whether the user wants to conduct **financial research on a company or stock**.\n"
    "2. Ask for missing but critical details only if not already provided:\n"
    "   - ✅ Ticker symbol of the company\n"
    "   - ✅ Fiscal year (fyear) to analyze\n"
    "   - Optional: list of competitors\n"
    "3. Once you have ticker and fyear, prepare a structured instruction and call the `workflow_tool`.\n"
    "4. Do **not** over-ask; if required info is already present, proceed directly.\n"
    "5. The instruction passed to `workflow_tool` **must always include the ticker symbol and fyear**.\n"
    "6. Format your workflow call like this:\n\n"

    "### Example Workflow Call:\n\n"
    "With the tools you've been provided, write an annual report based on Tesla's (TSLA) and Rivian's (RIVN) 2024 10-K reports, formatted into markdown.\n\n"
    "Pay attention to the following:\n"
    "- Use tools one by one for clarity, especially when asking for instructions.\n"
    "- Discuss how Tesla’s performance across these metrics justifies or contradicts its current market valuation (e.g., EV/EBITDA).\n"
    "- Each paragraph on the first page (Business Overview, Market Position, Operating Results) should be 150–160 words.\n"
    "- Each paragraph on the second page (Risk Assessment, Competitor Analysis) should be 500–600 words.\n"
    "- Generate a detailed, markdown-formatted annual report comprising: Business Overview, Market Position, Operating Results, Risk Assessment, and Competitor Analysis.\n"

    "✅ After triggering the workflow, inform the user that the task has been initiated and summarize what will be done.\n"
    "Be helpful, keep the flow casual, and assist users in kicking off high-quality financial research tasks."
    
    "Current Date and Time: {current_date_time}"
)

PROMPT = workflow_agent_prompt

async def run_maestro(inputs, config, workflow: Workflow, workflow_service: WorkflowService):
    """Run the Maestro agent and stream results asynchronously.
    
    Args:
        inputs: Input messages or text for the agent
        config: Configuration for the agent
        
    Yields:
        Chunks of data from the agent's execution
    """
    async with AsyncMongoDBSaver.from_conn_string(os.getenv("MONGODB_URI")) as checkpointer:
        maestro = create_react_agent(
                        model=gemini_flash,
                        tools=[workflow_tool],
                        prompt=SystemMessage(PROMPT.format(current_date_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
                        checkpointer=checkpointer,
                    )
        last_message = None
        message_type = None
        tool_execution = None  
        tool_calls = []
        current_task = None
        messages = workflow.messages
        async for _, chunk in maestro.astream(
            {"messages": [{"role": "user", "content": inputs.get('input', str(inputs))}]},
            config,
            stream_mode=["updates", "custom"],
        ):
            # Process and yield each chunk as it comes
            # Check if chunk is a dictionary (not a tuple)
            print("\nChunk:")
            print(chunk)
            print(type(chunk))
            if "agent" in chunk:
                last_message = chunk["agent"]["messages"][-1]  # Update with the latest content
                
                if last_message is None:
                    continue
                    
                if isinstance(last_message, AIMessage):
                    yield {"event": "complete", "is_cortex_output": True, "content": last_message.content}
                else:
                    yield {"event": "message", "is_cortex_output": False, "content": last_message.content}
                
            elif isinstance(chunk, dict):
                # Handle tuple case (likely a key-value pair)
                for k, v in chunk.items():
                    print(f"Key: {k}, Value: {v}")
                    if k != "__end__":
                        if k == "status":
                            if v == "Reasoning":
                                message_type = "instructor"
                            elif v == "Working":
                                message_type = "executor"
                            yield {"event": "status", "status": v}
                        elif k == "instructor_update":
                            message = WorkflowMessage(type=message_type, content=v, task=None, tool_execution=None)
                            messages.append(message)
                            yield {"event": "message", "type": message_type, "content": v}
                        elif k == "executor_task":
                            tool_calls = []
                            current_task = v
                        elif k == "tool_status":
                            tool_execution = ToolExecution(status=v, type="financial_tool", tool_output=None)
                            # yield {"event": "tool_status", "status": v}
                        elif k == "tool_output":
                            tool_execution.tool_output = v
                            tool_calls.append(tool_execution)
                        elif k == "writer_output":
                            tool_execution.type = "writing_tool"
                            tool_execution.tool_output = v
                            tool_calls.append(tool_execution)
                        elif k == "executor_update":
                            message = WorkflowMessage(type=message_type, content=v, task=current_task, tool_execution=tool_calls)
                            messages.append(message)
                            yield {"event": "message", "type": message_type, "content": v, "task": current_task, "tool_execution": [instance.model_dump() for instance in tool_calls]}

                logger.info(f"{k} - {v}")
                workflow.messages = messages
                workflow = workflow_service.update_workflow(workflow)
        
