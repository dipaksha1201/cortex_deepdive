import os
import requests
from functools import wraps
from sec_api import ExtractorApi, QueryApi, RenderApi
from dotenv import load_dotenv
from logger import agent_logger as logger

load_dotenv()

# Endpoint for generating PDFs
PDF_GENERATOR_API = "https://api.sec-api.io/filing-reader"
# Directory for caching extracted sections
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

def init_sec_api(func):
    """
    Decorator to initialize SEC API instances before any API call.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # api_key = os.environ.get("SEC_API_KEY")
        api_key = "9e93a61fa8dd57a037790797803cb7ffa706cf7ab5e3d68e1a4f2f697fe1f04e"
        print(f"SEC API Key: {api_key}")
        if not api_key:
            raise EnvironmentError("SEC_API_KEY environment variable not set.")
        # Initialize API instances globally
        global extractor_api, query_api, render_api
        extractor_api = ExtractorApi(api_key)
        query_api = QueryApi(api_key)
        render_api = RenderApi(api_key)
        return func(*args, **kwargs)
    return wrapper

class SecUtils:
    """
    A utility class to interact with the SEC API.
    """

    @staticmethod
    @init_sec_api
    def get_10k_metadata(ticker: str, start_date: str, end_date: str):
        """
        Searches for 10-K filings for a given ticker within a date range.
        Returns metadata for the most recent filing.
        """
        query = {
            "query": f'ticker:"{ticker}" AND formType:"10-K" AND filedAt:[{start_date} TO {end_date}]',
            "from": 0,
            "size": 10,
            "sort": [{"filedAt": {"order": "desc"}}],
        }
        response = query_api.get_filings(query)
        return response["filings"][0] if response["filings"] else None

    @staticmethod
    @init_sec_api
    def download_10k_filing(ticker: str, start_date: str, end_date: str, save_folder: str) -> str:
        """
        Downloads the latest 10-K filing in HTML format.
        """
        metadata = SecUtils.get_10k_metadata(ticker, start_date, end_date)
        if metadata:
            ticker_symbol = metadata["ticker"]
            filing_url = metadata["linkToFilingDetails"]
            filing_date = metadata["filedAt"][:10]
            file_name = f"{filing_date}_{metadata['formType']}_{filing_url.split('/')[-1]}.htm"
            
            os.makedirs(save_folder, exist_ok=True)
            file_content = render_api.get_filing(filing_url)
            file_path = os.path.join(save_folder, file_name)
            
            with open(file_path, "w") as f:
                f.write(file_content)
            return f"{ticker_symbol}: HTML download succeeded. Saved to {file_path}"
        return f"No 10-K filing found for {ticker}"

    @staticmethod
    @init_sec_api
    def download_10k_pdf(ticker: str, start_date: str, end_date: str, save_folder: str) -> str:
        """
        Downloads the latest 10-K filing as a PDF.
        """
        metadata = SecUtils.get_10k_metadata(ticker, start_date, end_date)
        if metadata:
            ticker_symbol = metadata["ticker"]
            filing_url = metadata["linkToFilingDetails"]
            filing_date = metadata["filedAt"][:10]
            file_name = f"{filing_date}_{metadata['formType'].replace('/A', '')}_{filing_url.split('/')[-1]}.pdf"
            
            os.makedirs(save_folder, exist_ok=True)
            api_url = f"{PDF_GENERATOR_API}?token={os.environ['SEC_API_KEY']}&type=pdf&url={filing_url}"
            response = requests.get(api_url, stream=True)
            response.raise_for_status()
            file_path = os.path.join(save_folder, file_name)
            
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return f"{ticker_symbol}: PDF download succeeded. Saved to {file_path}"
        return f"No 10-K filing found for {ticker}"

    @staticmethod
    @init_sec_api
    def get_10k_section(
        ticker_symbol: str,
        fyear: str,
        section: str,
        report_address: str = None,
        save_path: str = None,
    ) -> str:
        """
        Extract a specific section from a 10-K report.

        If report_address is not provided, the method retrieves the filing metadata
        for the given ticker and fiscal year and uses the linkToFilingDetails as the report address.
        """
        # Ensure section is a string
        if isinstance(section, int):
            section = str(section)

        valid_sections = ["1A", "1B", "7A", "9A", "9B"] + [str(i) for i in range(1, 16)]
        if section not in valid_sections:
            raise ValueError(
                "Section must be in [1, 1A, 1B, 2, 3, 4, 5, 6, 7, 7A, 8, 9, 9A, 9B, 10, 11, 12, 13, 14, 15]"
            )

        cache_path = os.path.join(CACHE_DIR, f"sec_utils/{ticker_symbol}_{fyear}_{section}.txt")
        logger.info(f"Cache path: {cache_path}")
        if os.path.exists(cache_path):
            logger.info(f"Loading section from cache: {cache_path}")
            with open(cache_path, "r") as f:
                section_text = f.read()
        else:
            logger.info(f"Extracting section {section} for {ticker_symbol} in {fyear}")
            # If report_address isn't provided, retrieve it from filing metadata
            if report_address is None:
                # Define start and end dates for the fiscal year
                start_date = f"{fyear}-01-01"
                end_date = f"{fyear}-12-31"
                metadata = SecUtils.get_10k_metadata(ticker_symbol, start_date, end_date)
                if not metadata:
                    return f"Error: No filing metadata found for {ticker_symbol} in {fyear}"
                report_address = metadata.get("linkToFilingDetails")
                if not report_address:
                    return "Error: Filing metadata does not include a linkToFilingDetails."
                
            section_text = extractor_api.get_section(report_address, section, "text")
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            logger.info(f"Saving section to {cache_path}")
            with open(cache_path, "w") as f:
                f.write(section_text)

        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w") as f:
                f.write(section_text)

        return section_text