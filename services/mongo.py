import os
from dotenv import load_dotenv
import pymongo
import logging
from pymongo.mongo_client import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class MongoDBConfig:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGODB_URI")  # Default URI
        self.database_name = os.getenv("MONGODB_DATABASE_NAME")  # Default database name
        self.client = None
        self.db = None

    def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.database_name]
            return self.db
        except pymongo.errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
