"""
Report compilation nodes for combining sections and generating the final report.
"""
from typing import Dict, List
from langgraph.constants import Send
from langgraph.types import Command

from report_writer.state import ReportState, SectionState, SectionOutputState
from report_writer.state import Section
from report_writer import report_writer_llm
from langchain_core.messages import HumanMessage, SystemMessage
from report_writer.nodes.compiler.prompt import final_section_writer_instructions

def format_sections(sections: list[Section]) -> str:
    """ Format a list of sections into a string """
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
    {'='*60}
    Section {idx}: {section.name}
    {'='*60}
    Description:
    {section.description}
    Requires Research: 
    {section.research}

    Content:
    {section.content if section.content else '[Not yet written]'}

    """
    return formatted_str

def gather_completed_sections(state: ReportState):
    """Format completed sections as context for writing final sections.
    
    This node takes all completed research sections and formats them into
    a single context string for writing summary sections.
    
    Args:
        state: Current state with completed sections
        
    Returns:
        Dict with formatted sections as context
    """

    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    completed_report_sections = format_sections(completed_sections)

    return {"report_sections_from_research": completed_report_sections}

def initiate_final_section_writing(state: ReportState):
    """Create parallel tasks for writing non-research sections.
    
    This edge function identifies sections that don't need research and
    creates parallel writing tasks for each one.
    
    Args:
        state: Current state with all sections and research context
        
    Returns:
        List of Send commands for parallel section writing
    """

    # Kick off section writing in parallel via Send() API for any sections that do not require research
    return [
        Send("write_final_sections", {"topic": state["topic"], "section": s, "report_sections_from_research": state["report_sections_from_research"]}) 
        for s in state["sections"] 
        if not s.research and not s.internal_search
    ]

async def write_final_sections(state: SectionState):
    """Write sections that don't require research using completed sections as context."""
    topic = state["topic"]
    section = state["section"]
    context = state.get("report_sections_from_research", "")
    
    system_instructions = final_section_writer_instructions.format(
        topic=topic,
        section_name=section.name,
        section_description=section.description,
        context=context
    )
    
    section_content = report_writer_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate a report section based on the provided sources.")
    ])
    section.content = section_content
    return {"completed_sections": [section]}

def compile_final_report(state: ReportState):
    """Compile all sections into the final report.
    
    This node:
    1. Gets all completed sections
    2. Orders them according to original plan
    3. Combines them into the final report
    
    Args:
        state: Current state with all completed sections
        
    Returns:
        Dict containing the complete report
    """

    # Get sections
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}

    # Update sections with completed content while maintaining original order
    for section in sections:
        section.content = completed_sections[section.name]

    # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])

    return {"final_report": all_sections}