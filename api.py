
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from config import Config

class MevXAPI:
    def __init__(self):
        self.base_url = "https://api.mevx.io/api/v1"

    async def get_mevx_info(self) -> Optional[List[Dict[str, Any]]]:
        """Get token information from MevX API"""
        try:
            params = {
                'chain': 'sol',
                'orderBy': 'createdAt desc',
                'limit': 50,
                'context': 'meme',
                'marketCap[gte]': 100000,
                'volume[gte]': 200000
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/flash/pools", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('pools', [])
                    else:
                        print(f"API request failed with status: {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching MevX info: {e}")
            return None

    async def get_mevx_promotion_info(self, token_address: str) -> Optional[List[Dict[str, Any]]]:
        """Get promotion information for a specific token"""
        try:
            params = {
                'q': token_address.strip(),
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/pools/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('pools', [])
                    else:
                        print(f"API request failed with status: {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching MevX promotion info: {e}")
            return None

    async def get_mevx_token_holders(self, token_address: str) -> Optional[int]:
        """Get holder count for a specific token"""
        try:
            params = {
                'chain': 'sol',
                'token': token_address.strip(),
                'limit': 100,
                'orderBy': 'amount desc'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/holders", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('totalSize', 0)
                    else:
                        print(f"API request failed with status: {response.status}")
                        return 0
        except Exception as e:
            print(f"Error fetching MevX token holders: {e}")
            return 0

class SolanaTrackerAPI:
    def __init__(self):
        self.config = Config()
        self.base_url = "https://data.solanatracker.io"
        self.headers = {"x-api-key": self.config.SOLANA_TRACKER_API_KEY}

    async def get_tracker_info(self) -> Optional[List[Dict[str, Any]]]:
        """Get token information from SolanaTracker API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/tokens/trending", headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # print(f"Trackder response data: ", data)
                        return data
                    else:
                        print(f"API request failed with status: {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching Solana Tracker info: {e}")
            return None

    async def get_tracker_promotion_info(self, token_address: str) -> Optional[List[Dict[str, Any]]]:
        """Get promotion information for a specific token"""
        try:
            querystring = {"page":"1","limit":"100","sortBy":"createdAt","sortOrder":"desc"}

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/search", headers=self.headers, params=querystring) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        print(f"API request failed with status: {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching Solana Tracker promotion info: {e}")
            return None

    async def get_tracker_token_holders(self, token_address: str) -> Optional[int]:
        """Get holder count for a specific token"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/tokens/{token_address.strip()}/holders", headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('totalSize', 0)
                    else:
                        print(f"API request failed with status: {response.status}")
                        return 0
        except Exception as e:
            print(f"Error fetching Solana Tracker token holders: {e}")
            return 0


class DexScreenerAPI:
    def __init__(self):
        self.base_url = "https://api.dexscreener.com"

    async def get_tokens_batch(self, token_addresses: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Get token data for multiple addresses (up to 25) in a single request"""
        try:
            if not token_addresses or len(token_addresses) > 25:
                print(f"Invalid batch size: {len(token_addresses) if token_addresses else 0}. Max 25 addresses per request.")
                return None

            # Join addresses with commas
            addresses_str = ",".join(token_addresses)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/tokens/v1/solana/{addresses_str}",
                    headers={"Accept": "*/*"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"DEXScreener API response received: {len(data) if isinstance(data, list) else 0} pairs")
                        return data if isinstance(data, list) else []
                    else:
                        print(f"DEXScreener API request failed with status: {response.status}")
                        response_text = await response.text()
                        print(f"Response: {response_text}")
                        return None
        except Exception as e:
            print(f"Error fetching DEXScreener batch data: {e}")
            return None

mevx_api = MevXAPI()
tracker_api = SolanaTrackerAPI()
dexscreener_api = DexScreenerAPI()

async def get_mevx_info():
    return await mevx_api.get_mevx_info()

async def get_mevx_promotion_info(token_address: str):
    return await mevx_api.get_mevx_promotion_info(token_address)

async def get_mevx_token_holders(token_address: str):
    return await mevx_api.get_mevx_token_holders(token_address)

async def get_tracker_info():
    return await tracker_api.get_tracker_info()

async def get_tracker_promotion_info(token_address: str):
    return await tracker_api.get_tracker_promotion_info(token_address)

async def get_tracker_token_holders(token_address: str):
    return await tracker_api.get_tracker_token_holders(token_address)

async def get_dexscreener_tokens_batch(token_addresses: List[str]):
    return await dexscreener_api.get_tokens_batch(token_addresses)


