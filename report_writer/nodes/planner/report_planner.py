"""
Report planning nodes for generating and managing report structure.
"""
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import Send
from langgraph.types import interrupt, Command
from report_writer import planner_llm, planner_query_writer, gemini_flash

from report_writer.state import ReportState, Sections, Queries, HybridQueries
from report_writer.utils import perform_internal_knowledge_search, perform_web_search
from .prompt import (
    report_planner_query_writer_instructions_only_web_search,
    report_planner_instructions_only_web_search,
    report_planner_query_writer_instructions_hybrid_rag,
    report_planner_instructions_hybrid_rag,
    report_planner_query_writer_instructions_only_web_search_feedback,
    report_planner_query_writer_instructions_hybrid_rag_feedback,
    rewrite_report_plan_instructions
)

from logger import runner_logger as logger


async def retrieve_query_responses(query_list, mode):
    """Retrieve responses for the given search queries."""
    if mode == "hybrid_rag": 
        internal_query_list = [query.search_query for query in query_list.internal_search_queries]
        web_query_list = [query.search_query for query in query_list.web_search_queries]
        if len(internal_query_list) > 0:
            internal_search_results = await perform_internal_knowledge_search(internal_query_list, "dipak")
        else:
            internal_search_results = "No new internal search queries generated"
        if len(web_query_list) > 0:
            web_search_results, _ = perform_web_search(web_query_list)
        else:
            web_search_results = "No new web search queries generated"
        return {"internal_search_results": internal_search_results, "web_search_results": web_search_results}
    else:
        query_list = [query.search_query for query in query_list.queries]
        if len(query_list) > 0:
            search_results , _ = perform_web_search(query_list)
        else:
            search_results = "No new web search queries generated"
        return {"web_search_results": search_results}

async def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the initial report plan with sections."""
    topic = state["topic"]
    report_structure = config["configurable"]["report_structure"]
    number_of_queries = config["configurable"]["number_of_queries"]
    mode = config["configurable"]["mode"]
    logger.info(f"Generating report plan for topic: {topic}")
    logger.info(f"Report structure: {report_structure}")
    logger.info(f"Number of queries: {number_of_queries}")
    logger.info(f"Mode: {mode}")

    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    if mode == "hybrid_rag":
        structured_llm = gemini_flash.with_structured_output(HybridQueries)
        system_instructions_query = report_planner_query_writer_instructions_hybrid_rag.format(
            topic=topic, 
            report_organization=report_structure, 
            number_of_queries=number_of_queries,
            internal_documents=state["internal_documents"]
        )
    else:
        structured_llm = gemini_flash.with_structured_output(Queries)
        system_instructions_query = report_planner_query_writer_instructions_only_web_search.format(
            topic=topic, 
            report_organization=report_structure, 
            number_of_queries=number_of_queries
        )

    logger.info("Calling structured llm for query generation")
    results = structured_llm.invoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="Generate search queries that will help with planning the sections of the report.")
    ])
    logger.info(f"Generated search queries: {results}")
    query_results = await retrieve_query_responses(results, mode)
    

    if mode == "hybrid_rag":
        source_str = query_results["internal_search_results"] +"\n\n"+ query_results["web_search_results"]
        system_instructions_sections = report_planner_instructions_hybrid_rag.format(
            topic=topic, 
            report_organization=report_structure, 
            context=source_str
        )
    else:
        source_str = query_results["web_search_results"]
        system_instructions_sections = report_planner_instructions_only_web_search.format(
            topic=topic, 
            report_organization=report_structure, 
            context=source_str
        )
    logger.info(f"Source string: {source_str}")

    # Report planner instructions
    planner_message = """Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. 
                        Each section must have: name, description, research, internal_search, and content fields."""

    structured_llm = planner_llm.with_structured_output(Sections)
    report_sections = structured_llm.invoke([
        SystemMessage(content=system_instructions_sections),
        HumanMessage(content=planner_message)
    ])
    logger.info(f"Generated report sections: {report_sections}")
    if mode != "hybrid_rag":
        for section in report_sections.sections:
            section.internal_search = False

    return {"sections": report_sections.sections, "plan_context": source_str, "description": report_sections.description}

async def rewrite_report_plan(state: ReportState, config: RunnableConfig): 
    topic = state["topic"]
    sections = state['sections']
    mode = config["configurable"]["mode"]
    feedback = state["feedback_on_report_plan"]
    plan_context = state["plan_context"]
    sections_str = "\n\n".join(
        f"Section: {section.name}\n"
        f"Description: {section.description}\n"
        f"Online Research needed: {'Yes' if section.research else 'No'}\n"
        f"Internal Research needed: {'Yes' if section.internal_search else 'No'}\n"
        for section in sections
    )

    if mode == "hybrid_rag":
        structured_llm = planner_query_writer.with_structured_output(HybridQueries)
        system_instructions_query = report_planner_query_writer_instructions_hybrid_rag_feedback.format(
            topic=topic, 
            report_organization=config["configurable"]["report_structure"], 
            number_of_queries=config["configurable"]["number_of_queries"],
            internal_documents=state["internal_documents"],
            sections=sections_str,
            feedback=feedback
        )
    else:
        structured_llm = planner_query_writer.with_structured_output(Queries)
        system_instructions_query = report_planner_query_writer_instructions_only_web_search_feedback.format(
            topic=topic, 
            report_organization=config["configurable"]["report_structure"], 
            number_of_queries=config["configurable"]["number_of_queries"],
            sections=sections_str,
            feedback=feedback
        )

    results = structured_llm.invoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="Regenerate search queries that will help with planning the sections of the report based on the feedback. Only generate queries if needed. Do not generate queries that cover the same topics as the current report plan. Do not generate unnecessary queries or duplicates.")
    ])
    logger.info(f"Generated search queries after feedback: {results}")
    query_results = await retrieve_query_responses(results, mode)

    if mode == "hybrid_rag":
        source_str = query_results["internal_search_results"] +"\n\n"+ query_results["web_search_results"]
    else:
        source_str = query_results["web_search_results"]

    structured_llm = planner_llm.with_structured_output(Sections)
    system_instructions = rewrite_report_plan_instructions.format(
            topic=topic,
            report_organization=config["configurable"]["report_structure"],
            context=plan_context,
            sections=sections_str,
            feedback=feedback,
            new_context=source_str
        )
    report_sections = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Rewrite the report plan based on the feedback.")
    ])

    return {"sections": report_sections.sections, "description": report_sections.description}

def human_feedback(state: ReportState) -> Command[Literal["rewrite_report_plan", "build_section_with_research"]]:
    """Get human feedback on the report plan and route to next steps."""
    topic = state["topic"]
    sections = state['sections']

    interrupt_message = sections
    logger.info(f"Creating report plan: Human feedback request")
    feedback = interrupt(interrupt_message)
    logger.info(f"Human feedback response: {feedback}")

    if isinstance(feedback, bool) and feedback is True:
        return Command(goto=[
            Send("build_section_with_research", {"topic": topic, "section": s, "internal_documents": state["internal_documents"], "search_iterations": 0}) 
            for s in sections 
            if s.research or s.internal_search
        ])
    elif isinstance(feedback, str):
        return Command(goto="rewrite_report_plan", update={"feedback_on_report_plan": feedback})
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")
