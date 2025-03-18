from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import os

def google_search(query):
    query = query + " ## Search Instructions## Give the most relevant information first. Do a thorough search and provide all the information you can find. Always answer in English."
    # Initialize the client
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Set the model ID
    model_id = "gemini-2.0-flash"
    
    # Create the Google Search tool
    google_search_tool = Tool(
        google_search=GoogleSearch()
    )
    
    # Generate content using the model
    response = client.models.generate_content(
        model=model_id,
        contents=query,
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
        )
    )
    # Print the response content
    final_response = ""
    for each in response.candidates[0].content.parts:
        final_response += each.text
    
    return final_response