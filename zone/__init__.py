import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_gemini(model):
    llm = ChatGoogleGenerativeAI(model=model, google_api_key = os.getenv("GEMINI_API_KEY_BETA"))
    return llm

gemini_flash = get_gemini("gemini-2.0-flash")
gemini_pro = get_gemini("gemini-2.5-pro-exp-03-25")

__all__ = ["gemini_flash", "gemini_pro"]