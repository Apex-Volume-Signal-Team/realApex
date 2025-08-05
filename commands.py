# Updated multiple formatting in message functions and ensured consistent 0.0 formatting.
from typing import Dict, Any

def format_number(num: float) -> str:
    """Format numbers with K, M, B suffixes"""
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    if num >= 1_000:
        return f"{num / 1_000:.2f}k"
    return str(num)

def command_list():
    return [
        {"command": "start", "description": "Start the bot"},
        {"command": "promote", "description": "Token promotion"}
    ]

def start_bot_msg(public_key: str) -> str:
    return f"""🤖 Welcome to ApexSignal Promotion Bot!

Your ultimate solution for promoting your crypto projects and tokens. Whether you want to enhance your project's visibility with advertisements or create excitement with promotional calls, I'm here to help.

Here's what I offer:

📡 Advertise Your Project:
- Feature your project in our community.
- Reach a broader audience and boost your project's visibility.

💹 Promote Your Token:
- Connect with potential investors and enthusiasts.
- Build excitement and engagement around your token.

Getting started is simple!

1. Use the /promote command to initiate the booking process.
2. Send the required SOL amount to the given address.
3. Share additional details like your token address, Telegram link, and a brief description.

Your project's success is just a few clicks away. Let's get started and turn your crypto dreams into reality!

If you need assistance or have questions, feel free to ask. Happy promoting! 🚀

💰 Deposit wallet address: 

`{public_key}`

Copyright © Apex Solana Signal"""

def promote_time_msg() -> str:
    return """🚀 Token Promotion Service

Please enter the number of times you want to promote your token:

💰 Price: 0.1 SOL per promotion

Example: Send `5` to promote your token 5 times (Cost: 0.5 SOL)

Your promotion will be featured in our premium channel with:
- Detailed token analysis
- Market data and metrics
- Direct buy links
- Community exposure

Ready to boost your token's visibility? 📈"""

def promote_msg(public_key: str, promote_count: int) -> str:
    total_cost = promote_count * 0.1
    return f"""📋 **Promotion Order Summary**

**Token Promotions:** {promote_count}x
**Cost per promotion:** 0.1 SOL
**Total Cost:** {total_cost} SOL

💰 **Payment Instructions:**
Send exactly `{total_cost} SOL` to:
`{public_key}`

⚠️ **Important:**
- Send the exact amount only
- Payment must come from your registered wallet
- Promotions will start after payment confirmation

Click "Confirm Payment" below once you've sent the SOL."""

def admin_promote_msg(text: str) -> str:
    return f"""🔑 **Admin Promotion Approved**

**Promotion Count:** {text}
**Status:** Free (Admin Access)

Your promotion has been automatically approved. You can proceed directly to submit your token address for promotion.

Ready to promote? 🚀"""

