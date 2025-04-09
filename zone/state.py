from pydantic import BaseModel
from typing import Literal, List, Any, Optional


class SearchQueries(BaseModel):
    search_queries: List[str]

class SubCsvComposer(BaseModel):
    user_request: str
    search_queries: List[str]
    search_results: str
    extracted_values: List[dict[str, Any]]
    grade: Optional[Literal["PASS", "FAIL"]] = None
    reason: Optional[str] = ""
    index_column: str
    data_columns: List[str]
    search_iteration: int = 0   

class SearchResultsGrade(BaseModel):
    grade: Literal["PASS", "FAIL"]
    reason: str