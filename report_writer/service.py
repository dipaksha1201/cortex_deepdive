import os
import json
import httpx

async def retrieve_subqueries(queries: list[str], user_id: str):
    url = f"{os.getenv('DOCSERVICE_BASE_URL')}/query"
    data = {
        "user_name": user_id,
        "queries": queries
    }
    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }

    # Disable default timeouts
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=data, headers=headers) as response:
            if response.status_code == 200:
                async for line in response.aiter_lines():
                    try:
                        parsed_line = json.loads(line)
                        yield parsed_line
                    except json.JSONDecodeError:
                        print("Failed to parse line:", line)
            else:
                print("Failed:", response.status_code, response.text)