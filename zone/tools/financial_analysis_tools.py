"""
Financial analysis tools for generating prompts and analyzing financial data.
These tools are designed to be used with Langchain.
"""

import os
from textwrap import dedent
from datetime import timedelta, datetime
from typing import List, Annotated, Optional
from pydantic import Field
from langchain_core.tools import tool
from ..utilities import YFinanceUtils, SecUtils as SECUtils, FmpUtils as FMPUtils
from logger import runner_logger as logger
from dotenv import load_dotenv
from zone import gemini_flash
load_dotenv()
from langgraph.config import get_stream_writer


def combine_prompt(instruction: str, resource: str, table_str: str = None) -> str:
    """
    Combine instruction, resource, and optional table string into a single prompt.
    """
    if table_str:
        return f"{table_str}\n\nResource: {resource}\n\nInstruction: {instruction}"
    return f"Resource: {resource}\n\nInstruction: {instruction}"


def save_to_file(data: str, file_path: str) -> None:
    """
    Save the provided data into a file at file_path, ensuring the directory exists.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write(data)


@tool
def analyze_income_stmt(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")], 
) -> str:
    """
    Retrieve and analyze the income statement for a company.
    
    Generates a prompt for comprehensive analysis of a company's income statement.
    The analysis evaluates revenue trends, cost structures, profit margins, and EPS
    by comparing historical data and industry benchmarks.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving income statement for {ticker_symbol}"})
    income_stmt = YFinanceUtils.get_income_stmt(ticker_symbol)
    df_string = "Income Statement:\n" + income_stmt.to_string().strip()
    instruction = dedent(
        """
        Conduct a comprehensive analysis of the company's income statement. 
        Evaluate revenue trends, cost structures, profit margins, and EPS by comparing historical data and industry benchmarks. 
        Summarize the analysis in a single paragraph (under 130 words) with 4-5 key insights.
        """
    )
    section_text = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    prompt = combine_prompt(instruction, section_text, df_string)
    # Save the income statement to a file for reference 
    response = gemini_flash.invoke(prompt)
    writer({"tool_status": f"Income statement analysis completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : income_stmt.to_dict(orient='records'),
        "artifact_name" : f"{ticker_symbol} - {fyear} Income Statement Analysis"
    }
    writer(output)
    return response.content


@tool
def analyze_balance_sheet(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
) -> str:
    """
    Retrieve and analyze the balance sheet for a company.
    
    Generates a prompt for comprehensive analysis of a company's balance sheet.
    The analysis evaluates asset composition, liabilities, and shareholders' equity,
    focusing on liquidity, solvency, and capital structure trends.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Analyzing balance sheet for {ticker_symbol}"})
    
    balance_sheet = YFinanceUtils.get_balance_sheet(ticker_symbol)
    df_string = "Balance Sheet:\n" + balance_sheet.to_string().strip()
    instruction = dedent(
        """
        Analyze the company's balance sheet by evaluating asset composition, liabilities, and shareholders' equity. 
        Focus on liquidity, solvency, and capital structure trends compared to historical data. 
        Provide your assessment in a single paragraph under 130 words.
        """
    )
    section_text = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    prompt = combine_prompt(instruction, section_text, df_string)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Balance sheet analysis completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : balance_sheet.to_dict(orient='index'),
        "artifact_name" : f"{ticker_symbol} - {fyear} Balance Sheet Analysis"
    }
    writer(output)
    return response.content   


@tool
def analyze_cash_flow(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
) -> str:
    """
    Retrieve and analyze the cash flow statement for a company.
    
    Generates a prompt for comprehensive analysis of a company's cash flow statement.
    The analysis evaluates operating, investing, and financing activities,
    highlighting trends in cash generation, expenditures, and liquidity.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving cash flow for {ticker_symbol}"})
    cash_flow = YFinanceUtils.get_cash_flow(ticker_symbol)
    df_string = "Cash Flow Statement:\n" + cash_flow.to_string().strip()
    instruction = dedent(
        """
        Evaluate the company's cash flow by examining operating, investing, and financing activities. 
        Highlight trends in cash generation, expenditures, and liquidity. 
        Summarize your findings in a continuous paragraph under 130 words.
        """
    )
    section_text = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    prompt = combine_prompt(instruction, section_text, df_string)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Cash flow analysis completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : cash_flow.to_dict(orient='index'),
        "artifact_name" : f"{ticker_symbol} - {fyear} Cash Flow Analysis"
    }
    writer(output)
    return response.content 


