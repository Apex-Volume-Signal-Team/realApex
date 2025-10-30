# init cybernate 

import os
import asyncio
import base58
from datetime import datetime
from typing import Optional, Dict, Any
import concurrent.futures

import telebot
from telebot import types
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import threading

from config import Config
from db import connect_db, disconnect_db
from models import Setting, IFinancial
from services import TokenService, FinancialService, SettingService
from commands import start_bot_msg, promote_time_msg, promote_msg, admin_promote_msg
from utils import create_msg, reply_msg, promotion_msg, sleep, check_database_for_alerts
# from api import get_mevx_info, get_mevx_promotion_info, get_mevx_token_holders
from api import get_tracker_info, get_tracker_promotion_info, get_tracker_token_holders

app = FastAPI()

@app.get("/")
async def health_check():
    return JSONResponse({"message": "Backend Server is Running now!"})

class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.bot = telebot.TeleBot(self.config.BOT_TOKEN)
        self.wallet_kp = None
        self.promotion = False
        self.username = ""
        self.solana_client = AsyncClient(self.config.SOLANA_RPC_URL)
        self.call_cnt = {"count": 0}
        self.user_states = {}
        self.loop = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    async def setup(self):
        """Initialize the bot and database"""
        await connect_db()

        setting = await Setting.find_one({"name": "ApexSignal"})
        if not setting:
            bot_setting = {"name": "ApexSignal", "date": datetime.now().day}
            await Setting.insert_one(bot_setting)

        self.bot.set_my_commands([
            telebot.types.BotCommand("start", "Start the bot"),
            telebot.types.BotCommand("promote", "Token promotion"),
            telebot.types.BotCommand("remove", "Remove token (Admin only)")
        ])

        self.register_handlers()

    def register_handlers(self):
        """Register message handlers"""

        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            # Only respond to start command in private messages (DMs)
            if message.chat.type == 'private':
                self.run_async_in_executor(self.handle_start(message))

        @self.bot.message_handler(commands=['promote'])
        def promote_command(message):
            # Only respond to promote command in private messages (DMs)
            if message.chat.type == 'private':
                self.run_async_in_executor(self.handle_promote(message))

        @self.bot.message_handler(commands=['remove'])
        def remove_command(message):
            # Only respond to remove command in private messages (DMs)
            if message.chat.type == 'private':
                self.run_async_in_executor(self.handle_remove(message))

        @self.bot.message_handler(func=lambda message: True)
        def handle_text(message):
            # Only respond to text messages in private messages (DMs)
            if message.chat.type == 'private':
                self.run_async_in_executor(self.handle_message(message))

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self.run_async_in_executor(self.handle_callback_query(call))

    def run_async_in_executor(self, coro):
        """Run async coroutine in executor"""
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            try:
                future.result(timeout=30)
            except Exception as e:
                print(f"Error running async task: {e}")

    async def handle_start(self, message):
        """Handle /start command"""
        try:
            self.bot.send_message(message.chat.id, "Please wait a moment...")

            self.username = message.from_user.username or str(message.from_user.id)
            self.user_states[message.from_user.id] = {"promotion": False, "username": self.username}

            data = await FinancialService.get_wallet_by_username(self.username)

            if data:
                self.wallet_kp = Keypair.from_bytes(base58.b58decode(data['private_key']))
            else:
                self.wallet_kp = Keypair()
                financial_data = {
                    'username': self.username,
                    'public_key': str(self.wallet_kp.pubkey()),
                    'private_key': base58.b58encode(bytes(self.wallet_kp)).decode(),
                    'balance': 0,
                    'promote_time': 0
                }
                await FinancialService.create_financial(financial_data)

            wallet_msg = start_bot_msg(str(self.wallet_kp.pubkey()))
            self.bot.send_message(message.chat.id, wallet_msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Error in handle_start: {e}")
            self.bot.send_message(message.chat.id, "An error occurred. Please try again.")

    async def handle_promote(self, message):
        """Handle /promote command"""
        try:
            user_state = self.user_states.get(message.from_user.id, {})

            if self.wallet_kp and not user_state.get("promotion", False):
                promo_time_msg = promote_time_msg()
                self.bot.send_message(message.chat.id, promo_time_msg)
            else:
                self.bot.send_message(message.chat.id, "Please create a wallet first by using /start command.")
        except Exception as e:
            print(f"Error in handle_promote: {e}")

    async def handle_remove(self, message):
        """Handle /remove command - Admin only"""
        try:
            user_id = message.from_user.id
            
            # Check if user is admin
            if user_id not in self.config.ADMIN_USER_IDS:
                self.bot.send_message(message.chat.id, "❌ Unauthorized. This command is for admins only.")
                return

            # Parse command text
            text_parts = message.text.strip().split()
            
            if len(text_parts) != 2:
                self.bot.send_message(
                    message.chat.id, 
                    "❌ Invalid format. Use: /remove {mint_address}\n\nExample: /remove 47BpfH7SbcVJHmQeHVRogHjyFTqoy6ggvDzxotEapump"
                )
                return

            mint_address = text_parts[1].strip()
            
            # Validate mint address format (basic check)
            if len(mint_address) < 32 or len(mint_address) > 44:
                self.bot.send_message(message.chat.id, "❌ Invalid mint address format.")
                return

            # Check if token exists in database
            token = await TokenService.get_token_by_mint(mint_address)
            
            if not token:
                self.bot.send_message(
                    message.chat.id, 
                    f"❌ Token not found in database.\n\nMint: `{mint_address}`", 
                    parse_mode='Markdown'
                )
                return

            # Attempt to delete token
            deletion_success = await TokenService.delete_token(mint_address)
            
            if deletion_success:
                token_name = token.get('name', 'Unknown')
                token_symbol = token.get('symbol', 'N/A')
                
                self.bot.send_message(
                    message.chat.id,
                    f"✅ Token successfully removed from database.\n\n"
                    f"**Name:** {token_name}\n"
                    f"**Symbol:** ${token_symbol}\n"
                    f"**Mint:** `{mint_address}`\n\n"
                    f"All associated data has been deleted.",
                    parse_mode='Markdown'
                )
                
                print(f"🗑️ Admin {user_id} removed token: {token_name} ({mint_address})")
            else:
                self.bot.send_message(
                    message.chat.id, 
                    f"❌ Failed to remove token from database.\n\nMint: `{mint_address}`", 
                    parse_mode='Markdown'
                )
                print(f"❌ Failed to delete token {mint_address} from database")

        except Exception as e:
            print(f"Error in handle_remove: {e}")
            self.bot.send_message(message.chat.id, "❌ An error occurred while processing the remove command.")

    async def handle_message(self, message):
        """Handle text messages"""
        try:
            text = message.text.strip()
            chat_id = message.chat.id
            user_id = message.from_user.id

            if not self.wallet_kp:
                self.bot.send_message(chat_id, "Please create a wallet first by using /start command.")
                return

            user_state = self.user_states.get(user_id, {})

            if user_state.get("promotion", False):
                payment_details = await FinancialService.get_wallet_by_username(self.username)

                if not payment_details:
                    print(f'No payment record found for user: {self.username}')
                    self.bot.send_message(chat_id, "Please create a wallet first by using /start command.")
                    return

                promote_times = payment_details.get('promote_time', 0)
                for i in range(promote_times):
                    # promotion_data = await get_mevx_promotion_info(text)
                    promotion_data = await get_tracker_promotion_info(text)
                    # holders = await get_mevx_token_holders(text)
                    # holders = await get_tracker_token_holders(text)

                    if not promotion_data or not isinstance(promotion_data, list):
                        print("Error: Invalid data received from get_tracker_promotion_info()")
                        return

                    await promotion_msg(
                        self.bot, 
                        self.config.GROUP_CHAT_ID, 
                        promotion_data[0], 
                        self.config
                    )
                    await sleep(10)

                await FinancialService.update_financial(self.username, {"promote_time": 0})
                self.user_states[user_id]["promotion"] = False
                self.bot.send_message(chat_id, "Promotion successfully booked ✅")

            else:
                try:
                    promote_count = int(text)
                    await FinancialService.update_financial(self.username, {"promote_time": promote_count})

                    if self.username in ["max_tonny88", "thesharkstorm", "TheAlphaRonin"]:
                        promo_msg = admin_promote_msg(text)
                    else:
                        promo_msg = promote_msg(str(self.wallet_kp.pubkey()), promote_count)

                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton("Confirm Payment", callback_data="confirm_payment"))

                    self.bot.send_message(
                        chat_id, 
                        promo_msg, 
                        reply_markup=keyboard, 
                        parse_mode='Markdown'
                    )
                except ValueError:
                    self.bot.send_message(chat_id, "Please enter a valid number for promotion count.")
        except Exception as e:
            print(f"Error in handle_message: {e}")

    async def handle_callback_query(self, call):
        """Handle callback queries"""
        try:
            self.bot.answer_callback_query(call.id)

            if call.data == 'confirm_payment':
                await self.handle_payment_confirmation(call.message.chat.id, call.from_user.username or str(call.from_user.id))
            elif call.data.startswith('ath_'):
                # Handle ATH pagination with timestamp format: ath_{timestamp}_{page}
                try:
                    parts = call.data.split('_')
                    if len(parts) >= 3:
                        # New format: ath_{timestamp}_{page}
                        timestamp = int(parts[1])
                        page = int(parts[2])
                    else:
                        # Fallback for old format: ath_page_{page}
                        page = int(parts[1]) if parts[0] == 'ath' and len(parts) == 2 else int(parts[2])
                    
                    print(f"ATH pagination request: page {page} (callback_data: {call.data})")
                    await self.handle_ath_pagination(call, page)
                except (ValueError, IndexError) as e:
                    print(f"Invalid ATH pagination data: {call.data}, error: {e}")
                    # Since buttons are now persistent, just log the error without showing user error
                    print("Attempting to handle pagination anyway...")
                    try:
                        # Try to extract page number from any position
                        numbers = [int(part) for part in call.data.split('_') if part.isdigit()]
                        if numbers:
                            page = numbers[-1]  # Take the last number as page
                            await self.handle_ath_pagination(call, page)
                        else:
                            raise ValueError("No valid page number found")
                    except:
                        self.bot.answer_callback_query(
                            call.id, 
                            "❌ Invalid page request.", 
                            show_alert=True
                        )
        except Exception as e:
            print(f"Error in handle_callback_query: {e}")
            # Ensure we always answer the callback query
            try:
                self.bot.answer_callback_query(call.id, "❌ An error occurred.", show_alert=True)
            except:
                pass

    async def handle_ath_pagination(self, call, page: int):
        """Handle ATH batch message pagination"""
        try:
            # Calculate 48 hours ago from current time - same filter as send_ath_batch_message
            from datetime import datetime, timedelta
            forty_eight_hours_ago = datetime.now() - timedelta(hours=48)

            # Get tokens with multiple >= 5.0x from the last 48 hours (same as initial message)
            ath_tokens = await TokenService.get_tokens_by_query({
                "multiple": {"$gte": 5.0},
                "created_at": {"$gte": forty_eight_hours_ago}
            })

            if not ath_tokens:
                return

            # Sort by highest multiple first - consistent with send_ath_batch_message
            ath_tokens.sort(key=lambda x: x.get('multiple', 1), reverse=True)

            # Send/edit the requested page
            from utils import send_ath_page
            await send_ath_page(
                self.bot,
                call.message.chat.id,
                ath_tokens,
                page,
                message_id=call.message.message_id
            )

        except Exception as e:
            print(f"Error in handle_ath_pagination: {e}")

    async def handle_payment_confirmation(self, chat_id: int, username: str):
        """Handle payment confirmation"""
        try:
            is_paid = await self.check_payment(username)
            print(f"🚀 ~ handle_payment_confirmation ~ is_paid: {is_paid}")

            if is_paid:
                # Find user_id for this username
                user_id = None
                for uid, state in self.user_states.items():
                    if state.get("username") == username:
                        user_id = uid
                        break

                if user_id:
                    self.user_states[user_id]["promotion"] = True

                self.bot.send_message(
                    chat_id=chat_id,
                    text='Payment verified! 🎉\n\nInput token address for promotion like this:\n47BpfH7SbcVJHmQeHVRogHjyFTqoy6ggvDzxotEapump',
                    parse_mode='Markdown'
                )
            else:
                self.bot.send_message(chat_id, 'Payment not found. Please try again.')
        except Exception as e:
            print(f"Error in handle_payment_confirmation: {e}")

    async def check_payment(self, username: str) -> bool:
        """Check if payment has been made"""
        try:
            if username in ["max_tonny88", "thesharkstorm", "TheAlphaRonin"]:
                return True

            payment_details = await FinancialService.get_wallet_by_username(username)

            if not payment_details:
                print(f'No payment record found for user: {username}')
                return False

            public_key = payment_details['public_key']
            balance = payment_details.get('balance', 0)
            promote_time = payment_details.get('promote_time', 0)

            required_amount = self.config.PROMOTE_FEE * promote_time

            if balance >= required_amount:
                transfer_signature = await self.transfer_sol(
                    self.config.MAIN_KEYPAIR, 
                    Pubkey.from_string(public_key), 
                    self.config.PROMOTE_FEE * promote_time
                )
                print(f'Transfer signature: {transfer_signature}')

                await FinancialService.update_financial(username, {
                    "balance": balance - required_amount
                })
                return True

            deposit_pub = Pubkey.from_string(public_key)
            balance_response = await self.solana_client.get_balance(deposit_pub, commitment=Confirmed)
            balance_in_lamports = balance_response.value
            balance_in_sol = balance_in_lamports / 1_000_000_000

            print(f'Wallet {public_key} balance: {balance_in_sol} SOL')

            if balance_in_sol >= required_amount:
                await FinancialService.update_financial(username, {
                    "balance": balance_in_sol
                })

                transfer_signature = await self.transfer_sol(
                    self.config.MAIN_KEYPAIR, 
                    deposit_pub, 
                    required_amount
                )
                print(f'Transfer signature: {transfer_signature}')

                await FinancialService.update_financial(username, {
                    "balance": balance_in_sol - required_amount
                })

                return True

            return False

        except Exception as error:
            print(f'Error checking payment: {error}')
            return False

    async def transfer_sol(self, from_keypair: Keypair, to_address: Pubkey, amount_in_sol: float) -> str:
        """Transfer SOL between wallets"""
        try:
            lamports = int(amount_in_sol * 1_000_000_000)

            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=from_keypair.pubkey(),
                    to_pubkey=to_address,
                    lamports=lamports
                )
            )

            transaction = Transaction([transfer_instruction])
            response = await self.solana_client.send_transaction(
                transaction, 
                [from_keypair],
                opts={"skip_confirmation": False}
            )

            return str(response.value)

        except Exception as error:
            print(f'Transfer failed: {error}')
            raise error

    async def start_monitoring(self):
        """Start token monitoring loop with separate processes"""
        last_background_update = 0
        last_alert_check = 0
        last_ath_daily_send = 0

        while True:
            try:
                print('\033[2J\033[H')
                print("\033[32mPumpfun Volume Notify Bot\033[0m\n")

                # data = await get_mevx_info()
                data = await get_tracker_info()

                if not data or not isinstance(data, list):
                    # print("Error: Invalid data received from get_mevx_info()")
                    print("Error: Invalid data received from get_tracker_info()")
                    await sleep(self.config.SCAN_AMM_INTERVAL / 1000)
                    continue

                for element in data:
                    try:
                        # mint_address = element.get('baseToken', '')
                        mint_address = element.get('token', {}).get('mint', '')
                        if not mint_address:
                            print("❌ No mint address found in element, skipping")
                            continue

                        # Double-check token doesn't exist in database to prevent duplicates
                        cmp_mint = await TokenService.get_token_by_mint(mint_address)

                        if cmp_mint:
                            # Token already exists - skip calling (background monitoring handles updates)
                            print(f"🔄 Token {mint_address} already exists in database - skipping duplicate call")
                            continue
                        else:
                            print(f"🚀 ~ create_data ~ new token: {mint_address}")
                            await create_msg(
                                self.bot,
                                self.config.GROUP_CHAT_ID,
                                element,
                                self.config
                            )

                    except Exception as error:
                        print(f"Error processing element: {error}")
                        print(f"Debug - Element that caused error: {element}")
                        print(f"Debug - Error type: {type(error).__name__}")
                        import traceback
                        print(f"Debug - Full traceback: {traceback.format_exc()}")

                import time
                current_time = time.time()

                # Background token data updates every 10 seconds
                if current_time - last_background_update >= 10:
                    print("Running background token data updates...")
                    from utils import background_token_monitoring
                    await background_token_monitoring(
                        self.bot,
                        self.config.GROUP_CHAT_ID,
                        self.config.FREE_CALL_CHANNEL,
                        self.config
                    )
                    last_background_update = current_time

                # Check database for alerts every 5 seconds
                if current_time - last_alert_check >= 5:
                    print("Checking database for alert conditions...")
                    from utils import check_database_for_alerts
                    await check_database_for_alerts(
                        self.bot,
                        self.config.GROUP_CHAT_ID,
                        self.config
                    )
                    last_alert_check = current_time

                # Send daily ATH message at 7pm UTC (19:00) - PROTECTED TIMING
                from datetime import datetime, timezone
                now_utc = datetime.now(timezone.utc)
                # Check for 7pm UTC window (19:00-19:05) and ensure we haven't sent in the last 23 hours
                if (now_utc.hour == 19 and 0 <= now_utc.minute <= 5 and 
                    current_time - last_ath_daily_send >= 82800):  # 23 hours to ensure once per day
                    print(f"Sending daily ATH message at 7pm UTC (current time: {now_utc.hour:02d}:{now_utc.minute:02d})...")
                    try:
                        from utils import send_ath_batch_message
                        await send_ath_batch_message(
                            self.bot,
                            self.config.FREE_CALL_CHANNEL
                        )
                        last_ath_daily_send = current_time
                        print("✅ Daily ATH message sent successfully")
                    except Exception as ath_error:
                        print(f"❌ Error sending daily ATH message: {ath_error}")
                        # Don't update last_ath_daily_send if sending failed, so it can retry

                await sleep(self.config.SCAN_AMM_INTERVAL / 1000)

            except Exception as error:
                print(f"Error in monitoring loop: {error}")
                await sleep(10)

    async def send_initial_ath_batch(self):
        """Send initial ATH batch message when bot starts"""
        try:
            print("Sending initial ATH batch message...")
            from utils import send_ath_batch_message
            await send_ath_batch_message(
                self.bot,
                self.config.FREE_CALL_CHANNEL
            )
        except Exception as e:
            print(f"Error sending initial ATH batch message: {e}")

    def start_polling(self):
        """Start bot polling"""
        try:
            self.bot.polling(none_stop=True, interval=0)
        except Exception as e:
            print(f"Polling error: {e}")

    async def run(self):
        """Run the bot"""
        await self.setup()

        self.loop = asyncio.get_running_loop()

        print(f"Bot started successfully!")

        polling_thread = threading.Thread(target=self.start_polling, daemon=True)
        polling_thread.start()

        await self.start_monitoring()

async def run_server():
    """Run FastAPI server"""
    config = uvicorn.Config(app, host="0.0.0.0", port=3000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Main function"""
    bot = TelegramBot()

    # Send initial ATH batch message when bot starts
    asyncio.create_task(bot.send_initial_ath_batch())

    await asyncio.gather(
        run_server(),
        bot.run()
    )

if __name__ == "__main__":
    asyncio.run(main())