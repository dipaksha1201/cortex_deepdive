import os
import mplfinance as mpf
import pandas as pd
from matplotlib import pyplot as plt
from typing import Annotated, List, Tuple, Union
from pandas import DateOffset
from datetime import datetime, timedelta

from zone.utilities.yfinance_utils import YFinanceUtils


class ChartingTool:
    @staticmethod
    def plot_stock_chart(
        ticker_symbol: Annotated[str, "Ticker symbol of the stock (e.g., 'AAPL')"],
        start_date: Annotated[str, "Start date in 'YYYY-MM-DD' format"],
        end_date: Annotated[str, "End date in 'YYYY-MM-DD' format"],
        save_path: Annotated[str, "File path to save the chart"],
        verbose: Annotated[bool, "If True, print stock data"] = False,
        chart_type: Annotated[str, "Chart type: 'candle', 'ohlc', etc."] = "candle",
        style: Annotated[str, "Plot style: 'default', 'classic', etc."] = "default",
        mav: Annotated[Union[int, List[int], Tuple[int, ...], None], "Moving average window(s)"] = None,
        show_nontrading: Annotated[bool, "Show non-trading days"] = False,
    ) -> str:
        """
        Plot a stock price chart using mplfinance.
        """
        stock_data = YFinanceUtils.get_stock_data(ticker_symbol, start_date, end_date)
        if verbose:
            print(stock_data.to_string())

        params = {
            "type": chart_type,
            "style": style,
            "title": f"{ticker_symbol} {chart_type} Chart",
            "ylabel": "Price",
            "volume": True,
            "ylabel_lower": "Volume",
            "mav": mav,
            "show_nontrading": show_nontrading,
            "savefig": save_path,
        }
        filtered_params = {k: v for k, v in params.items() if v is not None}
        mpf.plot(stock_data, **filtered_params)
        return f"{chart_type} chart saved to <img {save_path}>"

    @staticmethod
    def get_share_performance(
        ticker_symbol: Annotated[str, "Ticker symbol of the stock (e.g., 'AAPL')"],
        filing_date: Annotated[Union[str, datetime], "Filing date in 'YYYY-MM-DD' format"],
        save_path: Annotated[str, "File path to save the chart"],
    ) -> str:
        """
        Plot the stock performance of a company compared to the S&P 500 over the past year.
        """
        if isinstance(filing_date, str):
            filing_date = datetime.strptime(filing_date, "%Y-%m-%d")

        def fetch_stock_data(ticker: str) -> pd.Series:
            start = (filing_date - timedelta(days=365)).strftime("%Y-%m-%d")
            end = filing_date.strftime("%Y-%m-%d")
            historical_data = YFinanceUtils.get_stock_data(ticker, start, end)
            return historical_data["Close"]

        target_close = fetch_stock_data(ticker_symbol)
        sp500_close = fetch_stock_data("^GSPC")
        info = YFinanceUtils.get_stock_info(ticker_symbol)

        company_change = ((target_close - target_close.iloc[0]) / target_close.iloc[0]) * 100
        sp500_change = ((sp500_close - sp500_close.iloc[0]) / sp500_close.iloc[0]) * 100

        start_date = company_change.index.min()
        four_months = start_date + DateOffset(months=4)
        eight_months = start_date + DateOffset(months=8)
        end_date = company_change.index.max()

        plt.rcParams.update({"font.size": 20})
        plt.figure(figsize=(14, 7))
        plt.plot(company_change.index, company_change, label=f'{info["shortName"]} Change %', color="blue")
        plt.plot(sp500_change.index, sp500_change, label="S&P 500 Change %", color="red")
        plt.title(f'{info["shortName"]} vs S&P 500 - Change % Over the Past Year')
        plt.xlabel("Date")
        plt.ylabel("Change %")
        plt.xticks(
            [start_date, four_months, eight_months, end_date],
            [
                start_date.strftime("%Y-%m"),
                four_months.strftime("%Y-%m"),
                eight_months.strftime("%Y-%m"),
                end_date.strftime("%Y-%m"),
            ],
        )
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plot_file = f"{save_path}/share_performance.png" if os.path.isdir(save_path) else save_path
        plt.savefig(plot_file)
        plt.close()
        return f"Share performance chart saved to <img {plot_file}>"

    @staticmethod
    def get_pe_eps_performance(
        ticker_symbol: Annotated[str, "Ticker symbol of the stock (e.g., 'AAPL')"],
        filing_date: Annotated[Union[str, datetime], "Filing date in 'YYYY-MM-DD' format"],
        years: Annotated[int, "Number of years to analyze"] = 4,
        save_path: Annotated[str, "File path to save the chart"] = None,
    ) -> str:
        """
        Plot the PE ratio and EPS performance of a company over the past `years` years.
        """
        if isinstance(filing_date, str):
            filing_date = datetime.strptime(filing_date, "%Y-%m-%d")

        income_stmt = YFinanceUtils.get_income_stmt(ticker_symbol)
        eps = income_stmt.loc["Diluted EPS", :]

        days = round((years + 1) * 365.25)
        start = (filing_date - timedelta(days=days)).strftime("%Y-%m-%d")
        end = filing_date.strftime("%Y-%m-%d")
        historical_data = YFinanceUtils.get_stock_data(ticker_symbol, start, end)

        dates = pd.to_datetime(eps.index[::-1], utc=True)
        results = {}
        for date in dates:
            if date not in historical_data.index:
                close_price = historical_data.asof(date)
            else:
                close_price = historical_data.loc[date]
            results[date] = close_price["Close"]

        pe = [p / e for p, e in zip(results.values(), eps.values[::-1])]
        dates_formatted = eps.index[::-1]
        eps_values = eps.values[::-1]
        info = YFinanceUtils.get_stock_info(ticker_symbol)

        fig, ax1 = plt.subplots(figsize=(14, 7))
        plt.rcParams.update({"font.size": 20})
        color = "tab:blue"
        ax1.set_xlabel("Date")
        ax1.set_ylabel("PE Ratio", color=color)
        ax1.plot(dates_formatted, pe, color=color)
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.grid(True)

        ax2 = ax1.twinx()
        color = "tab:red"
        ax2.set_ylabel("EPS", color=color)
        ax2.plot(dates_formatted, eps_values, color=color)
        ax2.tick_params(axis="y", labelcolor=color)

        plt.title(f'{info["shortName"]} PE Ratio and EPS Over the Past {years} Years')
        plt.xticks(rotation=45)
        plt.xticks(dates_formatted, [d.strftime("%Y-%m") for d in dates_formatted])
        plt.tight_layout()
        plot_file = f"{save_path}/pe_eps_performance.png" if os.path.isdir(save_path) else save_path
        plt.savefig(plot_file)
        plt.close()
        return f"PE and EPS performance chart saved to <img {plot_file}>"