@tool
def analyze_segment_stmt(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
) -> str:
    """
    Analyze business segments using income statement data.
    
    Generates a prompt for identifying and analyzing a company's business segments
    from the income statement and supporting 10-K sections. For each segment,
    details revenue, net profit, and key trends.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving income statement for segment analysis for {ticker_symbol}"})
    income_stmt = YFinanceUtils.get_income_stmt(ticker_symbol)
    df_string = "Income Statement (Segment Analysis):\n" + income_stmt.to_string().strip()
    instruction = dedent(
        """
        Identify and analyze the company's business segments from the income statement and supporting 10-K sections. 
        For each segment, detail revenue, net profit, and key trends in a concise manner. 
        Limit each segment analysis to 60 words and consolidate overall findings within 150 words.
        """
    )
    section_text = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    prompt = combine_prompt(instruction, section_text, df_string)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Segment analysis completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : income_stmt.to_dict(orient='index'),
        "artifact_name" : f"{ticker_symbol} - {fyear} Segment Analysis"
    }
    writer(output)
    return response.content


@tool
def income_summarization(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
    income_stmt_analysis: Annotated[str, Field(description="Previously generated income statement analysis")],
    segment_analysis: Annotated[str, Field(description="Previously generated segment analysis")],
) -> str:
    """
    Synthesize income statement and segment analysis into a coherent summary.
    
    Combines previously generated income statement and segment analyses into
    a coherent, continuous paragraph with numbered key points. Ensures the summary
    is fact-based, integrates historical comparisons, and is concise.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Combining income statement and segment analysis for {ticker_symbol}"})
    instruction = dedent(
        f"""
        Combine the following analyses:
        Income Statement Analysis: {income_stmt_analysis}
        Segment Analysis: {segment_analysis}
        Synthesize these into a coherent, continuous paragraph with numbered key points.
        Ensure the summary is fact-based, integrates historical comparisons, and is under 160 words.
        """
    )
    section_text = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    prompt = combine_prompt(instruction, section_text)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Income summarization completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : None,
        "artifact_name" : f"{ticker_symbol} - {fyear} Income Summary"
    }
    writer(output)
    return response.content


@tool
def get_risk_assessment(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
) -> str:
    """
    Retrieve risk factors and summarize the top 3 key risks.
    
    Extracts risk factors from the 10-K filing and generates a prompt to identify
    and summarize the top 3 key risks. For each risk, discusses industry risk,
    cyclicality, risk quantification, and any downside protections.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving risk factors for {ticker_symbol}"})
    company_name = YFinanceUtils.get_stock_info(ticker_symbol).get("shortName", "N/A")
    risk_factors = SECUtils.get_10k_section(ticker_symbol, fyear, "1A")
    section_text = f"Company Name: {company_name}\n\nRisk Factors:\n{risk_factors}\n\n"
    instruction = dedent(
        """
        From the risk factors provided, identify and summarize the top 3 key risks. 
        For each risk, discuss industry risk, cyclicality, risk quantification, and any downside protections. 
        Present your analysis in a continuous paragraph without bullet points.
        """
    )
    prompt = combine_prompt(instruction, section_text)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Risk assessment completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : None,
        "artifact_name" : f"{ticker_symbol} - {fyear} Risk Assessment"
    }
    writer(output)
    return response.content


@tool
def get_competitors_analysis(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    competitors: Annotated[List[str], Field(description="List of competitor ticker symbols")],
) -> str:
    """
    Generate a comparative financial analysis prompt for the company and its competitors.
    
    Retrieves financial metrics for the company and its competitors over the past four years
    and generates a prompt to analyze trends in EBITDA Margin, EV/EBITDA, FCF Conversion,
    Gross Margin, ROIC, Revenue, and Revenue Growth.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving financial metrics for competitors for {ticker_symbol}"})
    financial_data = FMPUtils.get_competitor_financial_metrics(ticker_symbol, competitors, years=4)
    table_str = ""
    for metric in financial_data[ticker_symbol].index:
        table_str += f"\n\n{metric}:\n"
        table_str += f"{ticker_symbol}: {financial_data[ticker_symbol].loc[metric]}\n"
        for competitor in competitors:
            table_str += f"{competitor}: {financial_data[competitor].loc[metric]}\n"
    
    instruction = dedent(
        f"""
        Analyze the financial metrics for {ticker_symbol} and its competitors {competitors} over the past four years. 
        Discuss trends for EBITDA Margin, EV/EBITDA, FCF Conversion, Gross Margin, ROIC, Revenue, and Revenue Growth. 
        For each year, provide a comparative analysis highlighting improvements, declines, and current valuation insights. 
        Present your analysis in a continuous paragraph without bullet points.
        """
    )
    resource = f"Financial data for {ticker_symbol} and {competitors}:\n{table_str}"
    prompt = combine_prompt(instruction, resource)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Competitors analysis completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : None,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : None,
        "artifact_name" : f"{ticker_symbol} and {competitors} - Competitors Analysis"
    }
    writer(output)
    return response.content


