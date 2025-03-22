from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import os
from logger import runner_logger as logger

def google_search(query):
    try:
        query = query + " ## Search Instructions## Give the most relevant information first. Do a thorough search and provide all the information you can find. Always answer in English."
        # Initialize the client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("Google API key not found in environment variables")
            return "Error: Google API key not configured properly."
            
        client = genai.Client(api_key=api_key)
        
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
        
        # Process the response content with proper error handling
        final_response = ""
        
        # Check if response has candidates
        if not response or not hasattr(response, 'candidates') or not response.candidates:
            logger.warning("Google search response has no candidates")
            return "No search results found. Please try a different query."
            
        # Check if the first candidate has content
        if not hasattr(response.candidates[0], 'content') or not response.candidates[0].content:
            logger.warning("Google search response candidate has no content")
            return "Search response has no content. Please try a different query."
            
        # Check if content has parts
        if not hasattr(response.candidates[0].content, 'parts') or not response.candidates[0].content.parts:
            logger.warning("Google search response content has no parts")
            return "Search response content is empty. Please try a different query."
        
        # Process all parts of the response
        for each in response.candidates[0].content.parts:
            if hasattr(each, 'text'):
                final_response += each.text
        
        if not final_response:
            logger.warning("No text content found in Google search response parts")
            return "No text content found in search results. Please try a different query."
            
        return final_response
        
    except Exception as e:
        logger.error(f"Error in google_search: {str(e)}")
        return f"An error occurred during the search: {str(e)}. Please try again later."