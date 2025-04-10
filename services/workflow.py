import logging
from services.mongo import MongoDBConfig
from cortex.state import WorkflowMessage
from pydantic import BaseModel, Field
from bson.objectid import ObjectId
from typing import Literal, List, Any, Optional, Union
import datetime
import pandas as pd

# Configure a logger for this module.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Workflow(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    id: ObjectId = Field(None, alias="_id")
    user_id: str
    name: str
    status: Literal["created", "in_progress", "completed"] = Field(default="created")
    messages: List[WorkflowMessage] = Field(default_factory=list)
    updated_at: Optional[str] = None  # ISO format datetime string

class WorkflowService:
    def __init__(self):
        db_config = MongoDBConfig()
        self.db = db_config.connect()
        logger.info("WorkflowService initialized and database connected.")

    def insert_workflow(self, workflow: Workflow) -> Workflow:
        # Set updated_at timestamp in ISO format
        workflow.updated_at = datetime.datetime.now().isoformat()
        
        # Insert into MongoDB 'workflows' collection
        result = self.db["workflows"].insert_one(workflow.model_dump())
        # Assign the generated _id to the workflow dict
        workflow.id = str(result.inserted_id)
        # Return a new Workflow instance with the inserted data
        return workflow
        
    def _convert_timestamps(self, obj: Any) -> Any:
        """Recursively convert Pandas Timestamps to ISO format strings."""
        if isinstance(obj, dict):
            # Handle Timestamp objects as keys
            return {k.isoformat() if isinstance(k, pd.Timestamp) else k: 
                    self._convert_timestamps(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_timestamps(item) for item in obj]
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif pd.isna(obj):
            return None
        else:
            return obj
            
    def get_workflow_by_id(self, workflow_id: str) -> Union[Workflow, None]:
        """Retrieve a workflow by its ID.
        
        Args:
            workflow_id: The ID of the workflow to retrieve
            
        Returns:
            The Workflow object if found, None otherwise
        """
        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(workflow_id)
            # Query the workflow from MongoDB
            workflow_data = self.db["workflows"].find_one({"_id": object_id})
            
            if workflow_data is None:
                logger.warning(f"Workflow with ID {workflow_id} not found")
                return None
            
            # Convert the MongoDB document to a Workflow object
            workflow = Workflow(**workflow_data)
            workflow.id = str(workflow.id)
            return workflow
            
        except Exception as e:
            logger.error(f"Error retrieving workflow with ID {workflow_id}: {str(e)}")
            return None
    
    def update_workflow(self, workflow: Workflow) -> Workflow:
        # Update the workflow in MongoDB 'workflows' collection
        if not workflow.id:
            raise ValueError("Workflow must have an id to be updated")
            
        # Set updated_at timestamp in ISO format
        workflow.updated_at = datetime.datetime.now().isoformat()
        
        # Convert ObjectId string back to ObjectId for MongoDB query
        object_id = ObjectId(workflow.id)
        
        # Get the workflow data and convert any Pandas Timestamps
        workflow_data = workflow.model_dump(exclude={"id"})
        workflow_data = self._convert_timestamps(workflow_data)
        
        # Update the document in MongoDB
        result = self.db["workflows"].replace_one(
            {"_id": object_id},
            workflow_data
        )
        
        if result.matched_count == 0:
            logger.warning(f"No workflow found with id {workflow.id}")
            
        logger.info(f"Updated workflow with id {workflow.id}")
        return workflow