@tool
def analyze_business_highlights(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
) -> str:
    """
    Analyze and summarize the performance highlights for each business line.
    
    Extracts business summary and MD&A sections from the 10-K filing and generates
    a prompt to describe the performance highlights for each business line with
    one summarizing sentence and one explanatory sentence per segment.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving business summary and MD&A for {ticker_symbol}"})
    business_summary = SECUtils.get_10k_section(ticker_symbol, fyear, 1)
    section_7 = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    section_text = f"Business Summary:\n{business_summary}\n\nMD&A:\n{section_7}"
    instruction = dedent(
        """
        Describe the performance highlights for each business line by providing one summarizing sentence and one explanatory sentence for each segment.
        """
    )
    prompt = combine_prompt(instruction, section_text)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Business highlights analysis completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : None,
        "artifact_name" : f"{ticker_symbol} - {fyear} Business Highlights"
    }
    writer(output)
    return response.content


@tool
def analyze_company_description(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    fyear: Annotated[str, Field(description="Fiscal year in YYYY format")],
    ) -> str:
    """
    Analyze the company description, including history, industry, strengths, and strategic initiatives.
    
    Extracts company information, business summary, and MD&A sections from the 10-K filing
    and generates a prompt to provide a comprehensive overview of the company, including
    its founding, industry, core strengths, competitive advantages, market position,
    and recent strategic initiatives.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving company information and business summary for {ticker_symbol}"})
    company_info = YFinanceUtils.get_stock_info(ticker_symbol)
    company_name = company_info.get("shortName", "N/A")
    business_summary = SECUtils.get_10k_section(ticker_symbol, fyear, 1)
    section_7 = SECUtils.get_10k_section(ticker_symbol, fyear, 7)
    section_text = f"Company Name: {company_name}\n\nBusiness Summary:\n{business_summary}\n\nMD&A:\n{section_7}"
    instruction = dedent(
        """
        Provide a comprehensive overview of the company, including its founding, industry, core strengths, competitive advantages, market position, and recent strategic initiatives. 
        Limit the description to 300 words.
        """
    )
    step_prompt = combine_prompt(instruction, section_text)
    instruction2 = "Summarize the above analysis in less than 130 words."
    prompt = combine_prompt(instruction2, step_prompt)
    response = gemini_flash.invoke(prompt) 
    writer({"tool_status": f"Company description completed for {ticker_symbol}"})
    output = {
        "tool_output" : response.content,
        "ticker_symbol" : ticker_symbol,
        "fyear" : fyear,
        "output_type" : "ticker_artifact",
        "file_type" : "text",
        "attached_csv" : None,
        "artifact_name" : f"{ticker_symbol} - {fyear} Company Description"
    }
    writer(output)
    return response.content 


@tool
def get_key_data(
    ticker_symbol: Annotated[str, Field(description="Stock ticker symbol")],
    filing_date: Annotated[str, Field(description="Filing date in YYYY-MM-DD format")]
) -> dict:
    """
    Aggregate key financial data for the given ticker and filing date.
    
    Retrieves and aggregates various financial metrics including analyst ratings,
    target price, average daily volume, closing price, market cap, 52-week price range,
    and book value per share (BVPS) for the specified ticker and filing date.
    """
    writer = get_stream_writer()
    writer({"tool_status": f"Retrieving key data for {ticker_symbol}"})
    if not isinstance(filing_date, datetime):
        filing_date = datetime.strptime(filing_date, "%Y-%m-%d")
    start_date = (filing_date - timedelta(weeks=52)).strftime("%Y-%m-%d")
    end_date = filing_date.strftime("%Y-%m-%d")
    hist = YFinanceUtils.get_stock_data(ticker_symbol, start_date, end_date)
    info = YFinanceUtils.get_stock_info(ticker_symbol)
    close_price = hist["Close"].iloc[-1]
    six_months_start = (filing_date - timedelta(weeks=26)).strftime("%Y-%m-%d")
    hist_last_6m = hist[(hist.index >= six_months_start) & (hist.index <= end_date)]
    avg_daily_volume_6m = hist_last_6m["Volume"].mean() if not hist_last_6m["Volume"].empty else 0
    fiftyTwoWeekLow = hist["High"].min()
    fiftyTwoWeekHigh = hist["Low"].max()
    rating, _ = YFinanceUtils.get_analyst_recommendations(ticker_symbol)
    target_price = FMPUtils.get_target_price(ticker_symbol, filing_date.strftime("%Y-%m-%d"))
    key_data = {
        "Rating": rating,
        "Target Price": target_price,
        f"6m avg daily vol ({info['currency']}mn)": f"{avg_daily_volume_6m / 1e6:.2f}",
        f"Closing Price ({info['currency']})": f"{close_price:.2f}",
        f"Market Cap ({info['currency']}mn)": _format_market_cap(ticker_symbol, filing_date.strftime('%Y-%m-%d')),
        f"52 Week Price Range ({info['currency']})": f"{fiftyTwoWeekLow:.2f} - {fiftyTwoWeekHigh:.2f}",
        f"BVPS ({info['currency']})": _format_bvps(ticker_symbol, filing_date.strftime('%Y-%m-%d')),
    }
    writer({"tool_status": f"Key data retrieved successfully for {ticker_symbol}"})
    return key_data


def _format_market_cap(ticker_symbol, date_str):
    """Helper method to safely format market cap value"""
    market_cap = FMPUtils.get_historical_market_cap(ticker_symbol, date_str)
    try:
        return f"{float(market_cap) / 1e6:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _format_bvps(ticker_symbol, date_str):
    """Helper method to safely format BVPS value"""
    bvps = FMPUtils.get_historical_bvps(ticker_symbol, date_str)
    try:
        return f"{float(bvps):.2f}"
    except (ValueError, TypeError):
        return "N/A"
