from langgraph.prebuilt import create_react_agent
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from cortex.state import Plan, Act
from zone.utilities import FmpUtils
from dotenv import load_dotenv
from langchain_core.messages import ToolMessage , AIMessage
from typing import Annotated
from pydantic import Field
from langchain_core.tools import tool
from report_writer.search import google_search
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from zone.tools.financial_analysis_tools import analyze_balance_sheet, analyze_cash_flow, analyze_income_stmt, analyze_segment_stmt, income_summarization, get_risk_assessment, get_competitors_analysis, get_key_data

load_dotenv()

def get_gemini(model):
    llm = ChatGoogleGenerativeAI(model=model, google_api_key = os.getenv("GEMINI_API_KEY_BETA"))
    return llm

gemini_flash = get_gemini("gemini-2.0-flash")
gemini_pro = get_gemini("gemini-2.5-pro-preview-03-25")

GoogleSearchQuery = Annotated[str, Field(description="A relevant query to search the internet for relevant information")]

@tool   
async def internet_search(query: GoogleSearchQuery):
    """Search the internet for the query."""
    return google_search(query) 

async def run_executor(task, config):
    # Choose the LLM that will drive the agent
    prompt = ("You are a helpful assistant. You have access to the following tools: "
              "`FmpUtils.get_sec_report`, `analyze_balance_sheet`, `analyze_cash_flow`, "
              "`analyze_income_stmt`, `analyze_segment_stmt`, `income_summarization`, "
            #   "`get_risk_assessment`, `get_competitors_analysis`, `get_key_data` when given a task "
              "use the tools mentioned above as per the instructions. "
              
              "IMPORTANT: Do not call a single tool more than once. Each tool should be called EXACTLY ONCE. "
              "Keep track of which tools you have already called. "
              "When you call FmpUtils.get_sec_report, call it ONCE with ALL tickers in a single call. "
              "After you get the results, move to the next step in the plan. "
              
              "Stop when you have completed the task. "
              "If the tool returns an instruction follow the instruction and return the result. "
              "When finished, end with 'Task complete' and a summary of what you found.")
    
    # Set a custom config with reduced recursion limit and appropriate settings
    agent_config = {
        "recursion_limit": 30,  # Lower recursion limit to fail faster if it loops
        "tool_usage": {
            "max_per_tool": 1  # Limit to 1 call per tool
        }
    }
    
    # Update config with user-provided config
    if config:
        agent_config.update(config)
    
    async with AsyncMongoDBSaver.from_conn_string(os.getenv("MONGODB_URI")) as checkpointer:
        agent_executor = create_react_agent(
            gemini_flash,
            [
                analyze_balance_sheet,
                analyze_cash_flow,
                analyze_income_stmt,
                analyze_segment_stmt,
                income_summarization,
                get_risk_assessment,
                get_competitors_analysis,
            ],
            prompt=prompt,
            checkpointer=checkpointer
        )
        
        try:
            last_message = None
            # Note: Setting stream_mode to "custom" lets your tools stream custom data.
            async for mode,  chunk in agent_executor.astream(
                {"messages": [{"role": "user", "content": task}]},
                config,
                stream_mode=["messages","custom"
                ],
            ):
                # if mode == "messages":
                if "messages" in chunk:
                    last_message = chunk["messages"][-1]  # Update with the latest content
                    # elif mode == "custom":
                    #     print("Custom Data:", chunk)
            
            if last_message is None:
                raise ValueError("No message was streamed from the agent.")
            return last_message.content
        
        except Exception as e:
            error_message = f"Error during execution: {str(e)}"
            print(f"\n{error_message}")
            return error_message

planner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
            This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
            The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps. create and refer the rough plan to get the context and convert it into a plan. Strictly follow the given plan and update it and come up with the updated plan for the given user objective.
            
        ## Plan to implement ###
        {plan}
        
        ## Objective ###
        {objective}
    """
)

planner = planner_prompt | gemini_flash.with_structured_output(Plan)

replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
You are a replanner assistant. You will be given the original plan and the steps that have already been completed. You have access to the tools provided in the prompt. You just have to update the plan based on the steps that have already been completed.
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. 
Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan. 

If you have completed the task, use Response. Dont use Plan if you have completed the task. Dont use Plan and create new plan if goal is met."""
)


replanner = replanner_prompt | gemini_pro.with_structured_output(Act)

__all__ = ["gemini_flash", "gemini_pro", "run_executor", "planner", "replanner"]
