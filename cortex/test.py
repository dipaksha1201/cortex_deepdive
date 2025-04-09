import asyncio
from cortex.graph import cortex
from textwrap import dedent
from logger import cortex_logger as logger
from dotenv import load_dotenv
load_dotenv()

config = { "configurable": { "thread_id": "cortex-125"}, "recursion_limit": 50 }
work_dir = "/content/cortex/report"
company = "AAPL"
competitors = ["GOOGL","MSFT"]
fyear = "2024"

task = dedent(
    f"""
    With the tools you've been provided, write an annual report based on {company}'s and{competitors}'s{fyear} 10-k report, format it into a markdown.
    Pay attention to the followings:
    - Use tools one by one for clarity, especially when asking for instructions.
    - Discuss how {company}’s performance over these years and across these metrics might justify or contradict its current market valuation (as reflected in the EV/EBITDA ratio).
    - Each paragraph in the first page(business overview, market position and operating results) should be between 150 and 160 words, each paragraph in the second page(risk assessment and competitors analysis) should be between 500 and 600 words, don't generate the markdown until this is explicitly fulfilled.
"""
)

# task = dedent(
#     f"""
#     With the tools you've been provided, write a report based on {company}'s and{competitors}'s{fyear} 10-k report.
#     analyse balance sheet and give your findings.
# """
# )

inputs = {"input": task}

async def main():
    async for event in cortex.astream(inputs, config=config, stream_mode="custom"):
        for k, v in event.items():
            if k != "__end__":
                logger.info(f"{k} - {v}")

if __name__ == "__main__":
    asyncio.run(main())