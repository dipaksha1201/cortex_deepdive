from typing import List
from report_writer.graph import run_deepdive, run_section_builder
import asyncio
from logger import runner_logger as logger
from services.document import DocumentService
from report_writer.utils import format_documents
from langgraph.types import Command
from report_writer.model import DeepResearch
from report_writer.graph import get_completed_sections
from report_writer.service import generate_report_metadata

DEFAULT_REPORT_STRUCTURE = """Use this structure to create a report on the user-provided topic:

1. Introduction (no research needed)
   - Brief overview of the topic area

2. Main Body Sections:
   - Each section should focus on a sub-topic of the user-provided topic
   
3. Conclusion
   - Aim for 1 structural element (either a list of table) that distills the main body sections 
   - Provide a concise summary of the report"""

def get_internal_documents(user_id: str):
    document_service = DocumentService()
    documents = document_service.get_user_documents(user_id)
    return format_documents(documents) 

def get_config(user_id: str, project_id: str, report_id: str):
    return {"configurable": {"user_id": user_id, "project_id": project_id, "thread_id": report_id, "report_structure": DEFAULT_REPORT_STRUCTURE, "number_of_queries": 3, "mode": "hybrid_rag", "max_search_iterations": 3, "max_follow_up_queries": 3, "max_section_words": 500}}

async def start_planner(user_id: str, project_id: str, topic: str, report_id: str):
    internal_documents = get_internal_documents(user_id)
    input = {"topic": topic, "internal_documents": internal_documents}
    config = get_config(user_id, project_id, report_id)
    plan = await run_deepdive(input, config)
    return plan

async def continue_research(user_id: str, project_id: str, report_id: str, data: str | bool):
    input = Command(resume=data)
    config = get_config(user_id, project_id, report_id)
    response = await run_deepdive(input, config)
    print("Response:", response)
    if isinstance(response, str):
        print("Response is a string")
        list_of_sources = []
        researcher = DeepResearch()
        researcher.id = report_id  
        completed_sections = await get_completed_sections(config)
        for section in completed_sections: 
            section_sources = {}
            section_sources["section_name"] = section.name
            section_sources["sources"] = section.sources
            list_of_sources.append(section_sources)

        unique_types = DeepResearch.get_unique_types_by_user_id(user_id)
        metadata = generate_report_metadata(response, unique_types)
        # Use the combined update method to perform a single database operation
        researcher.update_report_completion(
            report=response,
            sources=list_of_sources,
            metadata=metadata,
            status="completed"
        )
        return response
    else:
        print("Response is not a string")
        plan = response["rewrite_report_plan"]["sections"]
        description = response["rewrite_report_plan"]["description"]
        plan_dicts = [section.model_dump() for section in plan]
        result = {
            "report_id": report_id,
            "plan": plan_dicts,
            "type": "plan",
            "description": description,
            "topic" : "Same"
        }
        return result