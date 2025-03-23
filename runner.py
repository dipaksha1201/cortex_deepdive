from report_writer.graph import run_deepdive, run_section_builder
import asyncio
from logger import runner_logger as logger
from services.document import DocumentService
from report_writer.utils import format_documents
from report_writer.state import Section
from report_writer.search import google_search
from report_writer.model import DeepResearch

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

def run_section_builder_test():
    internal_documents = get_internal_documents("dipak")
    section = Section(name="Amazon Stock Performance Analysis", description="Brief overview of the topic area", research=True, internal_search=True, content="", sources="")
    input = {"topic": "A comparative analysis of Amazon's stock performance in the last 3 months", "internal_documents": internal_documents, "section": section, "search_iterations": 0}
    config = {"configurable": {"user_id": "dipak", "thread_id": "20-deepdive", "report_structure": DEFAULT_REPORT_STRUCTURE, "number_of_queries": 3, "mode": "hybrid_rag", "max_search_iterations": 3, "max_follow_up_queries": 3}}
    result = asyncio.run(run_section_builder(input, config))
    logger.info(f"Section builder result: {result}")

def run_get_unique_types_by_user_id():
    unique_types = DeepResearch.get_unique_types_by_user_id("dipak")
    logger.info(f"Unique types: {unique_types}")

def run():
    logger.info("Starting deepdive...")
    internal_documents = get_internal_documents("dipak")
    input = {"topic": "A comparative analysis to predict the performance of stocks in the next 3 months for apple and amazon", "internal_documents": internal_documents}
   #  input = Command(resume="add a new section for upcoming product offering analysis")
    # input = Command(resume=True)

    config = {"configurable": {"user_id": "dipak-122", "thread_id": "19-deepdive", "report_structure": DEFAULT_REPORT_STRUCTURE, "number_of_queries": 3, "mode": "hybrid_rag", "max_search_iterations": 3, "max_follow_up_queries": 3}}
    output = asyncio.run(run_deepdive(input, config))    
    logger.info(f"Deepdive output: \n{output}")

def run_search():
    print("Starting search...")
    response = google_search("What is the current price of Amazon stock?")
    print(response)    

if __name__ == "__main__":
    # run_search()
    # run_section_builder_test()
    run_get_unique_types_by_user_id()
    # run()
