
import os
from dotenv import load_dotenv
from solders.keypair import Keypair
import base58

load_dotenv()

class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")

        self.SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

        main_private_key = os.getenv('MAIN_PRIVATE_KEY', '')
        if main_private_key:
            try:
                self.MAIN_KEYPAIR = Keypair.from_bytes(base58.b58decode(main_private_key))
            except Exception as e:
                print(f"Error loading main keypair: {e}")
                self.MAIN_KEYPAIR = Keypair()
        else:
            self.MAIN_KEYPAIR = Keypair()
            print(f"Generated new main keypair: {self.MAIN_KEYPAIR.pubkey()}")

        self.GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '')  # Group chat ID (starts with -)
        self.INITIAL_CALL_TOPIC_ID = int(os.getenv('INITIAL_CALL_TOPIC_ID', '0'))  # Topic ID within the group
        self.FREE_CALL_CHANNEL = os.getenv('FREE_CALL_CHANNEL', '@your_free_channel')
        self.PREMIUM_CHANNEL = os.getenv('PREMIUM_CHANNEL', '@your_premium_channel')
        self.REFERER_HANDER = os.getenv('REFERER_HANDER', '')

        self.PROMOTE_FEE = float(os.getenv('PROMOTE_FEE', '0.1'))

        self.SCAN_AMM_INTERVAL = int(os.getenv('SCAN_AMM_INTERVAL', '10000'))

        self.MIN_MC = float(os.getenv('MIN_MC', '100000'))
        self.LIMIT_TIME = float(os.getenv('LIMIT_TIME', '60'))
        self.MIN_ALERT_VOLUME = float(os.getenv('MIN_ALERT_VOLUME', '200000'))

        self.MIN_DEV_HOLD_PCT = float(os.getenv('MIN_DEV_HOLD_PCT', '1'))
        self.MAX_DEV_HOLD_PCT = float(os.getenv('MAX_DEV_HOLD_PCT', '15'))
        self.MIN_TOP10HOLD_PCT = float(os.getenv('MIN_TOP10HOLD_PCT', '10'))
        self.MAX_TOP10HOLD_PCT = float(os.getenv('MAX_TOP10HOLD_PCT', '50'))

        self.ALERT_MULTIPLE_LIMIT = 2.0
        self.ALERT_CHECK_INTERVAL = int(os.getenv('ALERT_CHECK_INTERVAL', '1800'))  # 30 minutes in seconds
        self.FREE_CHANNEL_FORWARD_MULTIPLE = float(os.getenv('FREE_CHANNEL_FORWARD_MULTIPLE', '5.0'))

        self.PORT = int(os.getenv('PORT', '3000'))