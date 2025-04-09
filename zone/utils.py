def create_search_response_text(subquery_results) -> str:
    reasoning_steps = []
    for response in subquery_results:
        reasoning_steps.append("---------------Search Query---------------")
        reasoning_steps.append(response["query"])
        reasoning_steps.append("---------------Search Query RESPONSE---------------")
        reasoning_steps.append(response["response"])

    return "\n".join(reasoning_steps)

