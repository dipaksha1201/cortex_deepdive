
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from services.research import start_planner, continue_research
from report_writer.model import DeepResearch
import json
from typing import Optional, Union
import asyncio
from report_writer.agent import run_deepdive
import uuid

api_router = APIRouter()    

class ResearchRequest(BaseModel):
    conversation_id: str = ""
    message: str = ""
    feedback: Optional[Union[bool, str]] = None

@api_router.post("/deepdive/{user_id}/{project_id}")
async def create_deepdive(user_id: str, project_id: str, request: ResearchRequest):
    """Create a new deep dive research report"""
    try:
        print("Request:", request.conversation_id)
        if request.conversation_id == "":
            conversation_id = str(uuid.uuid4())
        else:
            conversation_id = request.conversation_id
        
        inputs = {"messages": [{"role": "user", "content": request.message}]}
        config = {"configurable": {"user_id": user_id, "project_id": project_id, "thread_id": conversation_id}}
        print("Inputs:", inputs)
        print("Config:", config)
        response = await run_deepdive(inputs, config)
        print("Response:", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/deepdive/{user_id}/{report_id}/continue")
async def continue_deepdive(user_id: str, report_id: str, request: ResearchRequest):
    """Continue an existing deep dive research report"""
    try:
        researcher = DeepResearch()
        researcher.id = report_id
        if isinstance(request.feedback, bool) and request.feedback is True:
            asyncio.create_task(continue_research(user_id, report_id, request.feedback))
            researcher.update_status("in_progress")
            return {"report_id": report_id, "response": "starting-research"}
        else:
            response = await continue_research(user_id, report_id, request.feedback)
            researcher.update_plan(response["plan"] , response["description"])
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



  