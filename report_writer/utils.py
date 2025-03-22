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
    if not queries:
        logger.warning("No search queries provided to perform_web_search")
        return "No search queries were provided."
        
    try:
        for query in queries:
            if not query or not isinstance(query, str):
                logger.warning(f"Invalid query type or empty query: {type(query)}")
                subquery_results[str(query)] = "Invalid search query format."
                continue
                
            logger.info(f"Performing web search for query: {query}")
            search_result = google_search(query)
            
            # Check if the search result indicates an error
            if search_result and (search_result.startswith("Error:") or 
                               search_result.startswith("An error occurred")):
                logger.warning(f"Search error for query '{query}': {search_result}")
            
            subquery_results[query] = search_result
            
        reasoning_text = create_reasoning_text_web(subquery_results)
        return reasoning_text
    except Exception as e:
        logger.error(f"Error in perform_web_search: {str(e)}")
        return f"An error occurred during web search: {str(e)}. Please try again later."

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