def display_msg(data: Dict[str, Any]) -> str:
    """Create display message for tokens"""
    try:
        name = data.get('name', 'N/A')
        symbol = data.get('symbol', 'N/A')
        mint = data.get('mint', 'N/A')
        market_cap = format_number(data.get('marketCap', 0))
        pumpfun_age = data.get('pumpfunAge', 'N/A')
        holder_count = int(data.get('holderCount', 0))
        volume = format_number(data.get('volume', 0))
        dev_wallet_percentage = data.get('devWalletPercentage', 0)
        top10_holder_percentage = data.get('top10HolderPercentage', 0)
        insider_wallet_percentage = data.get('insiderWalletPercentage', 0)
        sniper_wallet_percentage = data.get('sniperWalletPercentage', 0)
        exchange = data.get('exchange', 'Unknown')

        # Get social links
        twitter = data.get('twitter', '')
        telegram = data.get('telegram', '')
        website = data.get('website', '')

        # Build socials section
        socials = []
        if twitter:
            socials.append(f'<a href="{twitter}">X</a>')
        if telegram:
            socials.append(f'<a href="{telegram}">TELEGRAM</a>')
        if website:
            socials.append(f'<a href="{website}">WEBSITE</a>')

        socials_text = " | ".join(socials) if socials else "No socials"

        # Build exchange link based on exchange name and CA
        def get_exchange_link(exchange_name: str, ca: str) -> str:
            """Generate exchange link based on exchange name"""
            ca_lower = ca.lower()

            if ca_lower.endswith('bonk'):
                return f'<a href="https://bonk.fun/token/{ca}">Bonk.fun</a>'
            elif ca_lower.endswith('pump'):
                return f'<a href="https://pump.fun/{ca}">Pump.fun</a>'
            elif exchange_name.lower() in ['meteora']:
                return f'<a href="https://app.meteora.ag/pools/{ca}">Meteora</a>'
            elif exchange_name.lower() in ['raydium', 'launchlabs']:
                return f'<a href="https://raydium.io/swap/?inputCurrency=sol&outputCurrency={ca}">Raydium</a>'
            elif exchange_name.lower() in ['orca']:
                return f'<a href="https://www.orca.so/swap?tokenIn=So11111111111111111111111111111111111111112&tokenOut={ca}">Orca</a>'
            else:
                # For uncommon exchanges, use Jupiter
                return f'<a href="https://jup.ag/swap/SOL-{ca}">Jupiter</a>'

        exchange_link = get_exchange_link(exchange, mint)

        message = f"""💎 <b>{name} | ${symbol}</b>

<b>CA:</b> <code>{mint}</code>

💹 <b>Marketcap:</b> ${market_cap}
🕕 <b>Dex Age:</b> {pumpfun_age}

💰 <b>Dev Wallet:</b> {dev_wallet_percentage:.3f}%
👥 <b>Holders:</b> {holder_count}
💪 <b>Top 10 holder hold:</b> {top10_holder_percentage:.2f}%
🚀 <b>Volume:</b> ${volume}

🌐 <b>Socials:</b> {socials_text}

🔗 <b>Exchange:</b> {exchange_link}
📦 <b>Insider Wallet:</b> {insider_wallet_percentage:.2f}%
🎯 <b>Sniper Wallet:</b> {sniper_wallet_percentage:.2f}%

📈 <b>Chart:</b> <a href="https://dexscreener.com/solana/{mint}">DexScreener</a>

Copyright © Apex Solana Signal"""

        return message

    except Exception as e:
        print(f"Error in display_msg: {e}")
        return f"Error creating display message for {data.get('name', 'unknown token')}"

def multiple_msg(read_data: Dict[str, Any], element: Dict[str, Any]) -> str:
    try:
        print(f"Debug multiple_msg - read_data keys: {list(read_data.keys())}")
        print(f"Debug multiple_msg - element keys: {list(element.keys())}")
        print(f"Debug multiple_msg - element marketCap: {element.get('marketCap', 'NOT_FOUND')}")
        print(f"Debug multiple_msg - read_data market_cap: {read_data.get('market_cap', 'NOT_FOUND')}")

        element_mc = element.get('marketCap', 0)
        read_mc = read_data.get('market_cap', 1)

        if read_mc <= 0:
            read_mc = 1

        multiple = round(element_mc / read_mc, 1)

        # Calculate time since token was initially called
        from datetime import datetime
        created_at = read_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            time_diff = datetime.now() - created_at
            total_minutes = time_diff.total_seconds() / 60
            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)

            if hours > 0:
                time_text = f"{hours}h {minutes}m"
            else:
                time_text = f"{minutes}m"
        else:
            time_text = read_data.get('pumpfun_age', 'unknown')

        print(f"Debug multiple_msg - calculated multiple: {multiple}")

        message = f"""🎯 <b>{multiple:.1f}x ${read_data.get('symbol', 'N/A')} in {time_text}</b>

📊 <b>From</b> ${format_number(read_mc)} <b>→</b> ${format_number(element_mc)}

<b>CA:</b> <code>{read_data.get('mint', 'N/A')}</code>

Copyright © Apex Solana Signal"""

        print(f"Debug multiple_msg - Message created successfully, length: {len(message)}")
        return message

    except Exception as e:
        print(f"Error in multiple_msg: {e}")
        print(f"Debug multiple_msg - element: {element}")
        print(f"Debug multiple_msg - read_data: {read_data}")
        return f"Error creating multiple message for {read_data.get('name', 'unknown token')}"

