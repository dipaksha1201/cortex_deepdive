from report_writer.service import retrieve_subqueries
from report_writer.search import google_search
from logger import runner_logger as logger
"""Utility classes and functions for the report writer."""

async def perform_internal_knowledge_search(queries, user_id: str): 
    subquery_results = []
    async for output in retrieve_subqueries(queries, user_id):
        # Yield each piece of the response to stream downstream
        subquery_results.append(output)
    reasoning_text = create_reasoning_text(subquery_results)
    return reasoning_text

def perform_web_search(queries): 
    subquery_results = {}
    all_sources = []
    for query in queries:
        search_result = google_search(query)
        
        # Handle different return types from google_search
        if isinstance(search_result, tuple) and len(search_result) == 2:
            # Normal case: (result, sources)
            result, source = search_result
            subquery_results[query] = result
            all_sources.extend(source)
        else:
            # Error case: string
            subquery_results[query] = search_result if isinstance(search_result, str) else str(search_result)
            logger.warning(f"Google search for query '{query}' did not return sources")
    
    # Create a list of unique sources based on title
    unique_sources = []
    unique_titles = set()
    for source in all_sources:
        if source.get("title") and source["title"] not in unique_titles:
            unique_sources.append(source)
            unique_titles.add(source["title"])
            
    reasoning_text = create_reasoning_text_web(subquery_results)

    return reasoning_text, unique_sources

def create_reasoning_text_web(subquery_results) -> str:
    reasoning_steps = []
    for query, response in subquery_results.items():
        reasoning_steps.append("---------------SUB-QUERY-ONLINE---------------")
        reasoning_steps.append(query)
        reasoning_steps.append("---------------SUB-QUERY RESPONSE---------------")
        reasoning_steps.append(response)

    return "\n".join(reasoning_steps)

def create_reasoning_text(subquery_results) -> str:
    reasoning_steps = []
    for response in subquery_results:
        if response["type"] == "response":
            reasoning_steps.append("---------------SUB-QUERY---------------")
            reasoning_steps.append(response["query"])
            reasoning_steps.append("---------------SUB-QUERY RESPONSE---------------")
            reasoning_steps.append(response["response"])

    return "\n".join(reasoning_steps)


def format_documents(documents):
    formatted_string = ""
    for index, document in enumerate(documents, start=1):
        formatted_string += f"########Document {index}#########\n"
        formatted_string += f"Name: {document.name}\n"
        formatted_string += f"Type: {document.document_type}\n"
        formatted_string += f"Domain: {document.domain}\n"
        formatted_string += f"Description: {document.description}\n\n"
        formatted_string += f"#########################################\n\n"
    return formatted_string
