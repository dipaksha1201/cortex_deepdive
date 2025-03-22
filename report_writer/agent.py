from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from services.research import start_planner
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver   
from report_writer import gemini_flash
from langchain_core.messages import SystemMessage
import os
import datetime
from logger import agent_logger as logger
from report_writer.model import DeepResearch
from typing import Annotated
from pydantic import Field
from typing import Dict, List
from langchain_core.messages import ToolMessage
import json

PROMPT = """
You are Cortex, a specialized React-based AI agent designed exclusively for initiating structured research using the integrated tool called "Deep Research." Your primary objective is to assist the user in clearly drafting a research topic, refining it into a concise, actionable query, and then passing it directly to the Deep Research tool.
Guidelines for Interaction:
Topic Refinement:
Help the user precisely define and narrow down the research topic.
Ensure the topic is clear, focused, and suitable for deep, thorough investigation.
Topic should not be more than 6 words.
Tool Utilization:
Once a topic is clearly defined, initiate research immediately by sending it to the Deep Research tool.
User Direction:
If the user deviates from defining or refining a research topic, gently but firmly guide them back to topic formulation.
Clearly remind the user that your sole responsibility is facilitating and initiating research through topic refinement and submission to Deep Research.
Example Interaction:
User: "Can you help me with React best practices?"
Cortex: "Let's refine this into a clear research topic. For instance, 'Current best practices in state management for React applications.' Should I proceed with this research topic?"
User: "Tell me about something unrelated."
Cortex: "My role is specifically to help you define and initiate research topics using Deep Research. Please provide a topic you'd like to research or refine one together."

Refer messages in conversation for context.

Current Date and Time: {current_date_time}
"""

ResearchTopic = Annotated[str, Field(description="Draft a research topic")]

@tool(return_direct=True)
async def search(topic: ResearchTopic, config: RunnableConfig) -> str:
    """
    Initiates research by sending a topic to the Deep Research tool.
    Returns a JSON serialized string.
    """
    try:
        logger.info(f"Starting search for topic: {topic}")
        user_id = config["configurable"]["user_id"]
        project_id = config["configurable"]["project_id"]
        researcher = DeepResearch()
        researcher.create_report(user_id, project_id, topic)
        report_id = researcher.id
        response = await start_planner(user_id, project_id, topic, report_id)
        print("Deep research plan Response:", response)
        plan = response["generate_report_plan"]["sections"]
        description = response["generate_report_plan"]["description"]
        plan_dicts = [section.model_dump() for section in plan]
        researcher.update_plan(plan_dicts, description)
        researcher.update_status("in_planning")

        result = {
            "report_id": report_id,
            "plan": plan_dicts,
            "type": "plan",
            "conversation_id": config["configurable"]["thread_id"],
            "description": description,
            "topic": topic
        }

        return json.dumps(result)  # Serialize to JSON string explicitly

    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return json.dumps({"error": "There was an error while calling the Deep Research tool try again later: " + str(e)})

async def run_deepdive(inputs, config):
    async with AsyncMongoDBSaver.from_conn_string(os.getenv("MONGODB_URI")) as checkpointer:
            cortex = create_react_agent(
                        model=gemini_flash,
                        tools=[search],
                        prompt=SystemMessage(PROMPT.format(current_date_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
                        checkpointer=checkpointer,
                    )

            response = await cortex.ainvoke(inputs, config)
            last_message = response["messages"][-1] 
            print("Response:", last_message)
            if isinstance(last_message, ToolMessage):
                if "error" in last_message.content:
                    response = await cortex.ainvoke(inputs, config)
                else:
                    return json.loads(last_message.content)

            return {"reply": response["messages"][-1].content, "type": "cortex", "conversation_id": config["configurable"]["thread_id"]}

