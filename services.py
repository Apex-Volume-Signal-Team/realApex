
from models import Token, Financial, Setting, IToken, IFinancial, ISetting
from typing import Optional, Dict, Any
from datetime import datetime

class TokenService:
    @staticmethod
    async def get_token_by_mint(mint: str) -> Optional[Dict[str, Any]]:
        """Get token by mint address"""
        return await Token.find_one({"mint": mint})

    @staticmethod
    async def create_token(token_data: IToken) -> str:
        """Create a new token"""
        return await Token.insert_one(token_data)

    @staticmethod
    async def update_token(mint: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update token by mint address"""
        result = await Token.update_one({"mint": mint}, update_data)
        if result.modified_count > 0:
            return await Token.find_one({"mint": mint})
        return None

    @staticmethod
    async def delete_token(mint: str) -> bool:
        """Delete token by mint address"""
        result = await Token.delete_one({"mint": mint})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_tokens() -> list:
        """Get all tokens"""
        return await Token.find()

    @staticmethod
    async def get_tokens_called_today() -> list:
        """Get tokens called in the last 24 hours"""
        from datetime import datetime, timedelta
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        return await Token.find({"created_at": {"$gte": twenty_four_hours_ago}})

    @staticmethod
    async def get_tokens_for_alert_check() -> list:
        """Get tokens that need alert checking"""
        from datetime import datetime, timedelta
        five_days_ago = datetime.now() - timedelta(hours=120)
        return await Token.find({
            "created_at": {"$gte": five_days_ago},
            "msg_id": {"$exists": True}
        })

    @staticmethod
    async def get_tokens_by_query(query: Dict[str, Any]) -> list:
        """Get tokens by custom query"""
        return await Token.find(query)

class FinancialService:
    @staticmethod
    async def get_wallet_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Get wallet by username"""
        return await Financial.find_one({"username": username})

    @staticmethod
    async def create_financial(financial_data: IFinancial) -> str:
        """Create a new financial record"""
        return await Financial.insert_one(financial_data)

    @staticmethod
    async def update_financial(username: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update financial record by username"""
        result = await Financial.update_one({"username": username}, update_data)
        if result.modified_count > 0:
            return await Financial.find_one({"username": username})
        return None

    @staticmethod
    async def get_all_financials() -> list:
        """Get all financial records"""
        return await Financial.find()

class SettingService:
    @staticmethod
    async def get_bot_setting() -> Optional[Dict[str, Any]]:
        """Get bot setting"""
        return await Setting.find_one({"name": "ApexSignal"})

    @staticmethod
    async def update_bot_setting(date: int) -> Optional[Dict[str, Any]]:
        """Update bot setting date"""
        result = await Setting.update_one(
            {"name": "ApexSignal"}, 
            {"date": date}
        )
        if result.modified_count > 0:
            return await Setting.find_one({"name": "ApexSignal"})
        return None

    @staticmethod
    async def create_bot_setting() -> str:
        """Create bot setting"""
        setting_data = ISetting()
        return await Setting.insert_one(setting_data)

    @staticmethod
    async def get_ath_message_id() -> Optional[int]:
        """Get ATH message ID from database"""
        setting = await Setting.find_one({"name": "ath_message_id"})
        if setting:
            return setting.get('message_id')
        return None

    @staticmethod
    async def set_ath_message_id(message_id: int) -> None:
        """Set ATH message ID in database"""
        await Setting.update_one(
            {"name": "ath_message_id"},
            {"message_id": message_id, "updated_at": datetime.now()},
            upsert=True
        )