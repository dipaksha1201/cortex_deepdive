"""
Section writing nodes for generating and managing individual report sections.
"""
from typing import List
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from report_writer import planner_query_writer
from report_writer.state import SectionState, Queries, Feedback
from report_writer.graph import END
from report_writer import report_writer_llm
from report_writer.utils import perform_web_search, perform_internal_knowledge_search
from .prompt import (
    query_writer_instructions_internal,
    query_writer_instructions_web,
    section_writer_instructions,
    section_grader_instructions,
    section_writer_inputs
)
from logger import runner_logger as logger

async def perform_research(state: SectionState):
    search_iterations = state["search_iterations"]
    logger.info(f"Performing research for section: {state['section'].name}")
    
    if "search_queries" in state and len(state["search_queries"]) > 0:
        search_response = perform_web_search(state["search_queries"])
    
    if "internal_search_queries" in state and len(state["internal_search_queries"]) > 0:
        internal_search_response = await perform_internal_knowledge_search(state["internal_search_queries"], "dipak")
    
    return {
        "search_results": search_response or "",
        "internal_search_results": internal_search_response or "",
        "search_iterations": search_iterations + 1
    }
    
async def generate_queries(state: SectionState, config: RunnableConfig):
    """Generate search queries for researching a specific section."""
    topic = state["topic"]
    section = state["section"]
    number_of_queries = config["configurable"]["number_of_queries"]
    search_queries = []
    internal_search_queries = []
    structured_llm = planner_query_writer.with_structured_output(Queries)
    if section.internal_search:
        system_instructions = query_writer_instructions_internal.format(
            topic=topic,
            section_topic=section.name,
            internal_documents=state["internal_documents"],
            number_of_queries=number_of_queries
        )
        results = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries for this section.")
    ])
        internal_search_queries = [query.search_query for query in results.queries]
    
    if section.research:
        system_instructions = query_writer_instructions_web.format(
            topic=topic,
            section_topic=section.name,
            number_of_queries=number_of_queries
        )
        results = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Generate search queries for this section.")
        ])
        search_queries = [query.search_query for query in results.queries]

    return {"search_queries": search_queries, "internal_search_queries": internal_search_queries}

def search_web(state: SectionState):
    """Execute web searches for the section queries."""
    queries = state["search_queries"]
    search_iterations = state["search_iterations"]
    queries = [query.search_query for query in queries]
    search_results = perform_web_search(queries)
    return {
        "search_results": search_results,
        "search_iterations": search_iterations + 1
    }

async def write_section(state: SectionState, config: RunnableConfig):
    """Write a section of the report and evaluate if more research is needed."""
    topic = state["topic"]
    section = state["section"]
    search_results = state["search_results"]
    internal_search_results = state["internal_search_results"]
    search_iterations = state["search_iterations"]
    max_search_iterations = config["configurable"]["max_search_iterations"]
    max_follow_up_queries = config["configurable"]["max_follow_up_queries"]

    section_writer_inputs_formatted = section_writer_inputs.format(topic=topic, 
                                                             section_name=section.name, 
                                                             section_topic=section.description, 
                                                             context=search_results, 
                                                             internal_context=internal_search_results, 
                                                             section_content=section.content)
    
    system_instructions = section_writer_instructions
    section_content = report_writer_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content=section_writer_inputs_formatted)
    ])

    section.content = section_content.content

    section_grader_message = ("Grade the report and consider follow-up questions for missing information. "
                              "If the grade is 'pass', return empty strings for all follow-up queries. "
                              "If the grade is 'fail', provide specific search queries to gather missing information.")
    
    grader_instructions = section_grader_instructions.format(
        topic=topic,
        section_topic=section.description,
        section=section_content,
        number_of_follow_up_queries=max_follow_up_queries
    )
    model = planner_query_writer.with_structured_output(Feedback)
    feedback = model.invoke([
        SystemMessage(content=grader_instructions),
        HumanMessage(content=section_grader_message)
    ])

    # If the section is passing or the max search depth is reached, publish the section to completed sections 
    if feedback.grade == "pass" or search_iterations >= max_search_iterations:
        # Publish the section to completed sections 
        logger.info(f"Publishing section to completed sections: \n {section}")
        return  Command(
        update={"completed_sections": [section]},
        goto=END
    )

    # Update the existing section with new content and update search queries
    else:
        return  Command(
            update={"search_queries": feedback.follow_up_queries, "section": section},
            goto="search_web"
            )

