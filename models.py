from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

db = None

@dataclass
class IToken:
    name: str
    symbol: str
    mint: str
    market_cap: float
    cur_market_cap: float
    pumpfun_age: str
    top10_holder_percentage: float
    holder_count: int
    dev_wallet_percentage: float
    twitter: Optional[str] = ""
    telegram: Optional[str] = ""
    website: Optional[str] = ""
    volume: float = 0
    cur_volume: float = 0
    insider_wallet_percentage: Optional[float] = 0
    sniper_wallet_percentage: Optional[float] = 0
    exchange: str = ""
    msg_id: Optional[int] = None
    forward_msg_id: Optional[int] = None
    forward_mc: Optional[float] = None
    multiple: float = 1
    multiple_mc: Optional[float] = None  # Market cap used when calculating the current multiple
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    forward_at: Optional[datetime] = None
    drop_cnt: int = 0
    _id: Optional[str] = None
    last_alert_mc: Optional[float] = None
    last_alert_at: Optional[datetime] = None
    last_alert_level: Optional[float] = None
    alert_sent: Optional[bool] = None
    call_time: Optional[datetime] = None
    has_been_forwarded: Optional[bool] = None

@dataclass
class IFinancial:
    username: str
    public_key: str
    private_key: str
    balance: float = 0
    promote_time: int = 0
    created_at: Optional[datetime] = None
    _id: Optional[str] = None

@dataclass
class ISetting:
    name: str = "ApexSignal"
    date: int = None
    _id: Optional[str] = None

    def __post_init__(self):
        if self.date is None:
            self.date = datetime.now().day

class Token:
    @staticmethod
    async def find_one(query):
        return await db.tokens.find_one(query)

    @staticmethod
    async def find(query=None):
        if query is None:
            query = {}
        cursor = db.tokens.find(query)
        return await cursor.to_list(length=None)

    @staticmethod
    async def insert_one(data):
        if isinstance(data, IToken):
            data.created_at = datetime.now()
            data.updated_at = datetime.now()
            doc = asdict(data)
        elif isinstance(data, dict):
            doc = data.copy()
            doc['created_at'] = datetime.now()
            doc['updated_at'] = datetime.now()
        else:
            doc = data
            doc['created_at'] = datetime.now()
            doc['updated_at'] = datetime.now()

        result = await db.tokens.insert_one(doc)
        return result.inserted_id

    @staticmethod
    async def update_one(query, update_data):
        if '$set' not in update_data:
            update_data = {'$set': update_data}
        update_data['$set']['updated_at'] = datetime.now()
        return await db.tokens.update_one(query, update_data)

    @staticmethod
    async def delete_one(query):
        return await db.tokens.delete_one(query)

class Financial:
    @staticmethod
    async def find_one(query):
        return await db.financials.find_one(query)

    @staticmethod
    async def find(query=None):
        if query is None:
            query = {}
        cursor = db.financials.find(query)
        return await cursor.to_list(length=None)

    @staticmethod
    async def insert_one(data):
        if isinstance(data, IFinancial):
            data.created_at = datetime.now()
            doc = asdict(data)
        elif isinstance(data, dict):
            doc = data.copy()
            doc['created_at'] = datetime.now()
        else:
            doc = data
            doc['created_at'] = datetime.now()

        result = await db.financials.insert_one(doc)
        return result.inserted_id

    @staticmethod
    async def update_one(query, update_data):
        if '$set' not in update_data:
            update_data = {'$set': update_data}
        return await db.financials.update_one(query, update_data)

class Setting:
    @staticmethod
    async def find_one(query):
        return await db.settings.find_one(query)

    @staticmethod
    async def insert_one(data):
        if isinstance(data, ISetting):
            doc = asdict(data)
        elif isinstance(data, dict):
            doc = data.copy()
        else:
            doc = data

        result = await db.settings.insert_one(doc)
        return result.inserted_id

    @staticmethod
    async def update_one(query, update_data, upsert=False):
        if '$set' not in update_data:
            update_data = {'$set': update_data}
        return await db.settings.update_one(query, update_data, upsert=upsert)

async def init_models(database):
    global db
    db = database

    try:
        await db.tokens.create_index([("mint", 1)], unique=True)
        await db.financials.create_index([("username", 1)], unique=True)
        await db.settings.create_index([("name", 1)], unique=True)
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {e}")