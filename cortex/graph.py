from langgraph.graph import END
from langgraph.graph import StateGraph, START
from cortex.executor import run_executor, planner, replanner
from cortex.state import PlanExecute
from cortex.state import Plan
from langchain_core.runnables import RunnableConfig
from logger import runner_logger as logger
from langgraph.config import get_stream_writer

async def execute_step(state: PlanExecute, config: RunnableConfig):
    writer = get_stream_writer()
    writer({"status" : "Working"})
    plan = state["plan"]
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    
    writer({"executor_task" : task})
    
    # Format past_steps in a more readable way
    past_steps_formatted = ""
    if state["past_steps"]:
        past_steps_list = []
        for past_task, past_response in state["past_steps"]:
            past_steps_list.append(f"Step: {past_task}\nResponse: {past_response}")
        past_steps_formatted = "\n\n".join(past_steps_list)
    
    task_formatted = f"""For the following plan:
                        {plan_str}\n\nYou are tasked with executing step {1}, 
                        {task}. Refer the past actions to populate any required information for calling the tools.
                        ## PAST ACTIONS
                        {past_steps_formatted}\n\n
                        """
    

    response = await run_executor(task_formatted, config)
    writer({"executor_update" : response})
    
    print("\n")  # Add a newline after streaming completes
    
    return {
        "past_steps": [(task, response)],
    }


async def plan_step(state: PlanExecute):
    print("Planning...")
    plan = [   "Step 1: Analyze Companies 2024 financials using the following tool:\n- `analyze_balance_sheet`",
    
    "Step 2: Analyze Companies 2024 financials using the following tool:\n- `analyze_cash_flow`\n- ",
    
    "Step 3: Analyze Companies 2024 financials using the following tool:\n- `analyze_income_stmt`\n",
    "Step 4: Analyze Companies 2024 financials using the following tool:\n- `analyze_segment_stmt`\n",
    "Step 5: Analyze Companies 2024 financials using the following tool:\n- `income_summarization`\n",
    
    "Step 6: Use `get_competitors_analysis` to compare financial metrics between the requested companies. Only use data from the financial metrics table for competitor analysis. Remove duplicate or similar sentences elsewhere.",
    
    "Step 7: Use `get_risk_assessment` to extract the top 3 risks identified in Companies 10-K report.",
    
    "Step 8: Write three paragraphs (150–160 words each) for:\n- Business Overview\n- Market Position\n- Operating Results \n using insights from Steps 2 and 3.",
    
    "Step 9: Write two paragraphs (500–600 words each) for:\n- Risk Assessment (based on Step 4)\n- Competitors Analysis (only using the financial metrics table per instructions)",
    
    "Step 10: Generate Detailed report with appropriate markdown formatting using all the data collected and analyzed in the past steps with the following sections:\n- Business Overview\n- Market Position\n- Operating Results\n",
    ]
    plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    plan = await planner.ainvoke({"objective": state["input"], "plan": plan_text}) 
    print(plan)
    print("\n------------\n")
    return {"plan": plan.steps}
    # return {"plan": ["Analyze GOOGL's 2024 balance sheet"]}


async def replan_step(state: PlanExecute):
    writer = get_stream_writer()
    writer({"status" : "Reasoning"})
    output = await replanner.ainvoke(state)
    writer({"instructor_update" : output.update})
    if len(output.plan) == 0:
        return {"response": output.update}
    return {"plan": output.plan}


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"

workflow = StateGraph(PlanExecute)

# Add the plan node
workflow.add_node("planner", plan_step)

# Add the execution step
workflow.add_node("agent", execute_step)

# Add a replan node
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")

# From plan we go to agent
workflow.add_edge("planner", "agent")

# From agent, we replan
workflow.add_edge("agent", "replan")

workflow.add_conditional_edges(
    "replan",
    # Next, we pass in the function that will determine which node is called next.
    should_end,
    ["agent", END],
)

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
cortex = workflow.compile()

__all__ = ["cortex"]