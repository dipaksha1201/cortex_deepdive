from langgraph.graph import START, END, StateGraph
from report_writer.state import (
    ReportStateInput,
    ReportStateOutput,
    ReportState,
    SectionState,
    SectionOutputState,
)
from .nodes.planner.report_planner import generate_report_plan, human_feedback, rewrite_report_plan
from .nodes.writer.section_writer import generate_queries, search_web, write_section, perform_research
from .nodes.compiler.report_compiler import gather_completed_sections, write_final_sections, compile_final_report, initiate_final_section_writing
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver   
import os
from logger import cortex_logger as logger 
# Add nodes 
section_builder = StateGraph(SectionState, output=SectionOutputState)
section_builder.add_node("generate_queries", generate_queries)
section_builder.add_node("search_web", search_web)
section_builder.add_node("write_section", write_section)
section_builder.add_node("perform_research", perform_research)

# Add edges
section_builder.add_edge(START, "generate_queries")
section_builder.add_edge("generate_queries", "perform_research")
section_builder.add_edge("perform_research", "write_section")
section_builder.add_edge("search_web", "write_section")

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

async def run_deepdive(input, config):
    async with AsyncMongoDBSaver.from_conn_string(os.getenv("MONGODB_URI")) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        final_result = None
        # Use streaming mode "updates" to capture intermediate events (including interrupts)
        async for event in graph.astream(input, config, stream_mode="updates"):
            logger.info("Graph event:", str(event))
            # If an interrupt event is present, you can capture its payload:
            if "__interrupt__" in event:
                interrupt_payload = event["__interrupt__"]
                print("Interrupt encountered:", interrupt_payload)
                # Optionally, you can decide to break or resume the graph using a Command.
                # For now, we'll break out of the stream.
                break
            if "compile_final_report" in event:
                event = event["compile_final_report"]["final_report"]
            # Optionally, if the event represents a final result, store it.
            # (The final event may include a key like "final_result" or simply be the last state.)
            final_result = event

        return final_result

async def get_completed_sections(config):
    async with AsyncMongoDBSaver.from_conn_string(os.getenv("MONGODB_URI")) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        state = await graph.aget_state(config=config)
        return state.values["sections"]
        
async def run_section_builder(input, config):
    async with AsyncMongoDBSaver.from_conn_string(os.getenv("MONGODB_URI")) as checkpointer:
        graph = section_builder.compile(checkpointer=checkpointer)
        result = await graph.ainvoke(input, config)
        return result