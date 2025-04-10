import operator
from typing import Annotated, List, Tuple
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any


class PlanExecute(TypedDict):
    input: str 
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str

class TickerArtifact(BaseModel):
    output: str
    ticker_symbol: str
    fyear: Optional[str]
    output_type: str
    file_type: str
    attached_csv: Optional[object]
    artifact_name: str

class ToolExecution(BaseModel):
    status: str
    type: str
    tool_output: Optional[dict[str, Any]]

class WorkflowMessage(BaseModel):
    type: Literal["instructor", "executor", "user", "cortex"]
    content: str
    task: Optional[str]
    tool_execution: Optional[List[ToolExecution]]

class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

class Response(BaseModel):
    """Response to user."""

    response: str = Field(
        description="Used to respond to user after completing the task and not to be used in the middle of the task"
    )

class Act(BaseModel):
    plan: List[str] = Field(
        description="A list of remaining steps. This should be empty when the task is complete."
    )
    update: str = Field(
        description="Used to update user after completing the task or the next action to be taken."
    )