# init pyyy
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from services import TokenService, SettingService
from commands import display_msg, multiple_msg, forward_msg, link_btn, alert_msg
# from api import get_mevx_token_holders, get_mevx_info
from api import get_tracker_info, get_tracker_token_holders

async def sleep(seconds: int):
    """Async sleep function"""
    await asyncio.sleep(seconds)

def get_token_history_by_timestamp(block_time: int) -> Dict[str, Any]:
    """Calculate token age from timestamp"""
    mint_time = datetime.fromtimestamp(block_time)
    current_time = datetime.now()

    time_difference_ms = (current_time - mint_time).total_seconds() * 1000
    total_minutes = time_difference_ms / 1000 / 60
    total_hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)

    hours_str = f"0{total_hours}h" if total_hours < 10 else f"{total_hours}h"
    minutes_str = f"0{minutes}m" if minutes < 10 else f"{minutes}m"

    return {
        "type": f"{hours_str} : {minutes_str}",
        "minutes": total_minutes,
    }

async def promotion_msg(bot, channel_handle: str, element: Dict[str, Any], config):
    """Send promotion message"""
    try:
        pumpfun_age = get_token_history_by_timestamp(element.get('createdAt', 0))

        social = element.get('socials', {})
  
        data_msg = {
            'name': element.get('name', ''),
            'symbol': element.get('symbol', ''),
            'mint': element.get('mint', ''),
            'marketCap': element.get('marketCapUsd', 0),
            'pumpfunAge': pumpfun_age['type'],
            'top10HolderPercentage': element.get('top10', 0),
            'holderCount': element.get('holders',0),
            'devWalletPercentage': element.get('dev', 0),
            'twitter': social.get('twitter', ''),
            'telegram': social.get('telegram', ''),
            'website': social.get('website', ''),
            'volume': element.get('volume', 0),
            'insiderWalletPercentage': element.get('insiders', 0),
            'sniperWalletPercentage': element.get('snipers', 0),
            'exchange': element.get('market', ''),
            'multiple': 1,
        }

        msg = display_msg(data_msg)
        btn = link_btn(element.get('baseToken', ''), data_msg.get('symbol', ''))

        from telebot import types
        keyboard = types.InlineKeyboardMarkup()
        for row in btn['content']:
            keyboard_row = []
            for button in row:
                keyboard_row.append(types.InlineKeyboardButton(button['text'], url=button.get('url', '')))
            keyboard.add(*keyboard_row)

        bot.send_message(
            channel_handle, 
            msg, 
            reply_markup=keyboard, 
            parse_mode="HTML", 
            disable_web_page_preview=True,
            message_thread_id=config.INITIAL_CALL_TOPIC_ID
        )

        # Send promotion to premium channel too
        bot.send_message(
            config.PREMIUM_CHANNEL,
            msg,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as err:
        print(f"Error sending promotion message: {err}")

async def create_msg(bot, channel_handle: str, element: Dict[str, Any], config):
    """Create new token message using ONLY MevX API data"""
    try:
        # CRITICAL: Check if token already exists first to prevent duplicates
        # mint_address = element.get('baseToken', '')
        base_token_info = element.get('token', {})
        mint_address = base_token_info.get('mint', '')
        if not mint_address:
            print("❌ No mint address found in element")
            return

        # Check if token already exists in database
        existing_token = await TokenService.get_token_by_mint(mint_address)
        if existing_token:
            print(f"🔄 Token {mint_address} already exists in database - skipping duplicate call")
            return

        pumpfun_age = get_token_history_by_timestamp(element.get('token', {}).get('creation', {}).get('created_time', 0))

        # Filter conditions using MevX data
        if pumpfun_age['minutes'] > config.LIMIT_TIME:
            return

        # Use MevX API data structure directly
        risk = element.get('risk', {})
        dev_hold_pct = safe_float_conversion(risk.get('dev', {}).get('percentage', 0), 0)
        top10_hold_pct = safe_float_conversion(risk.get('top10', 0), 0)

        if not (config.MIN_DEV_HOLD_PCT <= dev_hold_pct <= config.MAX_DEV_HOLD_PCT):
            return

        if not (config.MIN_TOP10HOLD_PCT <= top10_hold_pct <= config.MAX_TOP10HOLD_PCT):
            return

        # Get market cap from MevX API response
        market_cap = safe_float_conversion(element.get('pools', [])[0].get('marketCap', {}).get("usd", 0), 0)
        if market_cap < config.MIN_MC:
            return
        
        # Check maximum market cap
        if market_cap > config.MAX_MC:
            return

        # Get volume from MevX API response  
        txns = element.get('pools', [])[0].get('txns', {})
        total_volume = safe_float_conversion(txns.get('volume'), 0)
        if total_volume < config.MIN_ALERT_VOLUME:
            return
        
        # Check maximum alert volume
        if total_volume > config.MAX_ALERT_VOLUME:
            return

        # Get social data from MevX API
        social = element.get('token', {}).get('strictSocials', {})
        
        # Check if token has at least 1 social link
        has_social = bool(
            social.get('twitter') or 
            social.get('telegram') or 
            social.get('website')
        )
        if not has_social:
            return

        # Get exchange info from MevX API
        exchange_name = element.get('pools', [])[0].get('market', '');
        if mint_address.lower().endswith('bonk'):
            exchange_name = 'Bonk.fun'

        # Create token data using only MevX API data
        token_data = {
            'name': base_token_info.get('name', ''),
            'symbol': base_token_info.get('symbol', ''),
            'mint': mint_address,
            'market_cap': market_cap,
            'cur_market_cap': market_cap,
            'pumpfun_age': pumpfun_age['type'],
            'top10_holder_percentage': top10_hold_pct,
            'holder_count': int(element.get('holders', 0)),
            'dev_wallet_percentage': dev_hold_pct,
            'twitter': social.get('twitter', ''),
            'telegram': social.get('telegram', ''),
            'website': social.get('website', ''),
            'volume': total_volume,
            'cur_volume': total_volume,
            'insider_wallet_percentage': safe_float_conversion(risk.get('insiders', {}).get("totalPercentage", 0), 0),
            'sniper_wallet_percentage': safe_float_conversion(risk.get('snipers', {}).get('totalPercentage', 0), 0),
            'exchange': exchange_name,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'multiple': 1.0,
        }

        # Create display message using MevX data
        msg = display_msg({
            'name': token_data['name'],
            'symbol': token_data['symbol'],
            'mint': token_data['mint'],
            'marketCap': token_data['market_cap'],
            'pumpfunAge': token_data['pumpfun_age'],
            'holderCount': token_data['holder_count'],
            'volume': token_data['volume'],
            'devWalletPercentage': token_data['dev_wallet_percentage'],
            'top10HolderPercentage': token_data['top10_holder_percentage'],
            'insiderWalletPercentage': token_data['insider_wallet_percentage'],
            'sniperWalletPercentage': token_data['sniper_wallet_percentage'],
            'twitter': token_data['twitter'],
            'telegram': token_data['telegram'],
            'website': token_data['website'],
            'exchange': token_data['exchange']
        })

        btn = link_btn(element.get('baseToken', ''), token_data['symbol'])

        from telebot import types
        keyboard = types.InlineKeyboardMarkup()
        for row in btn['content']:
            keyboard_row = []
            for button in row:
                keyboard_row.append(types.InlineKeyboardButton(button['text'], url=button.get('url', '')))
            keyboard.add(*keyboard_row)

        from commands import should_show_preview
        disable_preview = not should_show_preview(msg, token_data.get('twitter'))

        # Initialize message IDs
        sent_msg_id = None
        premium_msg_id = None

        # Send message to main group with topic ID
        try:
            sent_msg = bot.send_message(
                channel_handle, 
                msg, 
                reply_markup=keyboard, 
                parse_mode="HTML", 
                disable_web_page_preview=disable_preview,
                message_thread_id=config.INITIAL_CALL_TOPIC_ID
            )
            sent_msg_id = sent_msg.message_id
            print(f"✅ Message sent to main group (topic: {config.INITIAL_CALL_TOPIC_ID}): {token_data['name']}")
        except Exception as main_error:
            print(f"❌ Failed to send to main group: {main_error}")
            # Don't return here - still try to send to premium channel

        # Send to premium channel (standalone, no topic ID)
        try:
            premium_msg = bot.send_message(
                config.PREMIUM_CHANNEL,
                msg,
                reply_markup=keyboard,
                parse_mode="HTML",
                disable_web_page_preview=disable_preview
            )
            premium_msg_id = premium_msg.message_id
            print(f"✅ Message sent to premium channel: {token_data['name']}")
        except Exception as premium_error:
            print(f"❌ Failed to send to premium channel: {premium_error}")

        # Only save to database if at least one message was sent successfully
        if sent_msg_id or premium_msg_id:
            # Save token to database with both message IDs
            if sent_msg_id:
                token_data['msg_id'] = sent_msg_id
            if premium_msg_id:
                token_data['premium_msg_id'] = premium_msg_id
                
            await TokenService.create_token(token_data)
            print(f"✅ Token called and saved: {token_data['name']} ({token_data['symbol']}) - ${format_number(market_cap)} MC")
            print(f"   Main group msg_id: {sent_msg_id}, Premium msg_id: {premium_msg_id}")
        else:
            print(f"❌ Failed to send messages to both channels - token not saved to database")

    except Exception as err:
        print(f"Error creating message: {err}")

async def reply_msg(bot, channel_handle: str, free_channel: str, read_data: Dict[str, Any], element: Dict[str, Any], config, call_cnt: Dict[str, int]):
    """Send reply message for token updates"""
    try:
        print(f"Debug reply_msg - Starting function")

        # Validate required data
        if not element or not read_data:
            print("Error in reply_msg: Missing element or read_data")
            return

        # Debug: Print element structure to understand the data
        print(f"Debug - Element keys: {list(element.keys()) if element else 'None'}")
        print(f"Debug - Read data keys: {list(read_data.keys()) if read_data else 'None'}")

        # Check for marketCap in different possible locations
        market_cap_value = None
        if 'marketCap' in element:
            market_cap_value = element['marketCap']
            print(f"Debug - Found marketCap in element: {market_cap_value} (type: {type(market_cap_value)})")
        elif 'market_cap' in element:
            market_cap_value = element['market_cap']
            print(f"Debug - Found market_cap in element: {market_cap_value} (type: {type(market_cap_value)})")
        elif 'baseTokenInfo' in element and 'marketCap' in element['baseTokenInfo']:
            market_cap_value = element['baseTokenInfo']['marketCap']
            print(f"Debug - Found marketCap in baseTokenInfo: {market_cap_value} (type: {type(market_cap_value)})")
        else:
            print(f"Error in reply_msg: marketCap not found in element. Available keys: {list(element.keys())}")
            print(f"Debug - Full element structure: {element}")
            return

        current_date = datetime.now().day
        bot_info = await SettingService.get_bot_setting()

        drop_count = read_data.get('drop_cnt', 0)

        # Convert values to float to avoid division errors
        current_mc = safe_float_conversion(market_cap_value, 0)
        original_mc = safe_float_conversion(read_data.get('market_cap'), 1)

        print(f"Debug - Current MC after conversion: {current_mc} (type: {type(current_mc)})")
        print(f"Debug - Original MC after conversion: {original_mc} (type: {type(original_mc)})")

        # Ensure original_mc is not zero to avoid division by zero
        if original_mc <= 0:
            print(f"Debug - Original MC was <= 0, setting to 1")
            original_mc = 1

        # Safely access nested dictionaries
        base_token_info = element.get('baseTokenInfo', {})
        report_info = element.get('report', {})

        calculated_multiple = current_mc / original_mc if original_mc > 0 else 1
        current_highest_multiple = read_data.get('multiple', 1)

        update_data = {
            'cur_market_cap': current_mc,
            'top10_holder_percentage': safe_float_conversion(base_token_info.get('top10HoldersPercent'), 0),
            'holder_count': int(safe_float_conversion(base_token_info.get('holderCount'), 0)),
            'dev_wallet_percentage': safe_float_conversion(base_token_info.get('devHoldPercent'), 0),
            'cur_volume': safe_float_conversion(report_info.get('totalVolume'), 0),
            'insider_wallet_percentage': safe_float_conversion(base_token_info.get('insiderHoldPercent'), 0),
            'updated_at': datetime.now(),
            'drop_cnt': drop_count,
        }

        msg_data = {
            'name': read_data['name'],
            'mint': read_data['mint'],
            'marketCap': current_mc,
            'market_cap': read_data.get('market_cap', 0)
        }

        print(f"Debug - About to call multiple_msg with:")
        print(f"Debug - read_data keys: {list(read_data.keys())}")
        print(f"Debug - element keys: {list(element.keys())}")
        print(f"Debug - element marketCap value: {element.get('marketCap', 'NOT_FOUND')}")
        print(f"Debug - current_mc: {current_mc}")

        # Create a safe element copy with guaranteed marketCap
        safe_element = element.copy()
        safe_element['marketCap'] = current_mc
        print(f"Debug - Created safe_element with marketCap: {safe_element['marketCap']}")

        msg = multiple_msg(read_data, safe_element)

        print(f"Debug - About to send message to channel: {channel_handle}")
        print(f"Debug - Message content length: {len(msg)}")
        print(f"Debug - Reply to message ID: {read_data.get('msg_id')}")

        try:
            bot.send_message(
                channel_handle, 
                msg, 
                parse_mode="HTML",
                reply_to_message_id=read_data.get('msg_id'),
                disable_web_page_preview=True,
                message_thread_id=config.INITIAL_CALL_TOPIC_ID
            )
        except Exception as telegram_error:
            # If reply fails (message not found), send without reply
            if "message to be replied not found" in str(telegram_error):
                print(f"Original message not found, sending without reply for {read_data.get('name', 'unknown')}")
                bot.send_message(
                    channel_handle, 
                    msg, 
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    message_thread_id=config.INITIAL_CALL_TOPIC_ID
                )
            else:
                raise telegram_error

        print(f"Debug - Message sent successfully")

        market_cap_ratio = current_mc / original_mc



        await TokenService.update_token(read_data['mint'], update_data)

        if current_date != bot_info.get('date'):
            call_cnt['count'] = 0
            await SettingService.update_bot_setting(current_date)

    except Exception as error:
        print(f"Error in reply_msg: {error}")
        print(f"Debug - Error type: {type(error).__name__}")
        print(f"Debug - Error args: {error.args}")
        import traceback
        print(f"Debug - Full traceback: {traceback.format_exc()}")
        print(f"Debug - Element at error: {element}")
        print(f"Debug - Read data at error: {read_data}")

def safe_float_conversion(value, default=0.0):
    """Safely convert value to float"""
    try:
        if value is None or value == '' or value == 'null' or value == 'undefined':
            print(f"Debug safe_float_conversion - Value is None/empty, returning default: {default}")
            return default
        # Handle string representations of numbers
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                print(f"Debug safe_float_conversion - Empty string after strip, returning default: {default}")
                return default

        result = float(value)
        print(f"Debug safe_float_conversion - Successfully converted {value} to {result}")
        return result
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Debug safe_float_conversion - Failed to convert {value} (type: {type(value)}): {e}")
        print(f"Debug safe_float_conversion - Returning default: {default}")
        return default





def format_number(num: float) -> str:
    """Format numbers with K, M, B suffixes"""
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    if num >= 1_000:
        return f"{num / 1_000:.2f}k"
    return str(num)

async def background_token_monitoring(bot, channel_handle: str, free_channel: str, config):
    """Background monitoring: ONLY update token data (multiple, cur_market_cap, etc.)"""
    try:
        tokens = await TokenService.get_tokens_for_alert_check()
        print(f"Background monitoring {len(tokens)} tokens...")

        if not tokens:
            return

        # Extract token addresses for batch processing
        token_addresses = [token['mint'] for token in tokens]

        # Get current data for all tokens in batches (25 addresses per batch)
        current_data_map = await get_current_token_data_batch(token_addresses)

        for token in tokens:
            try:
                # Get current market data for this token from the batch results
                current_data = current_data_map.get(token['mint'])
                if not current_data:
                    continue

                current_mc = current_data.get('marketCap', 0)
                current_volume = current_data.get('volume', 0)
                initial_mc = token['market_cap']
                current_highest_multiple = token.get('multiple', 1)

                # Calculate current multiple
                multiple = current_mc / initial_mc if initial_mc > 0 else 0

                # Always update token data with current values
                update_data = {
                    'cur_market_cap': current_mc,
                    'cur_volume': current_volume,
                    'updated_at': datetime.now()
                }

                # Update the highest multiple achieved if current multiple is higher
                if multiple > current_highest_multiple:
                    update_data['multiple'] = round(multiple, 1)
                    update_data['multiple_mc'] = current_mc
                    print(f"Background update: {token.get('name', 'unknown')} new highest multiple: {multiple:.2f}x")



                # Always update token data to keep current values fresh
                await TokenService.update_token(token['mint'], update_data)

            except Exception as e:
                print(f"Error in background monitoring for {token.get('mint', 'unknown')}: {e}")
                continue

    except Exception as e:
        print(f"Error in background_token_monitoring: {e}")

async def check_database_for_alerts(bot, channel_handle: str, config):
    """Check database every 10 seconds for tokens that meet alert criteria - DATABASE ONLY"""
    try:
        # Get tokens that might need alerts (>=2.0x multiple, have msg_id)
        tokens = await TokenService.get_tokens_by_query({
            "multiple": {"$gte": 2.0},
            "msg_id": {"$exists": True}
        })

        print(f"Database alert check: {len(tokens)} tokens with >=2.0x multiple...")

        if not tokens:
            return

        for token in tokens:
            try:
                # Get values from database for alert logic - NO API CALLS
                stored_multiple = token.get('multiple', 1.0)  # Highest multiple achieved (updated by background monitoring)
                last_alert_level = token.get('last_alert_level', 0.0)  # Last alerted level
                current_mc = token.get('cur_market_cap', 0)  # Current market cap from database

                # Use database multiple for alert logic
                current_multiple_to_check = stored_multiple

                print(f"🔍 Alert check: {token.get('name', 'unknown')} - DB Multiple: {stored_multiple:.1f}x, Last Alert: {last_alert_level:.1f}x")

                # RULE 1: First alert - token has >=2.0x multiple but never sent alert
                if current_multiple_to_check >= 2.0 and (last_alert_level == 0.0 or last_alert_level is None):
                    alert_level_to_send = current_multiple_to_check

                    print(f"🚨 FIRST ALERT: {token.get('name', 'unknown')} {current_multiple_to_check:.1f}x → sending first alert")

                    # Send alert with database values
                    await send_token_alert(bot, channel_handle, token, current_mc, alert_level_to_send, config)

                    # Update ONLY alert-specific fields - preserve multiple and multiple_mc
                    update_data = {
                        'last_alert_level': round(alert_level_to_send, 1),
                        'last_alert_at': datetime.now(),
                        'alert_sent': True,
                        'updated_at': datetime.now()
                    }

                    # Update database with alert info only
                    await TokenService.update_token(token['mint'], update_data)

                    # Check for forwarded message requirement (>=5.0x and not already forwarded)
                    has_been_forwarded = token.get('has_been_forwarded', False)
                    forwarded_msg_id = token.get('forwarded_msg_id')
                    print(f"🔍 FORWARD CHECK: {token.get('name', 'UNKNOWN')} - Multiple: {current_multiple_to_check:.1f}x, Already forwarded: {has_been_forwarded}, Msg ID: {forwarded_msg_id}")

                    if current_multiple_to_check >= 5.0 and not has_been_forwarded:
                        try:
                            print(f"🚀 FORWARD TRIGGER: {token.get('name', 'UNKNOWN')} hit {current_multiple_to_check:.1f}x during alert - sending to free channel")
                            forwarded_message = await forward_to_free_channel(bot, config.FREE_CALL_CHANNEL, token, current_mc, current_multiple_to_check)

                            # Mark as forwarded and store message ID in separate update
                            forward_update_data = {
                                'has_been_forwarded': True,
                                'forwarded_at': datetime.now(),
                                'forwarded_multiple': round(current_multiple_to_check, 1),
                                'updated_at': datetime.now()
                            }
                            if forwarded_message and hasattr(forwarded_message, 'message_id'):
                                forward_update_data['forwarded_msg_id'] = forwarded_message.message_id
                                print(f"✅ Token {token.get('name')} forwarded to free channel at {current_multiple_to_check:.1f}x - Message ID: {forwarded_message.message_id}")
                            else:
                                print(f"⚠️ Forward message sent but no message ID available for {token.get('name')}")

                            await TokenService.update_token(token['mint'], forward_update_data)
                        except Exception as forward_error:
                            print(f"Error sending forwarded message during alert: {forward_error}")
                    elif current_multiple_to_check >= 5.0 and has_been_forwarded and forwarded_msg_id:
                        # Send reply alert to forwarded message in free channel
                        try:
                            print(f"📢 FORWARDED REPLY: {token.get('name', 'UNKNOWN')} {current_multiple_to_check:.1f}x - replying to forwarded message ID: {forwarded_msg_id}")
                            await send_forwarded_reply_alert(bot, config.FREE_CALL_CHANNEL, token, current_mc, current_multiple_to_check, forwarded_msg_id)
                            print(f"✅ FORWARDED REPLY SENT: {token.get('name', 'UNKNOWN')} - replied to message ID: {forwarded_msg_id}")
                        except Exception as reply_error:
                            print(f"Error sending forwarded reply alert: {reply_error}")
                    elif current_multiple_to_check >= 5.0 and has_been_forwarded:
                        print(f"⚠️ FORWARD ALREADY SENT: {token.get('name', 'UNKNOWN')} - but no message ID available for reply")
                    elif current_multiple_to_check < 5.0:
                        print(f"📊 FORWARD NOT READY: {token.get('name', 'UNKNOWN')} only at {current_multiple_to_check:.1f}x (need 5.0x+)")

                    # Add 10 second delay as requested
                    await sleep(10)

                # RULE 2: Subsequent alerts - database multiple >= last_alert_level + 1.0
                elif current_multiple_to_check >= 2.0 and last_alert_level > 0.0:
                    if current_multiple_to_check >= (last_alert_level + 1.0):
                        alert_level_to_send = current_multiple_to_check

                        print(f"🚨 NEXT ALERT: {token.get('name', 'unknown')} {current_multiple_to_check:.1f}x → sending next alert (was: {last_alert_level:.1f}x)")

                        # Send alert with database values
                        await send_token_alert(bot, channel_handle, token, current_mc, alert_level_to_send, config)

                        # Update ONLY alert-specific fields - preserve multiple and multiple_mc
                        update_data = {
                            'last_alert_level': round(alert_level_to_send, 1),
                            'last_alert_at': datetime.now(),
                            'updated_at': datetime.now()
                        }

                        # Update database with alert info only
                        await TokenService.update_token(token['mint'], update_data)

                        # Check for forwarded message requirement (>=5.0x and not already forwarded)
                        has_been_forwarded = token.get('has_been_forwarded', False)
                        forwarded_msg_id = token.get('forwarded_msg_id')
                        print(f"🔍 FORWARD CHECK (Next Alert): {token.get('name', 'UNKNOWN')} - Multiple: {current_multiple_to_check:.1f}x, Already forwarded: {has_been_forwarded}, Msg ID: {forwarded_msg_id}")

                        if current_multiple_to_check >= 5.0 and not has_been_forwarded:
                            try:
                                print(f"🚀 FORWARD TRIGGER: {token.get('name', 'UNKNOWN')} hit {current_multiple_to_check:.1f}x during alert - sending to free channel")
                                forwarded_message = await forward_to_free_channel(bot, config.FREE_CALL_CHANNEL, token, current_mc, current_multiple_to_check)

                                # Mark as forwarded and store message ID in separate update
                                forward_update_data = {
                                    'has_been_forwarded': True,
                                    'forwarded_at': datetime.now(),
                                    'forwarded_multiple': round(current_multiple_to_check, 1),
                                    'updated_at': datetime.now()
                                }
                                if forwarded_message and hasattr(forwarded_message, 'message_id'):
                                    forward_update_data['forwarded_msg_id'] = forwarded_message.message_id
                                    print(f"✅ Token {token.get('name')} forwarded to free channel at {current_multiple_to_check:.1f}x - Message ID: {forwarded_message.message_id}")
                                else:
                                    print(f"⚠️ Forward message sent but no message ID available for {token.get('name')}")

                                await TokenService.update_token(token['mint'], forward_update_data)
                            except Exception as forward_error:
                                print(f"Error sending forwarded message during alert: {forward_error}")
                        elif current_multiple_to_check >= 5.0 and has_been_forwarded and forwarded_msg_id:
                            # Send reply alert to forwarded message in free channel
                            try:
                                print(f"📢 FORWARDED REPLY: {token.get('name', 'UNKNOWN')} {current_multiple_to_check:.1f}x - replying to forwarded message ID: {forwarded_msg_id}")
                                await send_forwarded_reply_alert(bot, config.FREE_CALL_CHANNEL, token, current_mc, current_multiple_to_check, forwarded_msg_id)
                                print(f"✅ FORWARDED REPLY SENT: {token.get('name', 'UNKNOWN')} - replied to message ID: {forwarded_msg_id}")
                            except Exception as reply_error:
                                print(f"Error sending forwarded reply alert: {reply_error}")
                        elif current_multiple_to_check >= 5.0 and has_been_forwarded:
                            print(f"⚠️ FORWARD ALREADY SENT: {token.get('name', 'UNKNOWN')} - but no message ID available for reply")
                        elif current_multiple_to_check < 5.0:
                            print(f"📊 FORWARD NOT READY (Next Alert): {token.get('name', 'UNKNOWN')} only at {current_multiple_to_check:.1f}x (need 5.0x+)")

                        # Add 10 second delay as requested
                        await sleep(10)
                    else:
                        print(f"Alert check: {token.get('name', 'unknown')} {current_multiple_to_check:.1f}x - need {last_alert_level + 1.0:.1f}x+ for next alert")

            except Exception as e:
                print(f"Error checking alert for {token.get('mint', 'unknown')}: {e}")
                continue

    except Exception as e:
        print(f"Error in check_database_for_alerts: {e}")

async def send_pending_alerts(bot, channel_handle: str, config):
    """Send alerts for tokens with pending_alert flag every 60 seconds"""
    try:
        # Get tokens with pending alerts
        pending_tokens = await TokenService.get_tokens_by_query({"pending_alert": True})

        for token in pending_tokens:
            try:
                current_mc = token.get('cur_market_cap', 0)
                alert_level = token.get('pending_alert_level', 2)

                # Send alert message with specific level
                await send_token_alert(bot, channel_handle, token, current_mc, alert_level, config)

                # Remove pending flag and alert level
                await TokenService.update_token(token['mint'], {
                    'pending_alert': False,
                    'pending_alert_level': None
                })

                await sleep(1)  # Small delay between messages

            except Exception as e:
                print(f"Error sending pending alert for {token.get('name', 'unknown')}: {e}")

    except Exception as e:
        print(f"Error in send_pending_alerts: {e}")

# ATH message ID is now stored in database - no global variable needed

async def trigger_ath_batch_update(bot, free_channel: str):
    """Trigger ATH batch update after a forwarded message is sent"""
    try:
        from services import SettingService

        # Get the previous ATH message ID from database
        last_ath_message_id = await SettingService.get_ath_message_id()

        # Delete the previous ATH batch message if it exists
        if last_ath_message_id:
            try:
                bot.delete_message(free_channel, last_ath_message_id)
                print(f"🗑️ Deleted previous ATH batch message (ID: {last_ath_message_id})")
            except Exception as delete_error:
                print(f"Failed to delete previous ATH message: {delete_error}")

        # Send new ATH batch message
        await send_ath_batch_message(bot, free_channel)

    except Exception as e:
        print(f"Error in trigger_ath_batch_update: {e}")

async def send_ath_batch_message(bot, free_channel: str):
    """Send ATH batch message with pagination"""
    try:
        # Calculate 48 hours ago from current time
        from datetime import datetime, timedelta
        forty_eight_hours_ago = datetime.now() - timedelta(hours=48)

        # Get tokens with multiple >= 5.0x from the last 48 hours
        ath_tokens = await TokenService.get_tokens_by_query({
            "multiple": {"$gte": 5.0},
            "created_at": {"$gte": forty_eight_hours_ago}
        })

        if not ath_tokens:
            print("No ATH tokens found (>=5.0x)")
            return

        # Sort by highest multiple first - consistent with send_ath_batch_message
        ath_tokens.sort(key=lambda x: x.get('multiple', 1), reverse=True)

        print(f"Found {len(ath_tokens)} ATH tokens for batch message")

        # Send first page of ATH batch message
        await send_ath_page(bot, free_channel, ath_tokens, page=1)

    except Exception as e:
        print(f"Error in send_ath_batch_message: {e}")

async def send_ath_page(bot, free_channel: str, all_ath_tokens: list, page: int, message_id: int = None):
    """Send a specific page of ATH tokens with improved error handling"""
    try:
        tokens_per_page = 10
        total_pages = (len(all_ath_tokens) + tokens_per_page - 1) // tokens_per_page

        if page < 1 or page > total_pages:
            print(f"Invalid page requested: {page} (total pages: {total_pages})")
            return

        # Calculate 24-hour statistics (from 7pm UTC yesterday to now)
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        twenty_four_hours_ago = now_utc - timedelta(hours=24)

        # Get tokens called in the last 24 hours
        from services import TokenService
        tokens_24h = await TokenService.get_tokens_by_query({
            "created_at": {"$gte": twenty_four_hours_ago}
        })

        # Calculate 24-hour metrics
        total_calls = len(tokens_24h)
        win_count = sum(1 for token in tokens_24h if token.get('multiple', 1.0) >= 1.5)
        win_rate = (win_count / total_calls * 100) if total_calls > 0 else 0.0

        # Calculate average profit
        total_multiple = sum(token.get('multiple', 1.0) for token in tokens_24h)
        avg_profit = total_multiple / total_calls if total_calls > 0 else 0.0

        # Count tokens in different multiple ranges
        range_2x = sum(1 for token in tokens_24h if 2.0 <= token.get('multiple', 1.0) < 5.0)
        range_5x = sum(1 for token in tokens_24h if 5.0 <= token.get('multiple', 1.0) < 10.0)
        range_10x = sum(1 for token in tokens_24h if 10.0 <= token.get('multiple', 1.0) < 15.0)
        range_15x = sum(1 for token in tokens_24h if token.get('multiple', 1.0) >= 15.0)

        # Find best performing token
        best_token = None
        best_multiple = 0.0
        for token in tokens_24h:
            if token.get('multiple', 1.0) > best_multiple:
                best_multiple = token.get('multiple', 1.0)
                best_token = token

        best_text = f"{best_token.get('symbol', 'N/A')} {best_multiple:.1f}x" if best_token else "N/A"

        ## Get tokens for this page
        start_idx = (page - 1) * tokens_per_page
        end_idx = start_idx + tokens_per_page
        page_tokens = all_ath_tokens[start_idx:end_idx]

        # Create message content with 24-hour stats and ATH heading
        message_lines = [
            "<b>💎 24hours Token Signal</b>\n",
            f"⚡️ Total Calls: <b>{total_calls}</b>",
            f"📈 +50% Win Rate: <b>{win_rate:.1f}%</b>",
            f"💰 Wins Avg Profit: <b>{avg_profit:.1f}x</b>\n",
            "24hr Xs Alerts:",
            f"💸 2X+: <b>{range_2x}</b>",
            f"💸 5X+: <b>{range_5x}</b>",
            f"💸 10X+: <b>{range_10x}</b>",
            f"💸 15X+: <b>{range_15x}</b>\n",
            f"🤑 Best: <b>{best_text}</b>\n",
            "<b>ATH OF TOKENS CALLED IN THE LAST 48 HOURS</b>\n"
        ]

        for i, token in enumerate(page_tokens):
            created_at = token.get('created_at', datetime.now())
            current_time = datetime.now()
            time_diff = (current_time - created_at).total_seconds()

            hours = int(time_diff // 3600)
            minutes = int((time_diff % 3600) // 60)
            time_str = f"{hours:02d}h : {minutes:02d}m"

            multiple = token.get('multiple', 1)
            symbol = token.get('symbol', 'N/A')

            # Use tree structure - last item gets └, others get ├
            tree_symbol = "└" if i == len(page_tokens) - 1 else "├"
            message_lines.append(f"${symbol}")
            message_lines.append(f"{tree_symbol} {multiple:.1f}x in {time_str}")

        message = "\n".join(message_lines)
        message += f"\n\nPage {page} of {total_pages}\nCopyright ©️ Apex Solana Signal"

        # Create keyboard with Join Premium and navigation buttons
        from telebot import types
        keyboard = types.InlineKeyboardMarkup()

        # Add Join Premium button first
        keyboard.add(types.InlineKeyboardButton("💎 Join Premium", url="https://t.me/onlysubsbot?start=ApexSignal"))

        # Add navigation buttons with timestamp for persistence
        import time
        current_timestamp = int(time.time())
        nav_buttons = []

        if page > 1:
            nav_buttons.append(types.InlineKeyboardButton("⏮️ Previous", callback_data=f"ath_{current_timestamp}_{page-1}"))
        if page < total_pages:
            nav_buttons.append(types.InlineKeyboardButton("Next ⏭️", callback_data=f"ath_{current_timestamp}_{page+1}"))

        if nav_buttons:
            keyboard.add(*nav_buttons)

        print(f"Sending ATH page {page} of {total_pages} with {len(page_tokens)} tokens")

        from services import SettingService

        if message_id:
            # Edit existing message
            try:
                bot.edit_message_text(
                    chat_id=free_channel,
                    message_id=message_id,
                    text=message,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                print(f"Successfully edited ATH message to page {page}")
                # Keep the same message_id since we're editing and save to database
                await SettingService.set_ath_message_id(message_id)
            except Exception as edit_error:
                print(f"Failed to edit ATH message: {edit_error}")
                # If edit fails, send new message
                try:
                    sent_msg = bot.send_message(
                        free_channel,
                        message,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    # Update to new message ID and save to database
                    await SettingService.set_ath_message_id(sent_msg.message_id)
                    print(f"Sent new ATH message after edit failure: page {page} - Message ID: {sent_msg.message_id}")
                except Exception as send_error:
                    print(f"Failed to send new ATH message: {send_error}")
        else:
            # Send new message and pin it
            try:
                sent_msg = bot.send_message(
                    free_channel,
                    message,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )

                # Store the message ID in database for future deletion
                await SettingService.set_ath_message_id(sent_msg.message_id)

                # Pin the message
                try:
                    bot.pin_chat_message(free_channel, sent_msg.message_id)
                    print(f"Pinned ATH batch message (page {page}) in {free_channel} - Message ID: {sent_msg.message_id}")
                except Exception as pin_error:
                    print(f"Failed to pin ATH message: {pin_error}")

            except Exception as send_error:
                print(f"Failed to send ATH message: {send_error}")

    except Exception as e:
        print(f"Error in send_ath_page: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

async def get_current_token_data_batch(token_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get current token data for multiple addresses using DEXScreener API"""
    try:
        from api import get_dexscreener_tokens_batch

        # Create batches of 25 addresses each
        batches = [token_addresses[i:i+25] for i in range(0, len(token_addresses), 25)]

        # Create concurrent tasks for all batches
        tasks = [get_dexscreener_tokens_batch(batch) for batch in batches]

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all results into a single dictionary
        token_data_map = {}

        for result in results:
            if isinstance(result, Exception):
                print(f"Batch request failed: {result}")
                continue

            if result and isinstance(result, list):
                for token_data in result:
                    if token_data and 'baseToken' in token_data:
                        base_token_address = token_data['baseToken']['address']
                        # Extract market cap correctly from DEXScreener response
                        market_cap = 0
                        if 'marketCap' in token_data:
                            market_cap = safe_float_conversion(token_data['marketCap'], 0)
                        elif 'fdv' in token_data:
                            market_cap = safe_float_conversion(token_data['fdv'], 0)

                        # Extract volume correctly
                        volume = 0
                        if 'volume' in token_data and isinstance(token_data['volume'], dict):
                            volume = safe_float_conversion(token_data['volume'].get('h24', 0), 0)
                        elif 'volume' in token_data:
                            volume = safe_float_conversion(token_data['volume'], 0)

                        # Convert DEXScreener format to match existing format
                        formatted_data = {
                            'baseToken': base_token_address,
                            'marketCap': market_cap,
                            'cur_market_cap': market_cap,
                            'volume': volume,
                            'cur_volume': volume,
                            'priceUsd': token_data.get('priceUsd', '0'),
                            'symbol': token_data.get('baseToken', {}).get('symbol', 'N/A'),
                            'name': token_data.get('baseToken', {}).get('name', 'N/A')
                        }
                        token_data_map[base_token_address] = formatted_data

        return token_data_map

    except Exception as e:
        print(f"Error getting batch token data: {e}")
        return {}

async def get_current_token_data(mint_address: str):
    """Get current token data for a single address using DEXScreener API"""
    try:
        batch_data = await get_current_token_data_batch([mint_address])
        return batch_data.get(mint_address)
    except Exception as e:
        print(f"Error getting current token data for {mint_address}: {e}")
        return None

async def send_token_alert(bot, channel_handle: str, token_data: Dict[str, Any], current_mc: float, multiple: float, config):
    """Send alert message for token"""
    try:
        token_name = token_data.get('name', 'unknown')

        print(f"🚨 SENDING ALERT: {token_name} - {multiple:.1f}x")
        print(f"   Original MC: ${format_number(token_data.get('market_cap', 0))}")
        print(f"   Current MC: ${format_number(current_mc)}")

        # Create alert message using multiple_mc for accurate "From → To" display
        display_mc = token_data.get('multiple_mc', current_mc)  # Use multiple_mc if available, fallback to current_mc
        alert_message = alert_msg(token_data, display_mc, multiple)
        btn = link_btn(token_data['mint'], token_data.get('symbol', ''), is_alert=True)

        from telebot import types
        keyboard = types.InlineKeyboardMarkup()
        for row in btn['content']:
            keyboard_row = []
            for button in row:
                keyboard_row.append(types.InlineKeyboardButton(button['text'], url=button.get('url', '')))
            keyboard.add(*keyboard_row)

        # Reply to original message if msg_id exists
        reply_to_msg_id = token_data.get('msg_id')
        premium_reply_to_msg_id = token_data.get('premium_msg_id')

        try:
            bot.send_message(
                channel_handle,
                alert_message,
                reply_markup=keyboard,
                parse_mode="HTML",
                reply_to_message_id=reply_to_msg_id,
                disable_web_page_preview=True,
                message_thread_id=config.INITIAL_CALL_TOPIC_ID
            )

            # Send alert to premium channel - reply to premium message if available
            try:
                bot.send_message(
                    config.PREMIUM_CHANNEL,
                    alert_message,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    reply_to_message_id=premium_reply_to_msg_id,
                    disable_web_page_preview=True
                )
                print(f"✅ Alert sent: {token_name} - {multiple:.1f}x (replied to msg_id: {reply_to_msg_id}, premium_msg_id: {premium_reply_to_msg_id})")
            except Exception as premium_error:
                # If premium reply fails, send without reply to premium channel
                if "message to be replied not found" in str(premium_error):
                    print(f"Premium message not found, sending alert without reply to premium channel for {token_name}")
                    bot.send_message(
                        config.PREMIUM_CHANNEL,
                        alert_message,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    print(f"✅ Alert sent: {token_name} - {multiple:.1f}x (replied to msg_id: {reply_to_msg_id}, premium standalone)")
                else:
                    raise premium_error

        except Exception as telegram_error:
            # If reply fails, send without reply
            if "message to be replied not found" in str(telegram_error):
                print(f"Original message not found, sending alert without reply for {token_name}")
                bot.send_message(
                    channel_handle,
                    alert_message,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    message_thread_id=config.INITIAL_CALL_TOPIC_ID
                )

                # Send alert to premium channel - try to reply to premium message if available
                try:
                    bot.send_message(
                        config.PREMIUM_CHANNEL,
                        alert_message,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                        reply_to_message_id=premium_reply_to_msg_id,
                        disable_web_page_preview=True
                    )
                    print(f"✅ Alert sent without reply: {token_name} - {multiple:.1f}x (premium replied to: {premium_reply_to_msg_id})")
                except Exception as premium_error:
                    # If premium reply also fails, send without reply to premium channel
                    if "message to be replied not found" in str(premium_error):
                        bot.send_message(
                            config.PREMIUM_CHANNEL,
                            alert_message,
                            reply_markup=keyboard,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                        print(f"✅ Alert sent without reply: {token_name} - {multiple:.1f}x (both standalone)")
                    else:
                        raise premium_error
            else:
                raise telegram_error

    except Exception as e:
        print(f"Error sending alert for {token_data.get('name', 'unknown')}: {e}")

async def forward_to_free_channel(bot, free_channel: str, token_data: Dict[str, Any], current_mc: float, multiple: float):
    """Forward 5x+ alerts to free channel - assumes multiple >= 5.0 check already done"""
    try:
        token_name = token_data.get('name', 'unknown')

        print(f"🚀 FORWARDING: {token_name} - {multiple:.1f}x to free channel")

        # Create alert message using multiple_mc for accurate "From → To" display  
        display_mc = token_data.get('multiple_mc', current_mc)  # Use multiple_mc if available, fallback to current_mc
        alert_message = alert_msg(token_data, display_mc, multiple)
        btn = link_btn(token_data['mint'], token_data.get('symbol', ''), is_forwarded=True)

        from telebot import types
        keyboard = types.InlineKeyboardMarkup()

        # Add all buttons from the link_btn function (includes premium and twitter search)
        for row in btn['content']:
            keyboard_row = []
            for button in row:
                keyboard_row.append(types.InlineKeyboardButton(button['text'], url=button.get('url', '')))
            keyboard.add(*keyboard_row)

        # Send forward to free channel
        forwarded_message = bot.send_message(
            free_channel,
            alert_message,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        print(f"✅ FORWARD: {token_name} sent to free channel - {multiple:.1f}x - Message ID: {forwarded_message.message_id}")

        return forwarded_message

    except Exception as e:
        print(f"❌ Error forwarding message to free channel for {token_data.get('name', 'unknown')}: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return None

async def send_forwarded_reply_alert(bot, free_channel: str, token_data: Dict[str, Any], current_mc: float, multiple: float, forwarded_msg_id: int):
    """Send reply alert to the forwarded message in the free channel"""
    try:
        token_name = token_data.get('name', 'unknown')

        print(f"📢 SENDING FORWARDED REPLY ALERT: {token_name} - {multiple:.1f}x (replying to msg_id: {forwarded_msg_id})")

        # Create alert message using multiple_mc for accurate "From → To" display
        display_mc = token_data.get('multiple_mc', current_mc)  # Use multiple_mc if available, fallback to current_mc
        alert_message = alert_msg(token_data, display_mc, multiple)
        btn = link_btn(token_data['mint'], token_data.get('symbol', ''), is_alert=True, is_forwarded=True)

        from telebot import types
        keyboard = types.InlineKeyboardMarkup()
        for row in btn['content']:
            keyboard_row = []
            for button in row:
                keyboard_row.append(types.InlineKeyboardButton(button['text'], url=button.get('url', '')))
            keyboard.add(*keyboard_row)

        # Send reply to the forwarded message
        try:
            bot.send_message(
                free_channel,
                alert_message,
                reply_markup=keyboard,
                parse_mode="HTML",
                reply_to_message_id=forwarded_msg_id,
                disable_web_page_preview=True
            )
            print(f"✅ Forwarded reply alert sent: {token_name} - {multiple:.1f}x (replied to msg_id: {forwarded_msg_id})")
        except Exception as telegram_error:
            # If reply fails (message not found), send without reply
            if "message to be replied not found" in str(telegram_error):
                print(f"Original forwarded message not found, sending reply without reply for {token_name}")
                bot.send_message(
                    free_channel,
                    alert_message,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                print(f"✅ Forwarded reply alert sent without reply: {token_name} - {multiple:.1f}x")
            else:
                raise telegram_error

    except Exception as e:
        print(f"Error sending forwarded reply alert for {token_data.get('name', 'unknown')}: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

from datetime import timedelta