import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from functools import wraps
from typing import Annotated, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Utility: Decorator to apply a decorator to all methods in a class
def decorate_all_methods(decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and not attr.startswith("__"):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate

# Utility: Adjust the date to the next weekday if needed
def get_next_weekday(date_str: str) -> datetime:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    while date_obj.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        date_obj += timedelta(days=1)
    return date_obj

# Decorator to initialize the FMP API key
def init_fmp_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global fmp_api_key
        if not os.environ.get("FMP_API_KEY"):
            print("Please set the FMP_API_KEY environment variable.")
            return None
        # fmp_api_key = os.environ["FMP_API_KEY"]
        fmp_api_key = "fYlYnVqOirbtSrRcQdRC1h5qx1DWH0Dt"
        return func(*args, **kwargs)
    return wrapper

@decorate_all_methods(init_fmp_api)
class FmpUtils:
    """Utility class to interact with the Financial Modeling Prep API."""

    @staticmethod
    def get_target_price(
        ticker_symbol: Annotated[str, "Ticker symbol"],
        target_date: Annotated[str, "Target date in yyyy-mm-dd format"],
    ) -> str:
        """Retrieve target price range and median for a given stock on a specific date."""
        url = f"https://financialmodelingprep.com/api/v4/price-target?symbol={ticker_symbol}&apikey={fmp_api_key}"
        response = requests.get(url)
        if response.status_code != 200:
            return f"Failed to retrieve data: {response.status_code}"
        data = response.json()
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        prices = [
            item["priceTarget"]
            for item in data
            if abs((datetime.strptime(item["publishedDate"].split("T")[0], "%Y-%m-%d") - target_dt).days) <= 999
        ]
        if prices:
            return f"{np.min(prices)} - {np.max(prices)} (Median: {np.median(prices)})"
        return "N/A"

    @staticmethod
    def get_sec_report(
        ticker_symbol: Annotated[str, "Ticker symbol only one"],
        fyear: Annotated[str, "Fiscal year as yyyy or 'latest'"],
    ) -> str:
        """Retrieve the SEC 10-K report URL and filing date for a given stock."""
        
        print("Retrieving SEC report data for ticker:", ticker_symbol)
        url = f"https://financialmodelingprep.com/api/v3/sec_filings/{ticker_symbol}?type=10-k&page=0&apikey={fmp_api_key}"
        response = requests.get(url)
        if response.status_code != 200:
            return f"Failed to retrieve data: {response.status_code}"
        data = response.json()
        if fyear == "latest":
            filing = data[0]
        else:
            filing = next((item for item in data if item["fillingDate"].startswith(fyear)), None)
            if filing is None:
                return "No report found for the specified year."
        return f"Link: {filing['finalLink']}\n Filing Date: {filing['fillingDate']} for {ticker_symbol}"

    @staticmethod
    def get_historical_market_cap(
        ticker_symbol: Annotated[str, "Ticker symbol"],
        date: Annotated[str, "Date in yyyy-mm-dd format"],
    ) -> str:
        """Retrieve the historical market capitalization for a stock on a given date."""
        adjusted_date = get_next_weekday(date).strftime("%Y-%m-%d")
        url = (
            f"https://financialmodelingprep.com/api/v3/historical-market-capitalization/"
            f"{ticker_symbol}?limit=100&from={adjusted_date}&to={adjusted_date}&apikey={fmp_api_key}"
        )
        response = requests.get(url)
        if response.status_code != 200:
            return f"Failed to retrieve data: {response.status_code}"
        data = response.json()
        if data:
            return data[0]["marketCap"]
        return "Data not available"

    @staticmethod
    def get_historical_bvps(
        ticker_symbol: Annotated[str, "Ticker symbol"],
        target_date: Annotated[str, "Date in yyyy-mm-dd format"],
    ) -> str:
        """Retrieve the historical Book Value Per Share (BVPS) closest to the target date."""
        url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker_symbol}?limit=40&apikey={fmp_api_key}"
        response = requests.get(url)
        data = response.json()
        if not data:
            return "No data available"
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        closest = min(data, key=lambda item: abs((datetime.strptime(item["date"], "%Y-%m-%d") - target_dt).days))
        return closest.get("bookValuePerShare", "No BVPS data available")

    @staticmethod
    def get_financial_metrics(
        ticker_symbol: Annotated[str, "Ticker symbol"],
        years: Annotated[int, "Number of years to retrieve metrics for"] = 4,
    ) -> pd.DataFrame:
        """Retrieve key financial metrics over a number of years for a stock."""
        base_url = "https://financialmodelingprep.com/api/v3"
        income_url = f"{base_url}/income-statement/{ticker_symbol}?limit={years}&apikey={fmp_api_key}"
        ratios_url = f"{base_url}/ratios/{ticker_symbol}?limit={years}&apikey={fmp_api_key}"
        key_metrics_url = f"{base_url}/key-metrics/{ticker_symbol}?limit={years}&apikey={fmp_api_key}"

        income_data = requests.get(income_url).json()
        ratios_data = requests.get(ratios_url).json()
        key_metrics_data = requests.get(key_metrics_url).json()

        df = pd.DataFrame()
        for i in range(years):
                revenue_growth = None
                if i > 0 and income_data[i - 1]["revenue"] != 0:
                    revenue_growth = round(
                        ((income_data[i]["revenue"] - income_data[i - 1]["revenue"]) / income_data[i - 1]["revenue"]) * 100, 1
                    )
                    revenue_growth = f"{revenue_growth}%"
                metrics = {
                    "Revenue (M)": round(income_data[i]["revenue"] / 1e6),
                    "Revenue Growth": revenue_growth,
                    "Gross Margin": round(income_data[i]["grossProfit"] / income_data[i]["revenue"], 2),
                    "EBITDA (M)": round(income_data[i]["ebitda"] / 1e6),
                    "EBITDA Margin": round(income_data[i].get("ebitdaratio", 0), 2),
                    "FCF (M)": round(
                        key_metrics_data[i]["enterpriseValue"] / key_metrics_data[i]["evToOperatingCashFlow"] / 1e6
                    )
                    if key_metrics_data[i]["evToOperatingCashFlow"] != 0
                    else None,
                    "ROIC": f"{round(key_metrics_data[i].get('roic', 0) * 100, 1)}%",
                    "EV/EBITDA": round(key_metrics_data[i].get("enterpriseValueOverEBITDA", 0), 2),
                    "PE Ratio": round(ratios_data[i].get("priceEarningsRatio", 0), 2),
                    "PB Ratio": round(key_metrics_data[i].get("pbRatio", 0), 2),
                }
                year_label = income_data[i]["date"][:4]
                df[year_label] = pd.Series(metrics)
        return df.sort_index(axis=1)

    @staticmethod
    def get_competitor_financial_metrics(
        ticker_symbol: Annotated[str, "Ticker symbol"],
        competitors: Annotated[List[str], "List of competitor ticker symbols"],
        years: Annotated[int, "Number of years to retrieve metrics for"] = 4,
    ) -> dict:
        """Retrieve financial metrics for a company and its competitors."""
        base_url = "https://financialmodelingprep.com/api/v3"
        all_data = {}
        symbols = [ticker_symbol] + competitors

        for sym in symbols:
            income_url = f"{base_url}/income-statement/{sym}?limit={years}&apikey={fmp_api_key}"
            ratios_url = f"{base_url}/ratios/{sym}?limit={years}&apikey={fmp_api_key}"
            key_metrics_url = f"{base_url}/key-metrics/{sym}?limit={years}&apikey={fmp_api_key}"

            income_data = requests.get(income_url).json()
            ratios_data = requests.get(ratios_url).json()
            key_metrics_data = requests.get(key_metrics_url).json()

            metrics_dict = {}
            for i in range(years):
                revenue_growth = None
                if i > 0 and income_data[i - 1]["revenue"] != 0:
                    revenue_growth = round(
                        ((income_data[i]["revenue"] - income_data[i - 1]["revenue"]) / income_data[i - 1]["revenue"]) * 100,
                        1,
                    )
                    revenue_growth = f"{revenue_growth}%"
                metrics_dict[i] = {
                    "Revenue (M)": round(income_data[i]["revenue"] / 1e6),
                    "Revenue Growth": revenue_growth,
                    "Gross Margin": round(income_data[i]["grossProfit"] / income_data[i]["revenue"], 2),
                    "EBITDA Margin": round(income_data[i].get("ebitdaratio", 0), 2),
                    "FCF Conversion": round(
                        key_metrics_data[i]["enterpriseValue"]
                        / key_metrics_data[i]["evToOperatingCashFlow"]
                        / income_data[i]["netIncome"]
                        if key_metrics_data[i]["evToOperatingCashFlow"] != 0
                        else 0,
                        2,
                    ),
                    "ROIC": f"{round(key_metrics_data[i].get('roic', 0) * 100, 1)}%",
                    "EV/EBITDA": round(key_metrics_data[i].get("enterpriseValueOverEBITDA", 0), 2),
                }
            all_data[sym] = pd.DataFrame.from_dict(metrics_dict, orient="index").sort_index(axis=1)
        return all_data

if __name__ == "__main__":
    # For testing: ensure that FMP_API_KEY is set in your environment.
    print(FmpUtils.get_sec_report("NEE", "2024"))