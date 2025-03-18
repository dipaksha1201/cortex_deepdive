import logging
from typing import List, Literal
from services.mongo import MongoDBConfig
from services.models import Document
from bson.objectid import ObjectId

# Configure a logger for this module.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        # In-memory store for conversations; replace with a persistent store in production.
        db_config = MongoDBConfig()
        self.db = db_config.connect()
        logger.info("DocumentService initialized and database connected.")

    def insert_document(self, document: Document) -> Document:
        # Insert into MongoDB 'documents' collection
        result = self.db["documents"].insert_one(document.model_dump())
        # Assign the generated _id to the document dict
        document.id = str(result.inserted_id)
        # Return a new Document instance with the inserted data
        return document

    def get_user_documents(self, user_id: str) -> List[Document]:
        """Retrieve all documents for a specific user."""
        logger.info("Retrieving documents for user_id: %s", user_id)
        # Query the database for documents that match the given user_id.
        documents = self.db["documents"].find({"user_id": user_id})
        documents = [Document(**doc) for doc in documents]
        logger.info("Found %d documents for user '%s'", len(documents), user_id)
        return documents

    def get_document_by_id(self, document_id: str) -> Document:
        """Retrieve a document by its ID."""
        logger.info("Retrieving document with id: %s", document_id)
        result = self.db["documents"].find_one({"_id": ObjectId(document_id)})
        if not result:
            raise ValueError(f"Document with id {document_id} not found")
        return Document(**result)

    def delete_document_by_id(self, document_id: str) -> bool:
        """Delete a document by its ID."""
        logger.info("Deleting document with id: %s", document_id)
        result = self.db["documents"].delete_one({"_id": ObjectId(document_id)})
        if result.deleted_count == 0:
            raise ValueError(f"Document with id {document_id} not found")
        logger.info("Document with id %s deleted successfully", document_id)
        return True


