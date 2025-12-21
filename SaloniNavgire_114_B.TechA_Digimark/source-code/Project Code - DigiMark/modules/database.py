from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/last')

try:
    client = MongoClient(MONGO_URI)
    db = client['last']
    teachers_collection = db['teachers']
    
    # Create unique index on email
    teachers_collection.create_index('email', unique=True)
    
    print("✅ MongoDB Connected Successfully")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")
    db = None
    teachers_collection = None
