import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
load_dotenv()
def get_gemini(model):
    llm = ChatGoogleGenerativeAI(model=model, google_api_key = os.getenv("GEMINI_API_KEY_BETA"))
    return llm

def initialize_langchain_embedding_model():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key = os.getenv("GEMINI_API_KEY_BETA"))
    return embeddings

planner_query_writer = get_gemini("gemini-2.0-flash")
planner_llm = get_gemini("gemini-2.0-flash")
report_writer_llm = get_gemini("gemini-2.0-flash-thinking-exp")
gemini_flash = get_gemini("gemini-2.0-flash")

__all__ = ["planner_query_writer", "planner_llm", "report_writer_llm", "gemini_flash"]