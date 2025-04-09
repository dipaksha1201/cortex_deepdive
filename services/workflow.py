import logging
from services.mongo import MongoDBConfig
from cortex.state import WorkflowMessage
from pydantic import BaseModel, Field
from bson.objectid import ObjectId
from typing import Literal, List

# Configure a logger for this module.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Workflow(BaseModel):
    id: ObjectId = Field(None, alias="_id")
    user_id: str
    name: str
    status: Literal["created", "in_progress", "completed"] = Field(default="created")
    messages: List[WorkflowMessage] = Field(default_factory=list)

class WorkflowService:
    def __init__(self):
        db_config = MongoDBConfig()
        self.db = db_config.connect()
        logger.info("WorkflowService initialized and database connected.")

    def insert_workflow(self, workflow: Workflow) -> Workflow:
        # Insert into MongoDB 'workflows' collection
        result = self.db["workflows"].insert_one(workflow.model_dump())
        # Assign the generated _id to the workflow dict
        workflow.id = str(result.inserted_id)
        # Return a new Workflow instance with the inserted data
        return workflow