def forward_msg(read_data: Dict[str, Any], element: Dict[str, Any], drop_count: int) -> str:
    try:
        print(f"Debug forward_msg - read_data keys: {list(read_data.keys())}")
        print(f"Debug forward_msg - element keys: {list(element.keys())}")
        print(f"Debug forward_msg - element marketCap: {element.get('marketCap', 'NOT_FOUND')}")
        print(f"Debug forward_msg - read_data market_cap: {read_data.get('market_cap', 'NOT_FOUND')}")
        print(f"Debug forward_msg - drop_count: {drop_count}")

        element_mc = element.get('marketCap', 0)
        read_mc = read_data.get('market_cap', 1)

        if read_mc <= 0:
            read_mc = 1

        multiple = round(element_mc / read_mc, 1)

        # Calculate time since token was initially called
        from datetime import datetime
        created_at = read_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            time_diff = datetime.now() - created_at
            total_minutes = time_diff.total_seconds() / 60
            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)

            if hours > 0:
                time_text = f"{hours}h {minutes}m"
            else:
                time_text = f"{minutes}m"
        else:
            time_text = read_data.get('pumpfun_age', 'unknown')

        print(f"Debug forward_msg - calculated multiple: {multiple}")

        message = f"""🎯 <b>{multiple:.1f}x ${read_data.get('symbol', 'N/A')} in {time_text}</b>

📊 <b>From</b> ${format_number(read_mc)} <b>→</b> ${format_number(element_mc)}

<b>CA:</b> <code>{read_data.get('mint', 'N/A')}</code>

Copyright © Apex Solana Signal"""

        print(f"Debug forward_msg - Message created successfully, length: {len(message)}")
        return message

    except Exception as e:
        print(f"Error in forward_msg: {e}")
        print(f"Debug forward_msg - element: {element}")
        print(f"Debug forward_msg - read_data: {read_data}")
        return f"Error creating forward message for {read_data.get('name', 'unknown token')}"

def alert_msg(token_data: Dict[str, Any], current_mc: float, alert_level: float) -> str:
    """Create alert message for market cap increases"""
    try:
        from datetime import datetime

        # Calculate time since token was initially called
        created_at = token_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            time_diff = datetime.now() - created_at
            total_minutes = time_diff.total_seconds() / 60
            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)

            if hours > 0:
                time_text = f"{hours}h {minutes}m"
            else:
                time_text = f"{minutes}m"
        else:
            time_text = token_data.get('pumpfun_age', 'unknown')

        # Use multiple_mc if available, otherwise fallback to current_mc
        to_mc = token_data.get('multiple_mc', current_mc)

        message = f"""🎯 <b>{alert_level:.1f}x ${token_data.get('symbol', 'N/A')} in {time_text}</b>

📊 <b>From</b> ${format_number(token_data.get('market_cap', 0))} <b>→</b> ${format_number(to_mc)}

<b>CA:</b> <code>{token_data.get('mint', 'N/A')}</code>

Copyright © Apex Solana Signal"""

        print(f"Debug alert_msg - Message created successfully, length: {len(message)}")
        return message

    except Exception as e:
        print(f"Error in alert_msg: {e}")
        return f"Error creating alert message for {token_data.get('name', 'unknown token')}: {e}"

def should_show_preview(message_text: str, twitter_url: str = None) -> bool:
    """Check if message should show web page preview (only for Twitter/X links)"""
    if not twitter_url:
        return False

    # Check if Twitter URL is the first link in the message
    import re
    links = re.findall(r'<a href="([^"]+)"', message_text)

    if links and twitter_url in links[0]:
        return True

    return False

