from typing import Annotated, List, TypedDict, Literal, Dict
import operator
from pydantic import BaseModel, Field
from typing import Any


class Section(BaseModel):
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the report."
    )
    internal_search: bool = Field(
        description="Whether to perform internal search from the document hub for this section of the report."
    )
    content: str = Field(
        description="The content of the section."
    )   
    sources: List[Dict[str, Any]] | str = Field(
        description="List of sources used in this section."
    )

class Sections(BaseModel):
    description: str = Field(
        description="A one-sentence description of the sections of the report decided during the report planning process."
    )
    sections: List[Section] = Field(
        description="Sections of the report.",
    )

class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query for web search or internal search from the document hub.")

class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )

class HybridQueries(BaseModel): 
    internal_search_queries: List[SearchQuery] = Field(
        description="List of internal search queries.",
    )
    web_search_queries: List[SearchQuery] = Field(
        description="List of web search queries.",
    )

class Feedback(BaseModel):
    """Represents feedback for a report section evaluation.

    Attributes:
        grade: Indicates whether the section meets requirements ('pass') or needs revision ('fail').
        follow_up_queries: Contains a list of search queries to gather additional information if needed.
    """
    grade: Literal["pass","fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of follow-up search queries.",
    )

class ReportStateInput(TypedDict):
    topic: str # Report topic
    internal_documents: str # Internal documents
    
class ReportStateOutput(TypedDict):
    final_report: str # Final report

class ReportState(TypedDict):
    """State for managing the overall report generation workflow.
    
    This class maintains the state of the report generation process, including:
    - The report topic
    - User feedback on the report plan
    - List of report sections and their completion status
    - Compiled sections from research for final section writing
    - The final generated report
    
    Attributes:
        topic: The main topic of the report
        feedback_on_report_plan: User feedback on the proposed report structure
        sections: List of Section objects representing report sections
        completed_sections: List of completed sections using Send() API
        report_sections_from_research: Formatted string of completed research sections
        final_report: The complete generated report
    """
    topic: str # Report topic    
    description: str # Report description
    feedback_on_report_plan: str # Feedback on the report plan
    plan_context: str # Context built to address the feedback
    internal_documents: str # Internal documents
    sections: list[Section] # List of report sections
    completed_sections: Annotated[list, operator.add] # Send() API key
    report_sections_from_research: str # String of any completed sections from research to write final sections
    final_report: str # Final report

class SectionState(TypedDict):
    topic: str # Report topic
    section: Section # Report section  
    search_iterations: int # Number of search iterations done
    search_queries: list[SearchQuery] # List of search queries
    internal_search_queries: list[SearchQuery] # List of internal search queries
    search_results: str # String of formatted search results
    internal_search_results: str # String of formatted internal search results
    report_sections_from_research: str # String of any completed sections from research to write final sections
    completed_sections: list[Section] # Final key we duplicate in outer state for Send() API
    internal_documents: str # Internal documents
    search_sources: list[Any] # List of search sources

class SourceLabel(BaseModel):
    title: str = Field(..., description="Title of the source, e.g., the name of the website or publisher.")

class Source(BaseModel):
    index: str = Field(..., description="Unique identifier or index for the source within the report section.")
    confidence_scores: List[float] = Field(
        ..., description="List of confidence scores corresponding to the extracted information from the source."
    )
    segment_text: str = Field(
        ..., description="Text segment from the report that is associated with this source. Only include a small amount of text."
    )
    sources: List[SourceLabel] = Field(
        ..., description="List of source labels containing the title of each source used in this segment."
    )

class SectionWriter(BaseModel):
    content: str = Field(
        ..., description="The comprehensive report paragraph or content for this section, generated by the LLM."
    )
    sources: List[Source] = Field(
        ..., description="List of sources used in this section, populated incrementally as the content is generated."
    )

class SectionOutputState(TypedDict):
    completed_sections: list[Section] # Final key we duplicate in outer state for Send() API