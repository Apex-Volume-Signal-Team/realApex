
import os
from motor.motor_asyncio import AsyncIOMotorClient
from models import init_models

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

client = None
db = None

async def connect_db():
    global client, db
    try:
        print(f"Connecting to MongoDB with URI: {MONGODB_URI}")
        client = AsyncIOMotorClient(MONGODB_URI)
        if '/' in MONGODB_URI and len(MONGODB_URI.split('/')) > 3:
            db_name = MONGODB_URI.split('/')[-1]
            if '?' in db_name:
                db_name = db_name.split('?')[0]
            if not db_name:
                db_name = 'apexDB'
        else:
            db_name = 'apexDB'

        print(f"Using database name: {db_name}")
        db = client[db_name]

        await client.admin.command('ping')
        print(f'MongoDB connected successfully to database: {db_name}')

        await init_models(db)

        return db
    except Exception as error:
        print(f'MongoDB connection error: {error}')
        raise error

async def disconnect_db():
    global client
    if client:
        client.close()
        print('MongoDB disconnected')
