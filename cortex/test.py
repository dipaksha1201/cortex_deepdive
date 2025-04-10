import asyncio
from cortex.graph import cortex
from textwrap import dedent
from logger import cortex_logger as logger
from cortex.state import WorkflowMessage, ToolExecution
from services.workflow import WorkflowService, Workflow
from dotenv import load_dotenv
load_dotenv()

config = { "configurable": { "thread_id": "cortex-11222"}, "recursion_limit": 50 }
# work_dir = "/content/cortex/report"
company = "AAPL"
competitors = ["MSFT"]
fyear = "2024"

task = dedent(
    f"""
    With the tools you've been provided, write an annual report based on {company}'s and{competitors}'s{fyear} 10-k report, format it into a markdown.
    Pay attention to the followings:
    - Use tools one by one for clarity, especially when asking for instructions.
    - Discuss how {company}’s performance over these years and across these metrics might justify or contradict its current market valuation (as reflected in the EV/EBITDA ratio).
    - Each paragraph in the first page(business overview, market position and operating results) should be between 150 and 160 words, each paragraph in the second page(risk assessment and competitors analysis) should be between 500 and 600 words, don't generate the markdown until this is explicitly fulfilled.
"""
)

task = dedent(
    f"""
    With the tools you've been provided, write a report based on AAPL's 2024 balance sheet and cash flow. Analyse balance sheet and cash flow and give your findings.
    """
)

inputs = {"input": task}

async def main():
    message_type = None
    messages = []
    tool_execution = None  
    tool_calls = []
    current_task = None
    workflow_service = WorkflowService()
    workflow = None
    
    async for event in cortex.astream(inputs, config=config, stream_mode="custom"):
        for k, v in event.items():
            if k != "__end__":
                if k == "status":
                    if v == "Reasoning":
                        message_type = "instructor"
                    elif v == "Working":
                        message_type = "executor"
                elif k == "instructor_update":
                    message = WorkflowMessage(type=message_type, content=v, task=None, tool_execution=None)
                    messages.append(message)
                elif k == "executor_task":
                    tool_calls = []
                    current_task = v
                elif k == "tool_status":
                    tool_execution = ToolExecution(status=v, type="financial_tool", tool_output=None)
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

                logger.info(f"{k} - {v}")
                
                # Create or update workflow after each event
                if workflow is None:
                    workflow = Workflow(user_id="dev", name="test workflow", messages=messages)
                    workflow = workflow_service.insert_workflow(workflow)
                else:
                    # Update the workflow with the latest messages
                    workflow.messages = messages
                    workflow = workflow_service.update_workflow(workflow)
    
    # Final update if workflow exists
    if workflow:
        logger.info(f"Final workflow update with {len(messages)} messages")
        workflow_service.update_workflow(workflow)

if __name__ == "__main__":
    asyncio.run(main())