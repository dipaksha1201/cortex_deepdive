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
from zone.tools.writing_tools import report_writer_tool

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
    prompt = (
    "You are a focused and capable assistant designed to complete structured tasks using a fixed set of tools.\n\n"
    "You have access to the following tools:\n"
    "- analyze_balance_sheet\n"
    "- analyze_cash_flow\n"
    "- analyze_income_stmt\n"
    "- analyze_segment_stmt\n"
    "- income_summarization\n"
    "- get_risk_assessment\n"
    "- get_competitors_analysis\n"
    "- report_writer_tool\n\n"

    "Instructions:\n"
    "1. Use the tools exactly as needed to complete the task—**no more, no less**.\n"
    "2. ⚠️ **Call each tool only once. Never reuse a tool.**\n"
    "3. Track which tools you’ve already used.\n"
    "4. If a tool returns an instruction, follow it and return the result.\n"
    "5. Always use `report_writer_tool` when writing or summarizing any insights.\n"
    "6. Stop when the task is fully complete.\n"
    "7. End with `Task complete.` followed by a summary of what you found.\n\n"
    "8. Never reply with more than 100 words.\n"
    
    "Think carefully. Be efficient. Complete the task with precision."
)
    
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
                report_writer_tool
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
    """
    For the given objective, generate a precise, step-by-step plan that clearly specifies the actions required to achieve the objective. Each step should be distinct, actionable, and self-contained, providing all necessary context and details without superfluous information. Ensure each step logically follows from the previous one, ultimately leading directly to the final desired outcome.

    The agent has access to the following tools:
    - analyze_balance_sheet
    - analyze_cash_flow
    - analyze_income_stmt
    - analyze_segment_stmt
    - income_summarization
    - get_risk_assessment
    - get_competitors_analysis
    - report_writer_tool

    ⚠️ Important:
    - You must create and refer to a rough plan to build context.
    - Then convert it into a structured, executable plan.
    - Strictly follow and update the plan based on the objective.
    - The final step in the plan **must** be a writing task using `report_writer_tool`.

    ## Example ##

    User Instruction:
    With the tools you've been provided, write an annual report based on Apple's and Microsoft's 2024 10-K report, formatted in markdown.

    Pay attention to the following:
    - Use tools sequentially for clarity, particularly when requesting instructions.
    - Discuss how Apple’s historical performance across provided metrics might support or contradict its current market valuation (as indicated by the EV/EBITDA ratio).
    - Paragraph lengths must strictly follow these constraints:
    - Page 1 (Business Overview, Market Position, Operating Results): 150–160 words each.
    - Page 2 (Risk Assessment, Competitor Analysis): 500–600 words each.
    - Do not generate markdown until explicitly instructed to do so.

    Plan structure:
    Step 1: Analyze Apple and Microsoft’s 2024 financials using the tool: analyze_balance_sheet.  
    Step 2: Analyze Apple and Microsoft’s 2024 financials using the tool: analyze_cash_flow.  
    Step 3: Analyze Apple and Microsoft’s 2024 financials using the tool: analyze_income_stmt.  
    Step 4: Analyze Apple and Microsoft’s 2024 financials using the tool: analyze_segment_stmt.  
    Step 5: Summarize Apple’s income insights using the tool: income_summarization.  
    Step 6: Conduct competitor analysis with get_competitors_analysis. Compare financial metrics exclusively from the provided table, removing redundancy.  
    Step 7: Identify and extract the top 3 risks from Apple’s 10-K report using get_risk_assessment.  
    Step 8: Draft three distinct paragraphs (150–160 words each) covering:  
    - Business Overview  
    - Market Position  
    - Operating Results  
    using insights from Steps 2 and 3 with report_writer_tool.  
    Step 9: Draft two paragraphs (500–600 words each) covering:  
    - Risk Assessment (from Step 7)  
    - Competitor Analysis (financial metrics only)  
    using report_writer_tool.  
    Step 10: Generate a detailed, markdown-formatted annual report comprising:  
    - Business Overview  
    - Market Position  
    - Operating Results  
    - Risk Assessment  
    - Competitor Analysis  
    Leverage all previous analyses and complete this using report_writer_tool.

    ## Objective ##
    {objective}
    """
)

planner = planner_prompt | gemini_flash.with_structured_output(Plan)

replanner_prompt = ChatPromptTemplate.from_template(
    """
    You are a replanner assistant.

        Your task is to intelligently update the original plan based on what has already been completed. You will receive:
        - An objective
        - The original plan
        - A list of steps already completed

        You also have access to the following tools:
        - analyze_balance_sheet
        - analyze_cash_flow
        - analyze_income_stmt
        - analyze_segment_stmt
        - income_summarization
        - get_risk_assessment
        - get_competitors_analysis
        - report_writer_tool

        ### Your responsibilities:
        - Remove all completed steps from the original plan.
        - Return **only the remaining steps** required to fulfill the objective.
        - The plan must consist of minimal, precise, self-contained steps.
        - If no replanning is needed, return `plan: []`
        - In **all cases**, include an `update:` field with a short summary of your decision and next action.

        if replanning is needed - Each step should be distinct, actionable, and self-contained, providing all necessary context and details without superfluous information. Ensure each step logically follows from the previous one, ultimately leading directly to the final desired outcome.

        ⚠️ Final writing tasks should always end with `report_writer_tool` if applicable.

        ---

        ### Input

        **Objective:**  
        {input}

        **Original Plan:**  
        {plan}

        **Completed Steps:**  
        {past_steps}

        ---

        ### Output Format

        You must return two keys:
        - `plan`: the updated list of remaining steps  
        - `update`: a brief explanation of what you decided and why

        ---

        ### Example

        **Objective:** Write a summary comparing Netflix and Disney’s 2024 income statements.  
        **Original Plan:**
        1. Analyze Netflix income using analyze_income_stmt  
        2. Analyze Disney income using analyze_income_stmt  
        3. Compare profitability using get_competitors_analysis  
        4. Write summary using report_writer_tool

        **Completed Steps:**
        1. Analyze Netflix income using analyze_income_stmt  
        2. Analyze Disney income using analyze_income_stmt 

        **Expected Output:**
        plan - "Compare profitability using get_competitors_analysis", "Write summary using report_writer_tool"
        update - "analysis of income statements of both companies completed. Proceeding to competitor analysis next, followed by report writing."

        Never return an empty plan with steps remaining to be completed. 
    """
)


replanner = replanner_prompt | gemini_pro.with_structured_output(Act)

__all__ = ["gemini_flash", "gemini_pro", "run_executor", "planner", "replanner"]
