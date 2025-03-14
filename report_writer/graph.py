from langgraph.graph import START, END, StateGraph
from report_writer.state import (
    ReportStateInput,
    ReportStateOutput,
    ReportState,
    SectionState,
    SectionOutputState,
)
from .nodes.planner.report_planner import generate_report_plan, human_feedback, rewrite_report_plan
from .nodes.writer.section_writer import generate_queries, search_web, search_internal, write_section, direct_research  
from .nodes.compiler.report_compiler import gather_completed_sections, write_final_sections, compile_final_report, initiate_final_section_writing
    

# Add nodes 
section_builder = StateGraph(SectionState, output=SectionOutputState)
section_builder.add_node("generate_queries", generate_queries)
section_builder.add_node("search_web", search_web)
section_builder.add_node("search_internal", search_internal)
section_builder.add_node("write_section", write_section)

# Add edges
section_builder.add_edge(START, "generate_queries")
section_builder.add_conditional_edges("generate_queries", direct_research, ["search_web", "search_internal"])
section_builder.add_edge("search_web", "write_section")
section_builder.add_edge("search_internal", "write_section")

# Outer graph for initial report plan compiling results from each section -- 

# Add nodes
builder = StateGraph(ReportState, input=ReportStateInput, output=ReportStateOutput)
builder.add_node("generate_report_plan", generate_report_plan)
builder.add_node("human_feedback", human_feedback)
builder.add_node("rewrite_report_plan", rewrite_report_plan)
builder.add_node("build_section_with_research", section_builder.compile())
builder.add_node("gather_completed_sections", gather_completed_sections)
builder.add_node("write_final_sections", write_final_sections)
builder.add_node("compile_final_report", compile_final_report)

# Add edges
builder.add_edge(START, "generate_report_plan")
builder.add_edge("generate_report_plan", "human_feedback")
builder.add_edge("rewrite_report_plan", "human_feedback")
builder.add_edge("build_section_with_research", "gather_completed_sections")
builder.add_conditional_edges("gather_completed_sections", initiate_final_section_writing, ["write_final_sections"])
builder.add_edge("write_final_sections", "compile_final_report")
builder.add_edge("compile_final_report", END)

graph = builder.compile()