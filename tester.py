import os
import types
from textwrap import dedent
from zone import CortexOrchestration

# Import your actual utilities
from zone.tools import ReportLabTool, ChartingTool, ReportAnalysisTools
from zone.utilities import TextUtils, FmpUtils
# --- Bundle Actual Utilities into a Module-like Object ---
utils = types.ModuleType("utils")
# Map your utility functions to expected names.
utils.get_sec_report = FmpUtils.get_sec_report
utils.check_text_length = TextUtils.check_text_length
utils.build_annual_report = ReportLabTool.build_annual_report
utils.ReportAnalysisUtils = ReportAnalysisTools
utils.ReportChartUtils = ChartingTool

# --- Prepare Work Directory ---
work_dir = "zone_test_run_1"
os.makedirs(work_dir, exist_ok=True)

# --- Create the Task Instruction (as in the autogen script) ---
company = "AAPL"
competitors = ["MSFT", "GOOGL"]
fyear = "2024"
task = dedent(
    f"""
    With the tools you've been provided, write an annual report based on {company}'s and {competitors}'s {fyear} 10-k report, format it into a pdf.
    Pay attention to the followings:
    - Explicitly explain your working plan before you kick off.
    - Use tools one by one for clarity, especially when asking for instructions.
    - All your file operations should be done in "{work_dir}".
    - Display any image in the chat once generated.
    - For competitors analysis, strictly follow my prompt and use data only from the financial metrics table, do not use similar sentences in other sections, delete similar sentence, classify it into either of the two. The last sentence always talks about the Discuss how {company}’s performance over these years and across these metrics might justify or contradict its current market valuation (as reflected in the EV/EBITDA ratio).
    - Each paragraph in the first page (business overview, market position and operating results) should be between 150 and 160 words, each paragraph in the second page (risk assessment and competitors analysis) should be between 500 and 600 words, don't generate the pdf until this is explicitly fulfilled.
    """
)

# --- Run the Test Script ---
if __name__ == "__main__":
    orchestrator = CortexOrchestration(work_dir=work_dir, utils=utils)
    orchestrator.run(task=task)