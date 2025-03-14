"""
Report planning nodes for generating and managing report structure.
"""
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import Send
from langgraph.types import interrupt, Command
from report_writer import planner_llm, planner_query_writer

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


async def retrieve_query_responses(query_list, mode):
    """Retrieve responses for the given search queries."""
    if mode == "hybrid_rag":    
        internal_search_results = await perform_internal_knowledge_search(query_list.internal_search_queries)
        web_search_results = await perform_web_search(query_list.web_search_queries)
        return {"internal_search_results": internal_search_results, "web_search_results": web_search_results}
    else:
        query_list = [query.search_query for query in query_list.queries]
        search_results = await perform_web_search(query_list)
        return {"web_search_results": search_results}

async def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the initial report plan with sections."""
    topic = state["topic"]
    report_structure = config["report_structure"]
    number_of_queries = config["number_of_queries"]
    mode = config["mode"]

    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    if mode == "hybrid_rag":
        structured_llm = planner_query_writer.with_structured_output(HybridQueries)
        system_instructions_query = report_planner_query_writer_instructions_hybrid_rag.format(
            topic=topic, 
            report_organization=report_structure, 
            number_of_queries=number_of_queries,
            internal_documents=state["internal_documents"]
        )
    else:
        structured_llm = planner_query_writer.with_structured_output(Queries)
        system_instructions_query = report_planner_query_writer_instructions_only_web_search.format(
            topic=topic, 
            report_organization=report_structure, 
            number_of_queries=number_of_queries
        )

    results = structured_llm.invoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="Generate search queries that will help with planning the sections of the report.")
    ])

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

    # Report planner instructions
    planner_message = """Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. 
                        Each section must have: name, description, plan, research, internal_search, and content fields."""

    structured_llm = planner_llm.with_structured_output(Sections)
    report_sections = structured_llm.invoke([
        SystemMessage(content=system_instructions_sections),
        HumanMessage(content=planner_message)
    ])

    if mode != "hybrid_rag":
        for section in report_sections.sections:
            section.internal_search = False

    return {"sections": report_sections.sections}

async def rewrite_report_plan(state: ReportState, config: RunnableConfig): 
    topic = state["topic"]
    sections = state['sections']
    mode = config["mode"]
    feedback = state["feedback_on_report_plan"]
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
            report_organization=config["report_structure"], 
            number_of_queries=config["number_of_queries"],
            internal_documents=state["internal_documents"],
            sections=sections_str,
            feedback=feedback
        )
    else:
        structured_llm = planner_query_writer.with_structured_output(Queries)
        system_instructions_query = report_planner_query_writer_instructions_only_web_search_feedback.format(
            topic=topic, 
            report_organization=config["report_structure"], 
            number_of_queries=config["number_of_queries"],
            sections=sections_str,
            feedback=feedback
        )

    results = structured_llm.invoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="Regenerate search queries that will help with planning the sections of the report based on the feedback. Only generate queries if needed. Do not generate queries that cover the same topics as the current report plan. Do not generate unnecessary queries or duplicates.")
    ])
    query_results = await retrieve_query_responses(results, mode)

    if mode == "hybrid_rag":
        source_str = query_results["internal_search_results"] +"\n\n"+ query_results["web_search_results"]
    else:
        source_str = query_results["web_search_results"]

    structured_llm = planner_llm.with_structured_output(Sections)
    system_instructions = rewrite_report_plan_instructions.format(
            topic=topic,
            report_organization=config["report_structure"],
            context=source_str,
            sections=sections_str,
            feedback=feedback
        )
    report_sections = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Rewrite the report plan based on the feedback.")
    ])

    return {"sections": report_sections.sections}

def human_feedback(state: ReportState) -> Command[Literal["rewrite_report_plan", "build_section_with_web_research"]]:
    """Get human feedback on the report plan and route to next steps."""
    topic = state["topic"]
    sections = state['sections']
    sections_str = "\n\n".join(
        f"Section: {section.name}\n"
        f"Description: {section.description}\n"
        f"Online Research needed: {'Yes' if section.research else 'No'}\n"
        f"Internal Research needed: {'Yes' if section.internal_search else 'No'}\n"
        for section in sections
    )

    interrupt_message = f"""Please provide feedback on the following report plan. 
                        \n\n{sections_str}\n
                        \nDoes the report plan meet your needs?\nPass 'true' to approve the report plan.\nOr, provide feedback to regenerate the report plan:"""
    
    feedback = interrupt(interrupt_message)

    if isinstance(feedback, bool) and feedback is True:
        return Command(goto=[
            Send("build_section_with_research", {"topic": topic, "section": s, "search_iterations": 0}) 
            for s in sections 
            if s.research or s.internal_search
        ])
    elif isinstance(feedback, str):
        return Command(goto="rewrite_report_plan", update={"feedback_on_report_plan": feedback})
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")
