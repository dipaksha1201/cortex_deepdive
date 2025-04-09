from zone.prompts import PROMPTS
from langgraph.graph import END, StateGraph, START
from zone.state import SearchQueries, SearchResultsGrade, SubCsvComposer
from langchain_core.runnables import RunnableConfig
from zone import gemini_pro, gemini_flash
from report_writer.search import google_search
from logger import runner_logger as logger
from langchain_core.output_parsers import JsonOutputParser
from langgraph.types import Command
from zone.utils import create_search_response_text

def generate_subqueries(user_request: str, index_column: str, data_columns: list[str]):
    prompt = PROMPTS["generate_search_queries"].format(user_request=user_request, index_column=index_column, data_columns=data_columns)
    response = gemini_flash.with_structured_output(SearchQueries).invoke(prompt)
    return {"subqueries": response.search_queries}

def perform_search(subqueries: list[str]):
    results = []
    instructions = "## Search Instructions## Give the most relevant information first, specifically look for requested data points and provide the precise data points requested."
    for subquery in subqueries:
        response = {}
        response["query"] = subquery
        response["response"] = google_search(subquery, with_sources=False, prompt=instructions)
        results.append(response)
    
    reasoning_text = create_search_response_text(results)
    return {"search_results": reasoning_text}

def process_search_results(user_request: str, search_queries: list[str], search_result: str, index_column: str, data_columns: list[str]):
    prompt = PROMPTS["process_search_results"].format(user_request=user_request, search_queries=search_queries, search_result=search_result, index_column=index_column, data_columns=data_columns)
    response = gemini_pro.invoke(prompt)
    parser = JsonOutputParser()
    return {"extracted_values": parser.parse(response.content)}

def search(state: SubCsvComposer):
    results = []
    for subquery in state.search_queries:
        response = {}
        response["query"] = subquery
        response["response"] = google_search(subquery, with_sources=False)
        results.append(response)
    
    reasoning_text = create_search_response_text(results)
    return {"search_results": reasoning_text}

def grade_search_results(state: SubCsvComposer, config: RunnableConfig):
    max_iterations = config["configurable"]["max_rectifier_iterations"]
    prompt = PROMPTS["grading_prompt"].format(user_request=state.user_request, search_queries=state.search_queries, search_results=state.search_results, extracted_values=state.extracted_values)
    response = gemini_flash.with_structured_output(SearchResultsGrade).invoke(prompt)
    logger.info(f"Search Results Grade: {response.grade} - {response.reason}\n")
    if response.grade == "FAIL" and state.search_iteration < max_iterations:
        logger.info(f"Search iteration {state.search_iteration +1} failed. Generating revised search queries...\n")
        return Command(
            update={"grade": response.grade, "reason": response.reason, "search_iteration": state.search_iteration + 1},
            goto="generate_revised_search_queries"
        )

    # Update the existing section with new content and update search queries
    else:
        return  Command(
            update={"grade": response.grade, "reason": response.reason},
            goto=END
            )

def generate_revised_search_queries(state: SubCsvComposer):
    prompt = PROMPTS["rewrite_search_queries"].format(original_search_queries=state.search_queries, extracted_values=state.extracted_values, search_results=state.search_results, grading_reason=state.reason)
    response = gemini_flash.with_structured_output(SearchQueries).invoke(prompt)
    logger.info(f"Revised Search Queries: {response.search_queries}\n")
    return {"revised_search_queries": response.search_queries}

def update_json(state: SubCsvComposer):
    prompt = PROMPTS["update_json"].format(index_column=state.index_column, data_columns=state.data_columns, extracted_values=state.extracted_values, new_search_result=state.search_results, grading_reason=state.reason)
    response = gemini_pro.invoke(prompt)
    parser = JsonOutputParser()
    logger.info(f"Updated JSON: {parser.parse(response.content)}\n")
    return {"extracted_values": parser.parse(response.content)}

csv_rectifier = StateGraph(SubCsvComposer)

csv_rectifier.add_node("generate_revised_search_queries", generate_revised_search_queries)
csv_rectifier.add_node("search", search)
csv_rectifier.add_node("process_search_results", update_json)
csv_rectifier.add_node("grade_search_results", grade_search_results)

csv_rectifier.add_edge(START, "grade_search_results")
csv_rectifier.add_edge("generate_revised_search_queries", "search")
csv_rectifier.add_edge("search", "process_search_results")
csv_rectifier.add_edge("process_search_results", "grade_search_results")

rectifier = csv_rectifier.compile()

def main():
    # Prompt for the agent's query
    query = "Extract these data points for Apple for2021, 2022,  2023 and 2024"
    index_column = "Year"
    data_columns = ["Revenue", "Operating Income", "Depreciation", "CapEx", "Change in Working Capital", "Tax Rate (%)"]
    
    # Initialize the result dictionary
    result = {}
    
    # Generate subqueries
    subqueries_result = generate_subqueries(query, index_column, data_columns)
    result.update(subqueries_result)  # Add subqueries to result
    logger.info(f"Subqueries: {result['subqueries']}\n")
    
    # Perform search
    search_result = perform_search(result["subqueries"])
    result.update(search_result)  # Add search results to result
    logger.info(f"Search Results: {result['search_results']}\n")
    
    # # Process search results
    # processed_result = process_search_results(query, result["subqueries"], result["search_results"], index_column, data_columns)
    # result.update(processed_result)  # Add processed results to result
    # logger.info(f"Processed Search Results: \n{processed_result['extracted_values']} \n")
    
    # # Grade search results
    # initial_state = {
    #     "index_column": index_column,
    #     "data_columns": data_columns,
    #     "search_queries": result["subqueries"],
    #     "search_results": result["search_results"],
    #     "extracted_values": result["extracted_values"],
    #     "user_request": query
    # }

    # config = {
    #     "configurable": {
    #         "max_rectifier_iterations": 3,
    #     }
    # }

    # response = rectifier.invoke(initial_state, config)
    # logger.info(f"Search Results Grade: {response['grade']} - {response['reason']}")
    
if __name__ == "__main__":
    main()