def link_btn(mint_address: str, symbol: str = "", is_forwarded: bool = False, is_alert: bool = False) -> Dict[str, Any]:
    """Generate trading bot links"""
    try:
        referer = "apexsignal"

        content = []

        # Add buttons based on message type
        if is_forwarded:
            # Create Twitter search URL with both symbol and CA
            if symbol:
                search_term = f"${symbol} OR {mint_address}"
            else:
                search_term = mint_address
            twitter_search_url = f"https://twitter.com/search?q={search_term}"

            # Add full-width buttons for forwarded messages
            content.append([{"text": "💎 Join Premium", "url": "https://t.me/onlysubsbot?start=ApexSignal"}])

            # Add trading bot buttons for forwarded messages
            content.extend([
                [
                    {"text": "👾 MevX (Bot)", "url": f"https://t.me/MevxTradingBot?start={mint_address}-{referer}"},
                    {"text": "🟣 STB", "url": f"https://t.me/solana_trojanbot?start=r-{referer}-{mint_address}"}
                ],
                [
                    {"text": "Ⓜ️ Maestro", "url": f"http://t.me/maestro?start={mint_address}-{referer}"},
                    {"text": "🐴 Trojan", "url": f"https://t.me/odysseus_trojanbot?start=r-{referer}-{mint_address}"}
                ],
                [
                    {"text": "🤖 GMGN", "url": f"https://t.me/GMGN_sol02_bot?start=i_eJTMUII1_c_{mint_address}"},
                    {"text": "🌸 Bloom", "url": f"https://t.me/BloomSolana_bot?start=ref_W783FKGM3D_ca_{mint_address}"}
                ]
            ])

        elif is_alert and is_forwarded:
            # For forwarded reply alerts, use same buttons as forwarded messages
            # Create Twitter search URL with both symbol and CA
            if symbol:
                search_term = f"${symbol} OR {mint_address}"
            else:
                search_term = mint_address
            twitter_search_url = f"https://twitter.com/search?q={search_term}"

            # Add full-width buttons for forwarded reply alerts (same as forwarded messages)
            content.append([{"text": "💎 Join Premium", "url": "https://t.me/onlysubsbot?start=ApexSignal"}])

            # Add trading bot buttons for forwarded reply alerts
            content.extend([
                [
                    {"text": "👾 MevX (Bot)", "url": f"https://t.me/MevxTradingBot?start={mint_address}-{referer}"},
                    {"text": "🟣 STB", "url": f"https://t.me/solana_trojanbot?start=r-{referer}-{mint_address}"}
                ],
                [
                    {"text": "Ⓜ️ Maestro", "url": f"http://t.me/maestro?start={mint_address}-{referer}"},
                    {"text": "🐴 Trojan", "url": f"https://t.me/odysseus_trojanbot?start=r-{referer}-{mint_address}"}
                ],
                [
                    {"text": "🤖 GMGN", "url": f"https://t.me/GMGN_sol02_bot?start=i_eJTMUII1_c_{mint_address}"},
                    {"text": "🌸 Bloom", "url": f"https://t.me/BloomSolana_bot?start=ref_W783FKGM3D_ca_{mint_address}"}
                ]
            ])

        elif is_alert:
            # For regular alert messages (not forwarded), NO buttons at all
            pass

        else:
            # For regular calls, add Twitter search as first full-width button
            if symbol:
                search_term = f"${symbol} OR {mint_address}"
            else:
                search_term = mint_address
            twitter_search_url = f"https://twitter.com/search?q={search_term}"

            content.append([{"text": "🔍 Search On X(twitter)", "url": twitter_search_url}])

            # Add trading bot buttons for regular calls
            content.extend([
                [
                    {"text": "👾 MevX (Bot)", "url": f"https://t.me/MevxTradingBot?start={mint_address}-{referer}"},
                    {"text": "🟣 STB", "url": f"https://t.me/solana_trojanbot?start=r-{referer}-{mint_address}"}
                ],
                [
                    {"text": "Ⓜ️ Maestro", "url": f"http://t.me/maestro?start={mint_address}-{referer}"},
                    {"text": "🐴 Trojan", "url": f"https://t.me/odysseus_trojanbot?start=r-{referer}-{mint_address}"}
                ],
                [
                    {"text": "🤖 GMGN", "url": f"https://t.me/GMGN_sol02_bot?start=i_eJTMUII1_c_{mint_address}"},
                    {"text": "🌸 Bloom", "url": f"https://t.me/BloomSolana_bot?start=ref_W783FKGM3D_ca_{mint_address}"}
                ]
            ])

        return {"content": content}
    except Exception as e:
        print(f"Error creating link buttons: {e}")
        return {"content": []}