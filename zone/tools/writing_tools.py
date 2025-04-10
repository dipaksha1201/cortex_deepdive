from pydantic import BaseModel, Field
from zone import gemini_pro
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated
from logger import runner_logger as logger
from langgraph.config import get_stream_writer
from langchain_core.prompts import ChatPromptTemplate

class ReportWriting(BaseModel):
    title: str = Field(description="4-5 word title of the artifact")
    content: str = Field(description="Properly formatted markdown content of the artifact")

report_writer_instructions = """ 
Roles:
Act as a PhD-level scientist, demonstrating rigorous analytical thinking, precision, and thoroughness in your approach. 
Your queries should reflect deep academic insight, mastery of foundational principles, and meticulous attention to detail. 
Ensure your approach is methodical and scholarly, designed to uncover nuanced insights, verify assumptions, and uphold 
academic standards of research quality.

Write the required artifact based on the instructions provided.
The instructions will be related to all the work done so far.
You can use the past steps to gather context and detailed information for writing the artifact.

<Writing Guidelines>
- Strict 250-300 word limit for each paragraph you decide to write.
- Use simple, clear language
- Use short paragraphs (3-4 sentences max)
- Use ## for the Report Topic you are writing about
- Use proper markdown formatting to write the artifact
</Writing Guidelines>

<Final Check>
1. Verify that EVERY claim is grounded in the provided Source material
2. Dont add any extra text to the final output
</Final Check>

<Past Steps>
{past_steps}
</Past Steps>

<Instructions>
{instruction}
</Instructions>
"""
Instruction = Annotated[str, Field(description="A detailed instruction to write the artifact, specifically mention what is required in the report and what can be reffered from your past steps. Generate a detailed instruction from your past steps and messages.")]

@tool
def report_writer_tool(instruction: Instruction, state: Annotated[dict, InjectedState]):
    """
    Write the required artifact based on the instructions provided.
    The instructions will be related to how the writer should write the artifact and what can be reffered from the past steps.
    The writer can use the past steps to gather context and detailed information for writing the artifact.
    """
    writer = get_stream_writer()
    writer({"tool_status": "Writing artifact"})
    
    try:
        past_steps_formatted = ""
        if "messages" in state:
            # Extract messages from the agent's state
            messages = state['messages']
            # Create a ChatPromptTemplate from the extracted messages
            chat_prompt = ChatPromptTemplate.from_messages(messages)
            past_steps_formatted = chat_prompt.format()
        
        prompt = report_writer_instructions.format(instruction=instruction, past_steps=past_steps_formatted)
        model = gemini_pro.with_structured_output(ReportWriting)
        
        response = model.invoke(prompt)
        writer({"tool_status": f"Artifact written on {response.title}"})
        output = {"title": response.title, "content": response.content}
        writer({"writer_output": output})
        
        return f"A complete artifact has been written based on the instructions provided on the topic: {response.title}"
    
    except Exception as e:
        error_message = f"Error in report_writer_tool: {str(e)}"
        writer({"tool_status": "Error writing artifact"})
        writer({"writer_output": {"title": "Error", "content": error_message}})
        
        return f"I encountered an error with the `report_writer_tool`. {error_message}"