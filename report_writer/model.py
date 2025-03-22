from pydantic import BaseModel
from typing import List
from report_writer.state import Section
from typing import Literal
from services.mongo import MongoDBConfig
from bson.objectid import ObjectId

class DeepResearch(BaseModel):
    id: str = ""
    user_id: str = ""
    project_id: str = ""
    topic: str = ""
    description: str = ""
    plan: List[Section] = []
    sources: List[str] = []
    status: Literal["to_be_started" , "in_planning","in_progress", "completed"] = "to_be_started"
    report: str = ""
    
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
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"status": status}})
        
    def update_report(self, report: str):
        self.report = report
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"report": report}})
        
    def update_completed_sections(self, completed_sections: List[Section]):
        self.completed_sections = completed_sections
        self.db["deep_research"].update_one({"_id": ObjectId(self.id)}, {"$set": {"completed_sections": completed_sections}})
        
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
        
    def update_sources(self, sources: List[str]):
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
        
        


        