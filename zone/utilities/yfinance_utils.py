import yfinance as yf
import pandas as pd
from functools import wraps
from typing import Optional, Callable, Any

# Decorator to initialize the Ticker object
def init_ticker(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(symbol: str, *args, **kwargs) -> Any:
        ticker = yf.Ticker(symbol)
        return func(ticker, *args, **kwargs)
    return wrapper

# Optional: A decorator to apply another decorator to all class methods
def decorate_all_methods(decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and not attr.startswith("__"):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate

@decorate_all_methods(init_ticker)
class YFinanceUtils:
    
    @staticmethod
    def get_stock_data(ticker, start_date: str, end_date: str, save_path: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve historical stock data between start_date and end_date.
        """
        data = ticker.history(start=start_date, end=end_date)
        if save_path:
            data.to_csv(save_path)
            print(f"Stock data saved to {save_path}")
        return data

    @staticmethod
    def get_stock_info(ticker) -> dict:
        """
        Get the latest stock information.
        """
        return ticker.info

    @staticmethod
    def get_company_info(ticker, save_path: Optional[str] = None) -> pd.DataFrame:
        """
        Extract key company information and return as a DataFrame.
        """
        info = ticker.info
        company_info = {
            "Company Name": info.get("shortName", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Sector": info.get("sector", "N/A"),
            "Country": info.get("country", "N/A"),
            "Website": info.get("website", "N/A")
        }
        df = pd.DataFrame([company_info])
        if save_path:
            df.to_csv(save_path, index=False)
            print(f"Company info saved to {save_path}")
        return df

    @staticmethod
    def get_stock_dividends(ticker, save_path: Optional[str] = None) -> pd.Series:
        """
        Get historical dividend data.
        """
        dividends = ticker.dividends
        if save_path:
            dividends.to_csv(save_path)
            print(f"Dividend data saved to {save_path}")
        return dividends

    @staticmethod
    def get_income_stmt(ticker) -> pd.DataFrame:
        """
        Get the income statement of the company.
        """
        income_stmt = ticker.financials
        return income_stmt

    @staticmethod
    def get_balance_sheet(ticker) -> pd.DataFrame:
        """
        Get the balance sheet of the company.
        """
        balance_sheet = ticker.balance_sheet
        return balance_sheet

    @staticmethod
    def get_cash_flow(ticker) -> pd.DataFrame:
        """
        Get the cash flow statement of the company.
        """
        cash_flow = ticker.cashflow
        return cash_flow

    @staticmethod
    def get_analyst_recommendations(ticker) -> tuple:
        """
        Get the most common analyst recommendation and the corresponding vote count.
        """
        recommendations = ticker.recommendations
        if recommendations.empty:
            return None, 0

        # Exclude period column if necessary and determine the maximum vote
        row = recommendations.iloc[0, 1:]
        max_votes = row.max()
        # Find the recommendation(s) with the maximum votes
        top_recs = row[row == max_votes].index.tolist()
        return top_recs[0], max_votes

# Example usage:
if __name__ == "__main__":
    # This will automatically initialize the ticker for "AAPL" before calling the method.
    # stock_data = YFinanceUtils.get_stock_data("AAPL", "2021-01-01", "2021-12-31")
    stock_data = YFinanceUtils.get_balance_sheet("AAPL")
    print(stock_data)