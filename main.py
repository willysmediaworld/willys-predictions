import threading
import telebot
from telebot import types
from flask import Flask, render_template_string
import os
import json
import requests
from datetime import datetime

# ==========================================
# CONFIGURATION & API KEYS
# ==========================================
ODDS_API_KEY = "a25ddc2f3ceffcb7f959e224f6a40d4f"
ADMIN_PASSWORD = "willys123"
BOT_TOKEN = "8700629519:AAFUXLN7K7XrS0DTMQ_sULOnlAvLIHc-SrU"

SPORTS_LEAGUES = [
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_germany_bundesliga',
    'soccer_italy_serie_a',
    'soccer_france_ligue_one'
]

DEFAULT_DATA = {
    "match1_name": "Liverpool vs Southampton",
    "match1_tip": "Home Win (1) @ 1.28",
    "match2_name": "Barcelona vs Mallorca",
    "match2_tip": "Over 1.5 Goals @ 1.22",
    "total_odds": "1.56",
    "sportybet_code": "PENDING",
    "affiliate_link": "https://www.sportybet.com",
    "last_updated": "Default"
}

def load_data():
    try:
        if os.path.exists("data.json"):
            with open("data.json", "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading data: {e}")
    return DEFAULT_DATA

def save_data(data):
    try:
        with open("data.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data: {e}")

DATA = load_data()

# ==========================================
# AUTOMATED MATCH FETCHING ENGINE
# ==========================================
def fetch_automated_predictions():
    global DATA
    selected_matches = []
    
    for league in SPORTS_LEAGUES:
        if len(selected_matches) >= 2:
            break
            
        url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                events = res.json()
                for event in events:
                    home_team = event.get('home_team')
                    away_team = event.get('away_team')
                    bookmakers = event.get('bookmakers', [])
                    if not bookmakers: continue
                    markets = bookmakers[0].get('markets', [])
                    if not markets: continue
                    outcomes = markets[0].get('outcomes', [])
                    
                    for outcome in outcomes:
                        name = outcome.get('name')
                        price = outcome.get('price', 0)
                        
                        if 1.20 <= price <= 1.45:
                            match_name = f"{home_team} vs {away_team}"
                            tip = f"{name} Win @ {price}"
                            
                            if not any(m['name'] == match_name for m in selected_matches):
                                selected_matches.append({
                                    "name": match_name,
                                    "tip": tip,
                                    "odd": price
                                })
                                break
        except Exception as e:
            print(f"Error scanning league {league}: {e}")

    if len(selected_matches) >= 2:
        m1 = selected_matches[0]
        m2 = selected_matches[1]
        t_odds = round(m1['odd'] * m2['odd'], 2)
        
        DATA['match1_name'] = m1['name']
        DATA['match1_tip']  = m1['tip']
        DATA['match2_name'] = m2['name']
        DATA['match2_tip']  = m2['tip']
        DATA['total_odds']  = str(t_odds)
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(DATA)
        return True, f"Successfully auto-selected 2 matches! Total Odds: ~{t_odds}"
    else:
        return False, "Not enough safe banker games found in current live markets."


# ==========================================
# 1. TELEGRAM BOT ENGINE
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN)

