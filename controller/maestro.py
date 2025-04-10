import os
import logging
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, AsyncGenerator
from services.workflow import WorkflowService, Workflow
from cortex.state import WorkflowMessage
from cortex.interface import run_maestro
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from bson.objectid import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/maestro")

# Request model
class MaestroRequest(BaseModel):
    workflow_id: str = Field(default="", description="Workflow ID, empty for new workflow")
    message: str = Field(..., description="User message to process")
    user_id: str = Field(..., description="User ID for the workflow")
    workflow_name: Optional[str] = Field(default="New Workflow", description="Name for new workflow")

@router.post("/run")
async def run_maestro_api(request: MaestroRequest):
    """API endpoint to run Maestro agent with workflow management as a streaming API.
    
    Creates a new workflow if workflow_id is empty, otherwise fetches existing workflow.
    Adds user message to workflow and streams the output from run_maestro as it runs.
    
    Args:
        request: MaestroRequest containing workflow_id, message, and user_id
        
    Returns:
        StreamingResponse with JSON events from the Maestro agent
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            workflow_service = WorkflowService()
            workflow = None
            
            # Get or create workflow
            if request.workflow_id:
                workflow = workflow_service.get_workflow_by_id(request.workflow_id)
                if not workflow:
                    error_event = json.dumps({"error": f"Workflow with ID {request.workflow_id} not found"})
                    yield f"data: {error_event}\n\n"
                    return
            else:
                # Create a new workflow
                workflow = Workflow(
                    user_id=request.user_id,
                    name=request.workflow_name,
                    messages=[]
                )
                workflow = workflow_service.insert_workflow(workflow)
                logger.info(f"Created new workflow with ID {workflow.id}")
                
                # Send initial workflow created event
                init_event = json.dumps({"event": "workflow_created", "workflow_id": str(workflow.id)})
                yield f"data: {init_event}\n\n"
            
            # Add user message to workflow
            user_message = WorkflowMessage(
                type="user",
                content=request.message,
                task=None,
                tool_execution=None
            )
            workflow.messages.append(user_message)
            workflow_service.update_workflow(workflow)
            
            # Configure runnable config with workflow_id
            config = RunnableConfig(
                configurable={
                    "workflow_id": str(workflow.id),
                    "thread_id": str(workflow.id)
                }
            )
            
            # Stream from run_maestro
            async for chunk in run_maestro({"input": request.message}, config, workflow, workflow_service):
                # Convert the chunk to a JSON string and yield as SSE
                event_data = json.dumps(chunk)
                yield f"data: {event_data}\n\n"
                
                # If this is the completion event, save the final message to the workflow
                if chunk.get("event") == "complete" and chunk.get("is_cortex_output", True):
                    cortex_message = WorkflowMessage(
                        type="cortex",
                        content=chunk.get("content"),
                        task=None,
                        tool_execution=None
                    )
                    workflow.messages.append(cortex_message)
                    workflow_service.update_workflow(workflow)
                    
        
        except Exception as e:
            logger.error(f"Error in event_generator: {str(e)}")
            error_event = json.dumps({"event": "error", "message": str(e)})
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
        