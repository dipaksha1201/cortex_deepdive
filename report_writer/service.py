import os
import json
import httpx
import asyncio
from logger import cortex_logger as logger
from typing import Dict, List, Any, AsyncGenerator
from report_writer import gemini_pro
from pydantic import BaseModel

PROMPT = """
Roles:
Act as a PhD-level scientist, demonstrating rigorous analytical thinking, precision, and thoroughness in your approach. 
Your queries should reflect deep academic insight, mastery of foundational principles, and meticulous attention to detail. 
Ensure your approach is methodical and scholarly, designed to uncover nuanced insights, verify assumptions, and uphold 
academic standards of research quality.

You are given a report. Your task is to extract up to 10 critical highlights that are genuinely insightful and actionable — avoid generic observations. Focus on insights that can drive business, product, or strategic decisions.

Also, based on the nature of the report, assign a unique research type that best reflects its content and purpose. This can be an existing category ({categories}) or a new, precise classification if the report does not fit traditional types.

Make sure the research type is from existing categories unless absolutely necessary. Avoid creating similar research types that already exist rather use existing categories. Research Type should not be longer than 2 words.

Report:
{report}
"""

class ReportMetadata(BaseModel):
    insights: List[str]
    type: str

def generate_report_metadata(report: str, categories: list[str]) -> ReportMetadata:
    prompt = PROMPT.format(categories=", ".join(categories), report=report)
    logger.info(f"Prompt: {prompt}")
    model = gemini_pro.with_structured_output(ReportMetadata)
    response = model.invoke(prompt)
    return response

async def retrieve_subqueries(queries: list[str], user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    url = f"{os.getenv('DOCSERVICE_BASE_URL')}/query"
    data = {
        "user_name": user_id,
        "queries": queries
    }
    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }

    logger.info(f"Retrieving subqueries for queries: {queries}")
    
    # Configure connection pool limits and timeouts
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
    timeout = httpx.Timeout(None)  # No timeout
    
    # Add retry logic
    max_retries = 3
    retry_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                async with client.stream("POST", url, json=data, headers=headers) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            try:
                                parsed_line = json.loads(line)
                                yield parsed_line
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse line: {line}")
                    else:
                        error_msg = f"Request failed: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        raise httpx.HTTPStatusError(error_msg, request=response.request, response=response)
            # If we get here without exceptions, we can break the retry loop
            break
        except (httpx.HTTPError, httpx.NetworkError, httpx.TimeoutException) as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                # Wait before retrying with exponential backoff
                await asyncio.sleep(retry_delay * (2 ** attempt))
            else:
                logger.error(f"All {max_retries} attempts failed for query request")
                raise