# QUICK COMMAND: /code (Update SportyBet Booking Code in 1 Second)
@bot.message_handler(commands=['code'])
def update_code_only(message):
    try:
        new_code = message.text.replace('/code', '').strip().upper()
        if not new_code:
            bot.reply_to(message, "❌ Please provide a booking code.\nExample: `/code BC982A1`", parse_mode="Markdown")
            return
            
        DATA['sportybet_code'] = new_code
        save_data(DATA)
        
        reply = (
            f"✅ **SPORTYBET CODE UPDATED!** 🔑\n\n"
            f"New Code: `{new_code}`\n"
            f"🌐 *Updated instantly on Website & Bot!*"
        )
        bot.reply_to(message, reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# COMMAND: /fetch (Force instant auto-scan)
@bot.message_handler(commands=['fetch'])
def trigger_fetch(message):
    bot.reply_to(message, "🔍 Scanning live football markets for 1.50 - 2.00 odds... Please wait.")
    success, msg = fetch_automated_predictions()
    if success:
        reply = (
            f"✅ **AUTO-FETCH COMPLETE!** 🔥\n\n"
            f"📌 **Match 1:** {DATA['match1_name']} ({DATA['match1_tip']})\n"
            f"📌 **Match 2:** {DATA['match2_name']} ({DATA['match2_tip']})\n"
            f"📊 **Total Odds:** ~{DATA['total_odds']}\n\n"
            f"👉 *Send `/code YOURCODE` to add today's SportyBet code!*"
        )
    else:
        reply = f"⚠️ {msg}\nDefault/stored predictions retained."
    bot.reply_to(message, reply, parse_mode="Markdown")

# COMMAND: /update (Full Manual Override)
@bot.message_handler(commands=['update'])
def update_predictions(message):
    try:
        raw_text = message.text.replace('/update', '').strip()
        parts = [p.strip() for p in raw_text.split('|')]
        
        if len(parts) < 7:
            bot.reply_to(message, "❌ Format: `/update willys123 | Match 1 | Tip 1 | Match 2 | Tip 2 | Odds | Code`", parse_mode="Markdown")
            return

        if parts[0] != ADMIN_PASSWORD:
            bot.reply_to(message, "⛔ Invalid password.")
            return

        DATA['match1_name'] = parts[1]
        DATA['match1_tip']  = parts[2]
        DATA['match2_name'] = parts[3]
        DATA['match2_tip']  = parts[4]
        DATA['total_odds']  = parts[5]
        DATA['sportybet_code'] = parts[6]
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        save_data(DATA)
        bot.reply_to(message, "✅ **PREDICTIONS UPDATED MANUALLY!**", parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_odds = types.KeyboardButton("🎯 Today's Safe 2-Odds")
    btn_code = types.KeyboardButton("📱 SportyBet Booking Code")
    btn_vip = types.KeyboardButton("👑 VIP Group Info")
    btn_contact = types.KeyboardButton("📞 Contact Support")
    markup.add(btn_odds, btn_code, btn_vip, btn_contact)
    
    msg = (
        f"Welcome **{user_name}** to **Willys Media World Predictions**! ⚽🔥\n\n"
        f"We specialize in daily high-probability **1.50 - 2.00 Odds**.\n\n"
        f"Please select an option below:"
    )
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🎯 Today's Safe 2-Odds":
        text = (
            f"⚽ **TODAY'S SAFE 1.50 - 2.00 ODDS** ⚽\n"
            f"-----------------------------------\n"
            f"📌 **Match 1:** {DATA['match1_name']}\n"
            f"💡 **Tip:** {DATA['match1_tip']}\n\n"
            f"📌 **Match 2:** {DATA['match2_name']}\n"
            f"💡 **Tip:** {DATA['match2_tip']}\n\n"
            f"📊 **Total Odds:** ~{DATA['total_odds']}\n"
            f"-----------------------------------\n"
            f"🔑 **SportyBet Code:** `{DATA['sportybet_code']}`\n\n"
            f"⚠️ *Bet responsibly! Always manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "📱 SportyBet Booking Code":
        text = (
            f"📱 **SPORTYBET BOOKING CODE** 📱\n\n"
            f"🔑 **Code:** `{DATA['sportybet_code']}` (Tap to copy)\n"
            f"🌐 **Platform:** SportyBet.com\n\n"
            f"👉 [Click Here to Play Games on SportyBet]({DATA['affiliate_link']})"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "👑 VIP Group Info":
        text = (
            "👑 **WILLYS VIP WINNERS CLUB** 👑\n\n"
            "✅ Daily 1.50 - 2.00 Banker Games\n"
            "✅ 4-Day Rollover Strategy\n"
            "💳 **Fee:** N3,000 / Month\n\n"
            "📩 Click 'Contact Support' to chat with Admin on WhatsApp to join VIP!"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "📞 Contact Support":
        text = (
            "🏢 **WILLYS MEDIA WORLD**\n"
            "-----------------------------------\n"
            "📍 **Location:** Ijebu-Imusin, Ogun State\n"
            "📧 **Email:** willysmediaworld@gmail.com\n"
            "📱 **Phone:** +2349018363715\n\n"
            "💬 **WhatsApp Admin:** [Click Here to Chat](https://wa.me/2349018363715)\n"
            "-----------------------------------"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

def run_bot():
    bot.infinity_polling()

# ==========================================
# 2. FLASK WEBSITE ENGINE
# ==========================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Willys Media World - Daily 2-Odds Predictions</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; padding: 15px; text-align: center; }
        .container { max-width: 500px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #1e293b, #334155); padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #475569; }
        h1 { color: #22c55e; font-size: 22px; margin-bottom: 5px; }
        p.subtitle { color: #94a3b8; font-size: 13px; }
        .card { background-color: #1e293b; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; text-align: left; }
        .card h2 { color: #38bdf8; font-size: 16px; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 6px; }
        .match { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; background: #0f172a; padding: 10px; border-radius: 8px; }
        .match-info { font-size: 13px; font-weight: bold; }
        .tip { color: #22c55e; font-size: 12px; margin-top: 3px; }
        .code-box { background: #0284c7; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-top: 12px; font-weight: bold; font-size: 14px; }
        .code-box span { background: #0f172a; padding: 4px 10px; border-radius: 4px; font-family: monospace; letter-spacing: 2px; color: #38bdf8; }
        .btn { display: block; width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; }
        .btn-telegram { background-color: #0284c7; color: white; }
        .btn-whatsapp { background-color: #22c55e; color: white; }
        .btn-sporty { background-color: #e11d48; color: white; margin-top: 10px; }
        .footer { color: #64748b; font-size: 11px; margin-top: 25px; line-height: 1.5; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>WILLYS MEDIA WORLD</h1>
        <p class="subtitle">🎯 Auto-Analyzed 1.50 - 2.00 Safe Odds</p>
    </div>
    
    <div class="card">
        <h2>⚽ Today's Safe 2-Odds</h2>
        
        <div class="match">
            <div>
                <div class="match-info">{{ data['match1_name'] }}</div>
                <div class="tip">Tip: {{ data['match1_tip'] }}</div>
            </div>
        </div>
        
        <div class="match">
            <div>
                <div class="match-info">{{ data['match2_name'] }}</div>
                <div class="tip">Tip: {{ data['match2_tip'] }}</div>
            </div>
        </div>
        
        <div class="code-box">SportyBet Code: <span>{{ data['sportybet_code'] }}</span></div>
        <a href="{{ data['affiliate_link'] }}" target="_blank" class="btn btn-sporty">🎰 Play Games on SportyBet</a>
    </div>

    <div class="card">
        <h2>🔥 Join Betting Communities</h2>
        <a href="https://t.me/Willys2Odds_bot" target="_blank" class="btn btn-telegram">🤖 Open Telegram Bot</a>
        <a href="https://wa.me/2349018363715" target="_blank" class="btn btn-whatsapp">💬 Join WhatsApp VIP Group</a>
    </div>

    <div class="footer">
        <p><strong>Willys Media World</strong></p>
        <p>📍 Okepo Quarters, Ijebu-Imusin, Ogun State.</p>
        <p>📧 willysmediaworld@gmail.com | 📱 +2349018363715</p>
        <p style="margin-top: 8px;">⚠️ 18+ Play Responsibly.</p>
    </div>
</div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=DATA)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
    
