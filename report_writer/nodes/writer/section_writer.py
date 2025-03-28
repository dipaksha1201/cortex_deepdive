"""
Section writing nodes for generating and managing individual report sections.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from report_writer import planner_query_writer, gemini_pro
from report_writer.state import SectionState, Queries, Feedback, SectionWriter
from report_writer.graph import END
from report_writer.utils import perform_web_search, perform_internal_knowledge_search
from .prompt import (
    query_writer_instructions_internal,
    query_writer_instructions_web,
    section_writer_instructions,
    section_grader_instructions,
    section_writer_inputs
)
from logger import runner_logger as logger

async def perform_research(state: SectionState, config: RunnableConfig):
    search_iterations = state["search_iterations"]
    user_id = config["configurable"]["user_id"]
    project_id = config["configurable"]["project_id"]
    
    logger.info(f"Performing research for section: {state['section'].name}")
    logger.info(f"Search queries: {state['search_queries']}")
    logger.info(f"Internal search queries: {state['internal_search_queries']}")
    
    # Initialize variables before conditional blocks
    search_response = ""
    internal_search_response = ""
    error_messages = []
    search_sources = []
    
    # Perform web search if queries exist
    if "search_queries" in state and len(state["search_queries"]) > 0:
        try:
            search_response, search_sources = perform_web_search(state["search_queries"])           
            # Check if the search response indicates an error
            if search_response and (search_response.startswith("Error:") or 
                                search_response.startswith("An error occurred")):
                error_message = f"Web search error: {search_response}"
                logger.warning(error_message)
                error_messages.append(error_message)
                # Provide a fallback message for the section writer
                search_response = "Web search could not be completed. Please rely on internal knowledge or proceed with limited information."
        except Exception as e:
            error_message = f"Exception during web search: {str(e)}"
            logger.error(error_message)
            error_messages.append(error_message)
            search_response = "Web search encountered an error. Please proceed with available information."
    
    # Perform internal search if queries exist
    if "internal_search_queries" in state and len(state["internal_search_queries"]) > 0:
        try:
            internal_search_response = await perform_internal_knowledge_search(state["internal_search_queries"], user_id, project_id)
            
            # Check if internal search response is empty or indicates an error
            if not internal_search_response or (isinstance(internal_search_response, str) and 
                                            (internal_search_response.startswith("Error:") or 
                                             internal_search_response.startswith("An error occurred"))):
                error_message = f"Internal search error or empty result: {internal_search_response}"
                logger.warning(error_message)
                error_messages.append(error_message)
                internal_search_response = "Internal knowledge search could not be completed. Please rely on web search or proceed with limited information."
        except Exception as e:
            error_message = f"Exception during internal search: {str(e)}"
            logger.error(error_message)
            error_messages.append(error_message)
            internal_search_response = "Internal knowledge search encountered an error. Please proceed with available information."
    
    # If both searches failed, add a note to the section content
    if error_messages and not search_response and not internal_search_response:
        section = state["section"]
        if not section.content:
            section.content = ""
        section.content += "\n\nNote: Research for this section encountered technical difficulties. The content is based on limited information."
        
    return {
        "search_results": search_response,
        "internal_search_results": internal_search_response,
        "search_iterations": search_iterations + 1,
        "search_sources": search_sources
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
    search_results, search_sources = perform_web_search(queries)
    return {
        "search_results": search_results,
        "search_iterations": search_iterations + 1,
        "search_sources": search_sources
    }

async def write_section(state: SectionState, config: RunnableConfig):
    """Write a section of the report and evaluate if more research is needed."""
    topic = state["topic"]
    section = state["section"]
    search_results = state["search_results"]
    search_sources = state["search_sources"]
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
    section_writer = gemini_pro.with_structured_output(SectionWriter)
    section_content = section_writer.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content=section_writer_inputs_formatted)
    ])

    section.content = section_content.content
    sources = [s.model_dump() for s in section_content.sources]
    for source in sources:
        if "sources" in source:
            source_refs = source["sources"]
            for s in source_refs:
                if "title" in s:
                    title = s["title"]
                    for ref in search_sources:
                        if "title" in ref and ref["title"] == title:
                            if "uri" in ref:  # Check if search API returns "uri" instead of "url"
                                s["url"] = ref["uri"]
                            elif "url" in ref:
                                s["url"] = ref["url"]
    
    section.sources = sources

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
        return  Command(
            update={"search_queries": feedback.follow_up_queries, "section": section},
            goto="search_web"
            )

