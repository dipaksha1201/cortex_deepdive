"""
Section writing nodes for generating and managing individual report sections.
"""
from typing import List
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import Send
from langgraph.types import Command
from report_writer import planner_query_writer
from report_writer.state import SectionState, Queries, Feedback
from report_writer.graph import END
from report_writer import report_writer_llm
from report_writer.utils import perform_web_search, perform_internal_knowledge_search
from .prompt import (
    query_writer_instructions_web,
    query_writer_instructions_internal,
    section_writer_instructions_web,
    section_writer_instructions_internal,
    section_grader_instructions,
    section_writer_inputs
)

def direct_research(state: SectionState):
    if state["section"].internal_search:
        return "search_internal"
    else:
        return "search_web"
    
async def generate_queries(state: SectionState, config: RunnableConfig):
    """Generate search queries for researching a specific section."""
    topic = state["topic"]
    section = state["section"]
    number_of_queries = config["number_of_queries"]
    structured_llm = planner_query_writer.with_structured_output(Queries)
    if section.internal_search:
        system_instructions = query_writer_instructions_internal.format(
            topic=topic,
            section_topic=section.name,
            internal_documents=state["internal_documents"],
            number_of_queries=number_of_queries
        )
    else:
        system_instructions = query_writer_instructions_web.format(
            topic=topic,
            section_topic=section.name,
            number_of_queries=number_of_queries
        )
    
    results = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries for this section.")
    ])
    
    return {"search_queries": [query.search_query for query in results.queries]}

async def search_internal(state: SectionState, config: RunnableConfig):
    """Execute internal knowledge searches for the section queries."""
    queries = state["search_queries"]
    search_iterations = state["search_iterations"]
    search_results = await perform_internal_knowledge_search(queries)
    
    return {
        "search_results": search_results,
        "search_iterations": search_iterations + 1
    }

async def search_web(state: SectionState, config: RunnableConfig):
    """Execute web searches for the section queries."""
    queries = state["search_queries"]
    search_iterations = state["search_iterations"]
    search_results = await perform_web_search(queries)
    
    return {
        "search_results": search_results,
        "search_iterations": search_iterations + 1
    }

async def write_section(state: SectionState, config: RunnableConfig):
    """Write a section of the report and evaluate if more research is needed."""
    topic = state["topic"]
    section = state["section"]
    search_results = state["search_results"]
    search_iterations = state["search_iterations"]
    max_search_iterations = config["max_search_iterations"]
    max_follow_up_queries = config["max_follow_up_queries"]

    section_writer_inputs_formatted = section_writer_inputs.format(topic=topic, 
                                                             section_name=section.name, 
                                                             section_topic=section.description, 
                                                             context=search_results, 
                                                             section_content=section.content)
    
    if section.internal_search:
        system_instructions = section_writer_instructions_internal
    else:
        system_instructions = section_writer_instructions_web
    
    section_content = report_writer_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content=section_writer_inputs_formatted)
    ])

    section.content = section_content

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
        return  Command(
        update={"completed_sections": [section]},
        goto=END
    )

    # Update the existing section with new content and update search queries
    else:
        if section.internal_search:
            return  Command(
            update={"search_queries": feedback.follow_up_queries, "section": section},
            goto="search_internal"
            )
        else:
            return  Command(
            update={"search_queries": feedback.follow_up_queries, "section": section},
            goto="search_web"
            )

