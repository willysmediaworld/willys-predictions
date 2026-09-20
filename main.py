import threading
import telebot
from telebot import types
from flask import Flask, render_template_string
import os
import json
import requests
import time
from datetime import datetime, timezone, timedelta

# ==========================================
# CONFIGURATION & LEAGUE MAPS
# ==========================================
ODDS_API_KEY = "a25ddc2f3ceffcb7f959e224f6a40d4f"
ADMIN_PASSWORD = "willys123"
BOT_TOKEN = "8700629519:AAFUXLN7K7XrS0DTMQ_sULOnlAvLIHc-SrU"

LEAGUE_DETAILS = {
    'soccer_epl': {'name': 'Premier League', 'country': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 England'},
    'soccer_spain_la_liga': {'name': 'La Liga', 'country': '🇪🇸 Spain'},
    'soccer_germany_bundesliga': {'name': 'Bundesliga', 'country': '🇩🇪 Germany'},
    'soccer_italy_serie_a': {'name': 'Serie A', 'country': '🇮🇹 Italy'},
    'soccer_france_ligue_one': {'name': 'Ligue 1', 'country': '🇫🇷 France'},
    'soccer_uefa_champs_league': {'name': 'Champions League', 'country': '🇪🇺 UEFA'},
    'soccer_uefa_europa_league': {'name': 'Europa League', 'country': '🇪🇺 UEFA'},
    'soccer_netherlands_eredivisie': {'name': 'Eredivisie', 'country': '🇳🇱 Netherlands'},
    'soccer_portugal_primeira_liga': {'name': 'Primeira Liga', 'country': '🇵🇹 Portugal'}
}

DEFAULT_DATA = {
    "matches": [
        {
            "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 England",
            "league": "Premier League",
            "teams": "Manchester City vs Everton",
            "tip": "Home Win or Draw (1X)",
            "odd": 1.18
        },
        {
            "country": "🇪🇸 Spain",
            "league": "La Liga",
            "teams": "Real Madrid vs Cadiz",
            "tip": "Over 1.5 Goals",
            "odd": 1.22
        },
        {
            "country": "🇩🇪 Germany",
            "league": "Bundesliga",
            "teams": "Bayern Munich vs Bochum",
            "tip": "Home Win (1)",
            "odd": 1.15
        }
    ],
    "total_odds": "1.66",
    "sportybet_code": "BC982A1",
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
# FAST AUTOMATED SCANNER
# ==========================================
def fetch_automated_predictions():
    global DATA
    selected_matches = []
    accumulated_odds = 1.0
    
    now_utc = datetime.now(timezone.utc)
    max_lookahead = now_utc + timedelta(hours=48)
    
    for league_key, details in LEAGUE_DETAILS.items():
        if accumulated_odds >= 1.50 and len(selected_matches) >= 2:
            break
            
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                events = res.json()
                for event in events:
                    commence_str = event.get('commence_time')
                    if not commence_str: continue
                        
                    commence_dt = datetime.fromisoformat(commence_str.replace('Z', '+00:00'))
                    if commence_dt < (now_utc - timedelta(hours=2)) or commence_dt > max_lookahead:
                        continue
                    
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
                        
                        # SAFE BANKER RANGE (1.12 to 1.38)
                        if 1.12 <= price <= 1.38:
                            match_title = f"{home_team} vs {away_team}"
                            tip_text = f"{name} Win @ {price}"
                            
                            if not any(m['teams'] == match_title for m in selected_matches):
                                selected_matches.append({
                                    "country": details['country'],
                                    "league": details['name'],
                                    "teams": match_title,
                                    "tip": tip_text,
                                    "odd": price
                                })
                                accumulated_odds *= price
                                break
                    
                    if accumulated_odds >= 1.50 and len(selected_matches) >= 2:
                        break
        except Exception as e:
            print(f"Error fetching {league_key}: {e}")

    if selected_matches:
        DATA['matches'] = selected_matches
        DATA['total_odds'] = str(round(accumulated_odds, 2))
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(DATA)
        return True, f"Auto-selected {len(selected_matches)} Banker Matches! Total Odds: ~{round(accumulated_odds, 2)}"
    else:
        return False, "No banker games found in current window. Stored matches displayed."


def get_quick_livescores():
    scores_list = []
    # Quick scan on EPL and Champions League for fast response
    for league_key in ['soccer_epl', 'soccer_uefa_champs_league', 'soccer_spain_la_liga']:
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/scores/?apiKey={ODDS_API_KEY}&daysFrom=1"
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                events = res.json()
                for e in events:
                    home = e.get('home_team')
                    away = e.get('away_team')
                    scores = e.get('scores')
                    completed = e.get('completed', False)
                    
                    if scores:
                        s_dict = {s['name']: s['score'] for s in scores}
                        status = "FINISHED" if completed else "LIVE ⚽"
                        score_str = f"{s_dict.get(home, 0)} - {s_dict.get(away, 0)}"
                        details = LEAGUE_DETAILS.get(league_key, {'country': '⚽', 'name': 'League'})
                        scores_list.append(f"{details['country']} {details['name']} [{status}]:\n{home}  **{score_str}**  {away}")
                        if len(scores_list) >= 3: break
        except Exception:
            pass
            
    if not scores_list:
        return "⚡ **LIVESCORES UPDATE** ⚡\n-----------------------------------\nNo live or completed matches in scanned major leagues today.\nCheck back during match hours!"
    return "⚡ **LIVESCORES UPDATE** ⚡\n-----------------------------------\n" + "\n\n".join(scores_list)


# ==========================================
# 1. TELEGRAM BOT ENGINE (NON-BLOCKING)
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['code'])
def update_code_only(message):
    try:
        new_code = message.text.replace('/code', '').strip().upper()
        if not new_code:
            bot.reply_to(message, "❌ Provide a code. Example: `/code BC982A1`", parse_mode="Markdown")
            return
            
        DATA['sportybet_code'] = new_code
        save_data(DATA)
        bot.reply_to(message, f"✅ **SPORTYBET CODE UPDATED:** `{new_code}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['fetch'])
def trigger_fetch(message):
    bot.reply_to(message, "🔍 Scanning global leagues for 99% Banker Matches... Please wait.")
    def run_fetch():
        success, msg = fetch_automated_predictions()
        reply = f"✅ **AUTO-FETCH COMPLETE!** 🔥\n\n{msg}\n\n👉 Send `/code YOURCODE` to update SportyBet Code!" if success else f"⚠️ {msg}"
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")
    threading.Thread(target=run_fetch).start()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_odds = types.KeyboardButton("🎯 Today's Safe 2-Odds")
    btn_code = types.KeyboardButton("📱 SportyBet Booking Code")
    btn_scores = types.KeyboardButton("⚡ LiveScores")
    btn_vip = types.KeyboardButton("👑 VIP Group Info")
    btn_contact = types.KeyboardButton("📞 Contact Support")
    markup.add(btn_odds, btn_code, btn_scores, btn_vip, btn_contact)
    
    msg = (
        f"Welcome **{user_name}** to **Willys Media World Predictions**! ⚽🔥\n\n"
        f"We specialize in daily high-probability **1.50 - 2.00 Odds**.\n\n"
        f"Please select an option below:"
    )
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🎯 Today's Safe 2-Odds":
        matches_text = ""
        matches = DATA.get('matches', DEFAULT_DATA['matches'])
        for i, m in enumerate(matches, 1):
            matches_text += f"📌 **Match {i}:** {m.get('country','⚽')} - {m.get('league','')}\n"
            matches_text += f"⚽ **Teams:** {m.get('teams','')}\n"
            matches_text += f"💡 **Tip:** {m.get('tip','')}\n\n"
            
        text = (
            f"⚽ **TODAY'S SAFE 1.50 - 2.00 BANKER TICKET** ⚽\n"
            f"-----------------------------------\n"
            f"{matches_text}"
            f"📊 **Total Combined Odds:** ~{DATA.get('total_odds', '1.60')}\n"
            f"-----------------------------------\n"
            f"🔑 **SportyBet Code:** `{DATA.get('sportybet_code', 'BC982A1')}`\n\n"
            f"⚠️ *Bet responsibly! Manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "⚡ LiveScores":
        bot.send_message(message.chat.id, "⌛ Checking live scores...", parse_mode="Markdown")
        def run_scores():
            ls_text = get_quick_livescores()
            bot.send_message(message.chat.id, ls_text, parse_mode="Markdown")
        threading.Thread(target=run_scores).start()

    elif message.text == "📱 SportyBet Booking Code":
        text = (
            f"📱 **SPORTYBET BOOKING CODE** 📱\n\n"
            f"🔑 **Code:** `{DATA.get('sportybet_code', 'BC982A1')}` (Tap to copy)\n"
            f"🌐 **Platform:** SportyBet.com\n\n"
            f"👉 [Click Here to Load Slip on SportyBet]({DATA.get('affiliate_link', 'https://www.sportybet.com')})"
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

def run_bot_forever():
    while True:
        try:
            print("Starting Telegram Bot Polling...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Bot Polling Error: {e}. Restarting in 5 seconds...")
            time.sleep(5)


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
        .league-badge { font-size: 11px; color: #fbbf24; font-weight: bold; margin-bottom: 3px; }
        .match { margin-bottom: 12px; background: #0f172a; padding: 10px; border-radius: 8px; border-left: 3px solid #22c55e; }
        .match-info { font-size: 13px; font-weight: bold; color: #ffffff; }
        .tip { color: #22c55e; font-size: 12px; margin-top: 3px; }
        .total-odds { background: #334155; padding: 8px; border-radius: 6px; text-align: center; color: #22c55e; font-weight: bold; margin-top: 10px; font-size: 14px; }
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
        <p class="subtitle">🎯 Auto-Analyzed 99% Banker 2-Odds</p>
    </div>
    
    <div class="card">
        <h2>⚽ Today's Banker Accumulator</h2>
        
        {% for match in data.get('matches', []) %}
        <div class="match">
            <div class="league-badge">{{ match.get('country','') }} - {{ match.get('league','') }}</div>
            <div class="match-info">{{ match.get('teams','') }}</div>
            <div class="tip">Tip: {{ match.get('tip','') }}</div>
        </div>
        {% endfor %}
        
        <div class="total-odds">📊 Combined Odds: ~{{ data.get('total_odds', '1.60') }}</div>
        
        <div class="code-box">SportyBet Code: <span>{{ data.get('sportybet_code', 'BC982A1') }}</span></div>
        <a href="{{ data.get('affiliate_link', 'https://www.sportybet.com') }}" target="_blank" class="btn btn-sporty">🎰 Load Slip on SportyBet</a>
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
    bot_thread = threading.Thread(target=run_bot_forever)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)            "odd": 1.22
        },
        {
            "country": "🇪🇸 Spain",
            "league": "La Liga",
            "teams": "Barcelona vs Mallorca",
            "tip": "Over 1.5 Goals",
            "odd": 1.25
        }
    ],
    "total_odds": "1.53",
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
# AUTOMATED 99% BANKER ACCUMULATOR ENGINE
# ==========================================
def fetch_automated_predictions():
    global DATA
    selected_matches = []
    accumulated_odds = 1.0
    
    now_utc = datetime.now(timezone.utc)
    max_lookahead = now_utc + timedelta(hours=36)
    
    for league_key, details in LEAGUE_DETAILS.items():
        if accumulated_odds >= 1.50 and len(selected_matches) >= 2:
            break # Reached target safe odds range (1.50 - 2.00)
            
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        try:
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                events = res.json()
                for event in events:
                    commence_str = event.get('commence_time')
                    if not commence_str: continue
                        
                    commence_dt = datetime.fromisoformat(commence_str.replace('Z', '+00:00'))
                    if commence_dt < (now_utc - timedelta(hours=2)) or commence_dt > max_lookahead:
                        continue
                    
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
                        
                        # ULTRA-SAFE FILTER: Focus strictly on heavy 1.10 - 1.30 odds
                        if 1.10 <= price <= 1.32:
                            match_title = f"{home_team} vs {away_team}"
                            tip_text = f"{name} Win @ {price}"
                            
                            if not any(m['teams'] == match_title for m in selected_matches):
                                selected_matches.append({
                                    "country": details['country'],
                                    "league": details['name'],
                                    "teams": match_title,
                                    "tip": tip_text,
                                    "odd": price
                                })
                                accumulated_odds *= price
                                break
                    
                    if accumulated_odds >= 1.50 and len(selected_matches) >= 2:
                        break
        except Exception as e:
            print(f"Error fetching {league_key}: {e}")

    if selected_matches:
        DATA['matches'] = selected_matches
        DATA['total_odds'] = str(round(accumulated_odds, 2))
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(DATA)
        return True, f"Auto-selected {len(selected_matches)} Ultra-Safe Banker Matches! Total Odds: ~{round(accumulated_odds, 2)}"
    else:
        return False, "No ultra-safe 99% banker games starting within 24 hours were found right now."


# Function to fetch LiveScores
def fetch_livescores():
    scores_list = []
    # Query major leagues for live scores
    for league_key, details in list(LEAGUE_DETAILS.items())[:3]:
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/scores/?apiKey={ODDS_API_KEY}&daysFrom=1"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                events = res.json()
                for e in events:
                    if e.get('completed') is False or e.get('scores'):
                        home = e.get('home_team')
                        away = e.get('away_team')
                        scores = e.get('scores')
                        
                        score_str = "VS (Not Started)"
                        if scores:
                            s_dict = {s['name']: s['score'] for s in scores}
                            score_str = f"{s_dict.get(home, 0)} - {s_dict.get(away, 0)}"
                            
                        scores_list.append(f"{details['country']} {details['name']}:\n⚽ {home} {score_str} {away}")
                        if len(scores_list) >= 4: break
        except Exception as ex:
            pass
            
    if not scores_list:
        return "⚡ **LIVE SCORES UPDATE** ⚡\n\nNo live matches currently in play. Check back during match time!"
    return "⚡ **LIVE SCORES UPDATE** ⚡\n-----------------------------------\n" + "\n\n".join(scores_list)


# ==========================================
# 1. TELEGRAM BOT ENGINE
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['code'])
def update_code_only(message):
    try:
        new_code = message.text.replace('/code', '').strip().upper()
        if not new_code:
            bot.reply_to(message, "❌ Please provide a booking code.\nExample: `/code BC982A1`", parse_mode="Markdown")
            return
            
        DATA['sportybet_code'] = new_code
        save_data(DATA)
        bot.reply_to(message, f"✅ **SPORTYBET CODE UPDATED:** `{new_code}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['fetch'])
def trigger_fetch(message):
    bot.reply_to(message, "🔍 Scanning global leagues for 99% Banker Matches & Odds... Please wait.")
    success, msg = fetch_automated_predictions()
    if success:
        reply = f"✅ **AUTO-FETCH COMPLETE!** 🔥\n\n{msg}\n\n👉 Send `/code YOURCODE` to attach SportyBet Booking Code!"
    else:
        reply = f"⚠️ {msg}"
    bot.reply_to(message, reply, parse_mode="Markdown")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_odds = types.KeyboardButton("🎯 Today's Safe 2-Odds")
    btn_code = types.KeyboardButton("📱 SportyBet Booking Code")
    btn_scores = types.KeyboardButton("⚡ LiveScores")
    btn_vip = types.KeyboardButton("👑 VIP Group Info")
    btn_contact = types.KeyboardButton("📞 Contact Support")
    markup.add(btn_odds, btn_code, btn_scores, btn_vip, btn_contact)
    
    msg = (
        f"Welcome **{user_name}** to **Willys Media World Predictions**! ⚽🔥\n\n"
        f"We specialize in daily high-probability **1.50 - 2.00 Odds**.\n\n"
        f"Please select an option below:"
    )
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🎯 Today's Safe 2-Odds":
        matches_text = ""
        for i, m in enumerate(DATA['matches'], 1):
            matches_text += f"📌 **Match {i}:** {m['country']} - {m['league']}\n"
            matches_text += f"⚽ **Teams:** {m['teams']}\n"
            matches_text += f"💡 **Tip:** {m['tip']}\n\n"
            
        text = (
            f"⚽ **TODAY'S SAFE 1.50 - 2.00 BANKER TICKET** ⚽\n"
            f"-----------------------------------\n"
            f"{matches_text}"
            f"📊 **Total Combined Odds:** ~{DATA['total_odds']}\n"
            f"-----------------------------------\n"
            f"🔑 **SportyBet Code:** `{DATA['sportybet_code']}`\n\n"
            f"⚠️ *Bet responsibly! Manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "⚡ LiveScores":
        bot.send_message(message.chat.id, "⌛ Fetching live match scores...", parse_mode="Markdown")
        ls_text = fetch_livescores()
        bot.send_message(message.chat.id, ls_text, parse_mode="Markdown")

    elif message.text == "📱 SportyBet Booking Code":
        text = (
            f"📱 **SPORTYBET BOOKING CODE** 📱\n\n"
            f"🔑 **Code:** `{DATA['sportybet_code']}` (Tap to copy)\n"
            f"🌐 **Platform:** SportyBet.com\n\n"
            f"👉 [Click Here to Load Slip on SportyBet]({DATA['affiliate_link']})"
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
        .league-badge { font-size: 11px; color: #fbbf24; font-weight: bold; margin-bottom: 3px; }
        .match { margin-bottom: 12px; background: #0f172a; padding: 10px; border-radius: 8px; border-left: 3px solid #22c55e; }
        .match-info { font-size: 13px; font-weight: bold; color: #ffffff; }
        .tip { color: #22c55e; font-size: 12px; margin-top: 3px; }
        .total-odds { background: #334155; padding: 8px; border-radius: 6px; text-align: center; color: #22c55e; font-weight: bold; margin-top: 10px; font-size: 14px; }
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
        <p class="subtitle">🎯 Auto-Analyzed 99% Banker 2-Odds</p>
    </div>
    
    <div class="card">
        <h2>⚽ Today's Banker Accumulator</h2>
        
        {% for match in data['matches'] %}
        <div class="match">
            <div class="league-badge">{{ match['country'] }} - {{ match['league'] }}</div>
            <div class="match-info">{{ match['teams'] }}</div>
            <div class="tip">Tip: {{ match['tip'] }}</div>
        </div>
        {% endfor %}
        
        <div class="total-odds">📊 Combined Odds: ~{{ data['total_odds'] }}</div>
        
        <div class="code-box">SportyBet Code: <span>{{ data['sportybet_code'] }}</span></div>
        <a href="{{ data['affiliate_link'] }}" target="_blank" class="btn btn-sporty">🎰 Load Slip on SportyBet</a>
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
    
