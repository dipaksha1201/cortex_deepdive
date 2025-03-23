from pydantic import BaseModel
from typing import List, Any
from report_writer.state import Section
from typing import Literal
from services.mongo import MongoDBConfig
from bson.objectid import ObjectId
import pytz
from datetime import datetime
from report_writer.service import ReportMetadata

class DeepResearch(BaseModel):
    id: str = ""
    user_id: str = ""
    project_id: str = ""
    topic: str = ""
    description: str = ""
    plan: List[Section] = []
    sources: List[Any] = []
    status: Literal["to_be_started" , "in_planning","in_progress", "completed"] = "to_be_started"
    report: str = ""
    created_at: str = ""
    insights: List[str] = []
    type: str = ""    
    # This will be excluded from serialization
    db: any = None

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True
        exclude = {"db"}

    def __init__(self, **data):
        super().__init__(**data)
        # Connect to database
        db_config = MongoDBConfig()
        self.db = db_config.connect()

    def create_report(self, user_id: str, project_id: str, topic: str):
        self.user_id = user_id
        self.project_id = project_id
        self.topic = topic
        # Exclude db from serialization
        result = self.db["deep_research"].insert_one(self.model_dump(exclude={"db"}))
        self.id = str(result.inserted_id)
        return self.id

    def update_status(self, status: Literal["in_planning","in_progress", "completed"]):
        self.status = status
        if status == "in_progress":
            self.created_at = datetime.now(pytz.utc).isoformat()
            self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"status": status, "created_at": self.created_at}})
        else:
            self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"status": status}})
        
    def update_report(self, report: str):
        self.report = report
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"report": report}})
        
    def update_metadata(self, metadata: ReportMetadata):
        """Update the metadata for this research report.
        
        Args:
            metadata: A ReportMetadata object containing insights and type."""
        self.insights = metadata.insights
        self.type = metadata.type
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"insights": self.insights, "type": self.type}})
    
    def update_report_completion(self, report: str, sources: List[Any], metadata: ReportMetadata, status: Literal["in_planning","in_progress", "completed"] = "completed"):
        """Update report with all completion data in a single database operation.
        
        Args:
            report: The completed report content
            sources: List of sources used in the report
            metadata: A ReportMetadata object containing insights and type
            status: The new status of the report (defaults to "completed")
        """
        # Update local object properties
        self.report = report
        self.sources = sources
        self.insights = metadata.insights
        self.type = metadata.type
        self.status = status
        
        # Perform a single database update with all fields
        self.db["deep_research"].update_one(
            {"_id": ObjectId(self.id)}, 
            {"$set": {
                "report": report,
                "sources": sources,
                "insights": self.insights,
                "type": self.type,
                "status": status
            }}
        )

    def update_plan(self, plan, description):
        """Update the plan for this research report.
        
        Args:
            plan: Can be either a list of Section objects or a list of dictionaries
                 representing serialized Section objects.
        """
        self.plan = plan
        self.description = description
        # Ensure we're storing serializable data in MongoDB
        if plan and isinstance(plan[0], dict):
            # Already in dictionary format
            plan_data = plan
        else:
            # Convert Section objects to dictionaries
            plan_data = [section.model_dump() if hasattr(section, 'model_dump') else section for section in plan]
            
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"plan": plan_data, "description": description}})
        
    def update_sources(self, sources: List[Any]):
        self.sources = sources
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"sources": sources}})
        
    def delete(self):
        self.db["deep_research"].delete_one({"_id": ObjectId(self.id)})
        
    def load_report_by_id(self, report_id: str):
        report = self.db["deep_research"].find_one({"_id": ObjectId(report_id)})
        if not report:
            raise ValueError(f"Report with id {report_id} not found")
        self = DeepResearch(**report)
        self.id = str(report["_id"])
        return self
        
    @staticmethod
    def get_unique_types_by_user_id(user_id: str):
        """
        Retrieve all unique types of DeepResearch documents for a specific user.
        
        Args:
            user_id (str): The ID of the user to filter by
            
        Returns:
            List[str]: A list of unique types found in the DeepResearch documents for the user
        """
        # Initialize the database connection
        db_config = MongoDBConfig()
        db = db_config.connect()
        
        # Query the database to find all distinct types for the given user_id
        # The distinct method returns a list of unique values for the specified field
        unique_types = db["deep_research"].distinct("type", {"user_id": user_id})
        
        # Return the list of unique types
        return unique_types
        
        