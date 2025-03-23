from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import os
from logger import runner_logger as logger

def generate_final_string(mapped_grounding_supports):
    final_lines = ["##Sources##\n"]
    
    for support in mapped_grounding_supports:
        segment_text = support.get("segment_text", "")
        confidence_scores = support.get("confidence_scores", [])
        # Format confidence scores as a comma separated string
        confidence_str = ", ".join([str(score) for score in confidence_scores])
        
        # Extract titles from the sources (ignore URI)
        source_titles = [src.get("title", "") for src in support.get("sources", [])]
        titles_str = ", ".join(source_titles)
        
        final_lines.append(f"Segment Text: {segment_text} - Confidence: [{confidence_str}]")
        final_lines.append(f"Sources: [{titles_str}]")
    
    return "\n".join(final_lines)

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
        
        sources = []
        candidate = response.candidates[0]

        mapped_grounding_supports = []
        candidate = response.candidates[0]

        if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
            # Extract sources from grounding chunks
            for chunk in candidate.grounding_metadata.grounding_chunks:
                if hasattr(chunk, "web") and chunk.web:
                    sources.append({
                        "title": chunk.web.title,
                        "uri": chunk.web.uri
                    })

        if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
            chunks = candidate.grounding_metadata.grounding_chunks
            for support in candidate.grounding_metadata.grounding_supports:
                support_mapping = {
                    "confidence_scores": support.confidence_scores,
                    "segment_text": support.segment.text,
                    "sources": []
                }
                # Map each grounding support to corresponding chunk(s) using the indices
                for index in support.grounding_chunk_indices:
                    if index < len(chunks) and hasattr(chunks[index], "web") and chunks[index].web:
                        support_mapping["sources"].append({
                            "title": chunks[index].web.title,
                            "uri": chunks[index].web.uri
                        })
                mapped_grounding_supports.append(support_mapping)

        grounding_metadata_string = generate_final_string(mapped_grounding_supports)

        if not final_response:
            logger.warning("No text content found in Google search response parts")
            return "No text content found in search results. Please try a different query."
        result = final_response + "\n\n" + grounding_metadata_string
        return (result, sources)
        
    except Exception as e:
        logger.error(f"Error in google_search: {str(e)}")
        return f"An error occurred during the search: {str(e)}. Please try again later."
