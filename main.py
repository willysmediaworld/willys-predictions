import threading
import telebot
from telebot import types
from flask import Flask, render_template_string
import os
import json
import requests
import urllib.parse
from datetime import datetime, timezone, timedelta

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
ODDS_API_KEY = "a25ddc2f3ceffcb7f959e224f6a40d4f"
ADMIN_PASSWORD = "willys123"
BOT_TOKEN = "8700629519:AAFUXLN7K7XrS0DTMQ_sULOnlAvLIHc-SrU"
SITE_DOMAIN = "https://willys-predictions.onrender.com"

LEAGUE_DETAILS = {
    'soccer_epl': {'name': 'Premier League', 'country': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 England'},
    'soccer_spain_la_liga': {'name': 'La Liga', 'country': '🇪🇸 Spain'},
    'soccer_germany_bundesliga': {'name': 'Bundesliga', 'country': '🇩🇪 Germany'},
    'soccer_italy_serie_a': {'name': 'Serie A', 'country': '🇮🇹 Italy'},
    'soccer_france_ligue_one': {'name': 'Ligue 1', 'country': '🇫🇷 France'},
    'soccer_uefa_champs_league': {'name': 'Champions League', 'country': '🇪🇺 UEFA'},
    'soccer_uefa_europa_league': {'name': 'Europa League', 'country': '🇪🇺 UEFA'}
}

# DEFAULT MULTI-MATCH ULTRA-SAFE ACCUMULATOR
DEFAULT_DATA = {
    "matches": [
        {
            "id": 1,
            "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 England",
            "league": "Premier League",
            "teams": "Manchester City vs Luton",
            "tip": "Home Win or Draw (1X)",
            "odd": 1.08,
            "time": "15:00 WAT",
            "status": "Scheduled"
        },
        {
            "id": 2,
            "country": "🇪🇸 Spain",
            "league": "La Liga",
            "teams": "Real Madrid vs Cadiz",
            "tip": "Over 0.5 Goals",
            "odd": 1.12,
            "time": "17:30 WAT",
            "status": "Scheduled"
        },
        {
            "id": 3,
            "country": "🇩🇪 Germany",
            "league": "Bundesliga",
            "teams": "Bayern Munich vs Cologne",
            "tip": "Home Win (1)",
            "odd": 1.15,
            "time": "18:30 WAT",
            "status": "Scheduled"
        },
        {
            "id": 4,
            "country": "🇫🇷 France",
            "league": "Ligue 1",
            "teams": "PSG vs Clermont",
            "tip": "Over 1.5 Goals",
            "odd": 1.18,
            "time": "20:00 WAT",
            "status": "Scheduled"
        }
    ],
    "total_odds": "1.64",
    "sportybet_code": "BC982A1",
    "affiliate_link": "https://www.sportybet.com/ng/",
    "last_updated": "Default"
}

def load_data():
    try:
        if os.path.exists("data.json"):
            with open("data.json", "r") as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_DATA

def save_data(data):
    try:
        with open("data.json", "w") as f:
            json.dump(data, f)
    except Exception:
        pass

DATA = load_data()


# ==========================================
# AUTOMATED MATCH FETCHING ENGINE
# ==========================================
def fetch_automated_predictions():
    global DATA
    selected_matches = []
    accumulated_odds = 1.0
    
    now_utc = datetime.now(timezone.utc)
    max_lookahead = now_utc + timedelta(hours=36)
    
    match_id_counter = 1
    for league_key, details in LEAGUE_DETAILS.items():
        if accumulated_odds >= 1.55 and len(selected_matches) >= 3:
            break
            
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                events = res.json()
                for event in events:
                    commence_str = event.get('commence_time')
                    if not commence_str: continue
                        
                    commence_dt = datetime.fromisoformat(commence_str.replace('Z', '+00:00'))
                    if commence_dt < (now_utc - timedelta(hours=2)) or commence_dt > max_lookahead:
                        continue
                    
                    # Convert UTC to WAT (UTC+1)
                    wat_dt = commence_dt + timedelta(hours=1)
                    match_time_str = wat_dt.strftime("%H:%M WAT")
                    
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
                        
                        if 1.08 <= price <= 1.28:
                            match_title = f"{home_team} vs {away_team}"
                            tip_text = f"{name} Win/Safe @ {price}"
                            
                            if not any(m['teams'] == match_title for m in selected_matches):
                                selected_matches.append({
                                    "id": match_id_counter,
                                    "country": details['country'],
                                    "league": details['name'],
                                    "teams": match_title,
                                    "tip": tip_text,
                                    "odd": price,
                                    "time": match_time_str,
                                    "status": "Scheduled"
                                })
                                match_id_counter += 1
                                accumulated_odds *= price
                                break
                    
                    if accumulated_odds >= 1.55 and len(selected_matches) >= 3:
                        break
        except Exception:
            pass

    if len(selected_matches) >= 2:
        DATA['matches'] = selected_matches
        DATA['total_odds'] = str(round(accumulated_odds, 2))
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(DATA)
        return True, f"Auto-selected {len(selected_matches)} Banker Matches! Total Odds: ~{round(accumulated_odds, 2)}"
    else:
        return False, "Using stored 99% banker accumulator ticket."


# ==========================================
# 1. TELEGRAM BOT ENGINE
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

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
    bot.reply_to(message, "🔍 Scanning global leagues for 99% Minimum-Odds Banker matches... Please wait.")
    def run_fetch():
        success, msg = fetch_automated_predictions()
        reply = f"✅ **AUTO-FETCH COMPLETE!** 🔥\n\n{msg}\n\n👉 Send `/code YOURCODE` to update SportyBet Code!"
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")
    threading.Thread(target=run_fetch).start()

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
        f"We specialize in daily high-probability **1.50 - 2.00 Odds** accumulators.\n\n"
        f"Please select an option below:"
    )
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🎯 Today's Safe 2-Odds":
        matches_text = ""
        matches = DATA.get('matches', DEFAULT_DATA['matches'])
        for i, m in enumerate(matches, 1):
            subpage_url = f"{SITE_DOMAIN}/match/{m.get('id', i)}"
            matches_text += f"📌 **Match {i}:** {m.get('country','⚽')} {m.get('league','')}\n"
            matches_text += f"⚽ **Teams:** [{m.get('teams','')}]({subpage_url})\n"
            matches_text += f"🕒 **Time:** {m.get('time','Scheduled')}\n"
            matches_text += f"💡 **Tip:** {m.get('tip','')}\n\n"
            
        text = (
            f"⚽ **TODAY'S 99% BANKER ACCUMULATOR TICKET** ⚽\n"
            f"-----------------------------------\n"
            f"{matches_text}"
            f"📊 **Total Combined Odds:** ~{DATA.get('total_odds', '1.64')}\n"
            f"-----------------------------------\n"
            f"🔑 **SportyBet Code:** `{DATA.get('sportybet_code', 'BC982A1')}`\n\n"
            f"⚠️ *Bet responsibly! Manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "📱 SportyBet Booking Code":
        text = (
            f"📱 **SPORTYBET BOOKING CODE** 📱\n\n"
            f"🔑 **Code:** `{DATA.get('sportybet_code', 'BC982A1')}` (Tap to copy)\n"
            f"🌐 **Platform:** SportyBet.com\n\n"
            f"👉 [Click Here to Load Slip on SportyBet]({DATA.get('affiliate_link', 'https://www.sportybet.com/ng/')})"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "👑 VIP Group Info":
        text = (
            "👑 **WILLYS VIP WINNERS CLUB** 👑\n\n"
            "✅ Daily 1.50 - 2.00 Banker Accumulators\n"
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

def run_bot_loop():
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=30)
        except Exception:
            pass

# ==========================================
# 2. FLASK WEBSITE ENGINE
# ==========================================
app = Flask(__name__)

# MAIN HOME TEMPLATE
HOME_HTML = """
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
        .league-badge { font-size: 11px; color: #fbbf24; font-weight: bold; margin-bottom: 3px; display: flex; justify-content: space-between; }
        .match-time { color: #38bdf8; font-size: 11px; }
        .match { margin-bottom: 12px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #22c55e; text-decoration: none; display: block; color: inherit; }
        .match:hover { background: #1e293b; }
        .match-info { font-size: 14px; font-weight: bold; color: #ffffff; }
        .tip { color: #22c55e; font-size: 12px; margin-top: 4px; }
        .click-hint { font-size: 10px; color: #64748b; margin-top: 4px; }
        .total-odds { background: #334155; padding: 10px; border-radius: 6px; text-align: center; color: #22c55e; font-weight: bold; margin-top: 10px; font-size: 15px; }
        .code-box { background: #0284c7; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-top: 12px; font-weight: bold; font-size: 14px; }
        .code-box span { background: #0f172a; padding: 4px 10px; border-radius: 4px; font-family: monospace; letter-spacing: 2px; color: #38bdf8; }
        .btn { display: block; width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; border: none; cursor: pointer; }
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
        <p class="subtitle">🎯 99% Banker Minimum-Odds Accumulator</p>
    </div>
    
    <div class="card">
        <h2>⚽ Today's Accumulator Ticket</h2>
        <p style="font-size:11px; color:#94a3b8; margin-bottom:10px;">💡 <i>Tap any match below to view LiveScore Subpage!</i></p>
        
        {% for match in data.get('matches', []) %}
        <a href="/match/{{ match.get('id', loop.index) }}" class="match">
            <div class="league-badge">
                <span>{{ match.get('country','') }} - {{ match.get('league','') }}</span>
                <span class="match-time">⏰ {{ match.get('time','Scheduled') }}</span>
            </div>
            <div class="match-info">⚽ {{ match.get('teams','') }}</div>
            <div class="tip">Tip: {{ match.get('tip','') }}</div>
            <div class="click-hint">⚡ Tap to view LiveScore Center</div>
        </a>
        {% endfor %}
        
        <div class="total-odds">📊 Combined Ticket Odds: ~{{ data.get('total_odds', '1.64') }}</div>
        
        <div class="code-box">SportyBet Code: <span>{{ data.get('sportybet_code', 'BC982A1') }}</span></div>
        
        <!-- DIRECT LINK BUTTON FOR MOBILE COMPATIBILITY -->
        <a href="{{ data.get('affiliate_link', 'https://www.sportybet.com/ng/') }}" 
           target="_blank" 
           onclick="navigator.clipboard.writeText('{{ data.get('sportybet_code', 'BC982A1') }}'); alert('🔑 Booking Code [{{ data.get('sportybet_code', 'BC982A1') }}] copied! Opening SportyBet...');" 
           class="btn btn-sporty">
           🎰 Copy Code & Open SportyBet
        </a>
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

# MATCH DETAILS & LIVESCORE SUBPAGE TEMPLATE
MATCH_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ match['teams'] }} - Willys Media World</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; padding: 15px; text-align: center; }
        .container { max-width: 500px; margin: 0 auto; }
        .back-btn { display: inline-block; background: #334155; color: #38bdf8; padding: 8px 15px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; margin-bottom: 15px; text-align: left; }
        .card { background-color: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; text-align: left; }
        .league { font-size: 12px; color: #fbbf24; font-weight: bold; text-transform: uppercase; }
        h1 { color: #ffffff; font-size: 20px; margin: 10px 0; }
        .time-badge { color: #38bdf8; font-size: 13px; font-weight: bold; margin-bottom: 10px; }
        .badge { display: inline-block; background: #22c55e; color: #000; font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px; margin-bottom: 15px; }
        .live-box { background: #0f172a; padding: 15px; border-radius: 10px; border: 1px solid #0284c7; text-align: center; margin-top: 15px; }
        .live-title { color: #38bdf8; font-size: 14px; font-weight: bold; margin-bottom: 8px; }
        .score { font-size: 24px; font-weight: bold; color: #22c55e; letter-spacing: 2px; }
        .status { font-size: 11px; color: #94a3b8; margin-top: 5px; }
        .btn { display: block; width: 100%; padding: 12px; margin-top: 15px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; background: #e11d48; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
<div class="container">
    <div style="text-align:left;">
        <a href="/" class="back-btn">⬅ Back to Accumulator Ticket</a>
    </div>

    <div class="card">
        <div class="league">{{ match['country'] }} - {{ match['league'] }}</div>
        <h1>⚽ {{ match['teams'] }}</h1>
        <div class="time-badge">⏰ Kickoff: {{ match['time'] }}</div>
        <div class="badge">Banker Tip: {{ match['tip'] }}</div>
        
        <div class="live-box">
            <div class="live-title">⚡ LIVESCORE CENTER</div>
            <div class="score">0 - 0</div>
            <div class="status">● {{ match['status'] }}</div>
        </div>

        <a href="{{ data.get('affiliate_link', 'https://www.sportybet.com/ng/') }}" target="_blank" class="btn">🎰 Bet Match on SportyBet</a>
    </div>
</div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_HTML, data=DATA)

@app.route('/match/<int:match_id>')
def match_detail(match_id):
    matches = DATA.get('matches', DEFAULT_DATA['matches'])
    selected = next((m for m in matches if m.get('id') == match_id), None)
    if not selected and matches:
        selected = matches[0]
    return render_template_string(MATCH_HTML, match=selected, data=DATA)

if __name__ == '__main__':
    t = threading.Thread(target=run_bot_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)            "status": "Scheduled / Live Tracking Active"
        },
        {
            "id": 2,
            "country": "🇪🇸 Spain",
            "league": "La Liga",
            "teams": "Real Madrid vs Cadiz",
            "tip": "Over 0.5 Goals",
            "odd": 1.12,
            "status": "Scheduled / Live Tracking Active"
        },
        {
            "id": 3,
            "country": "🇩🇪 Germany",
            "league": "Bundesliga",
            "teams": "Bayern Munich vs Cologne",
            "tip": "Home Win (1)",
            "odd": 1.15,
            "status": "Scheduled / Live Tracking Active"
        },
        {
            "id": 4,
            "country": "🇫🇷 France",
            "league": "Ligue 1",
            "teams": "PSG vs Clermont",
            "tip": "Over 1.5 Goals",
            "odd": 1.18,
            "status": "Scheduled / Live Tracking Active"
        }
    ],
    "total_odds": "1.64",
    "sportybet_code": "BC982A1",
    "affiliate_link": "https://www.sportybet.com/ng/",
    "last_updated": "Default"
}

def load_data():
    try:
        if os.path.exists("data.json"):
            with open("data.json", "r") as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_DATA

def save_data(data):
    try:
        with open("data.json", "w") as f:
            json.dump(data, f)
    except Exception:
        pass

DATA = load_data()


# ==========================================
# AUTOMATED MATCH FETCHING ENGINE
# ==========================================
def fetch_automated_predictions():
    global DATA
    selected_matches = []
    accumulated_odds = 1.0
    
    now_utc = datetime.now(timezone.utc)
    max_lookahead = now_utc + timedelta(hours=36)
    
    match_id_counter = 1
    for league_key, details in LEAGUE_DETAILS.items():
        if accumulated_odds >= 1.55 and len(selected_matches) >= 3:
            break
            
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        try:
            res = requests.get(url, timeout=3)
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
                        
                        if 1.08 <= price <= 1.28:
                            match_title = f"{home_team} vs {away_team}"
                            tip_text = f"{name} Win/Safe @ {price}"
                            
                            if not any(m['teams'] == match_title for m in selected_matches):
                                selected_matches.append({
                                    "id": match_id_counter,
                                    "country": details['country'],
                                    "league": details['name'],
                                    "teams": match_title,
                                    "tip": tip_text,
                                    "odd": price,
                                    "status": "Scheduled / Live Tracking Active"
                                })
                                match_id_counter += 1
                                accumulated_odds *= price
                                break
                    
                    if accumulated_odds >= 1.55 and len(selected_matches) >= 3:
                        break
        except Exception:
            pass

    if len(selected_matches) >= 2:
        DATA['matches'] = selected_matches
        DATA['total_odds'] = str(round(accumulated_odds, 2))
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(DATA)
        return True, f"Auto-selected {len(selected_matches)} Banker Matches! Total Odds: ~{round(accumulated_odds, 2)}"
    else:
        return False, "Using stored 99% banker accumulator ticket."


# ==========================================
# 1. TELEGRAM BOT ENGINE
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

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
    bot.reply_to(message, "🔍 Scanning global leagues for 99% Banker matches... Please wait.")
    def run_fetch():
        success, msg = fetch_automated_predictions()
        reply = f"✅ **AUTO-FETCH COMPLETE!** 🔥\n\n{msg}\n\n👉 Send `/code YOURCODE` to update SportyBet Code!"
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")
    threading.Thread(target=run_fetch).start()

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
        f"We specialize in daily high-probability **1.50 - 2.00 Odds** accumulators.\n\n"
        f"Please select an option below:"
    )
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🎯 Today's Safe 2-Odds":
        matches_text = ""
        matches = DATA.get('matches', DEFAULT_DATA['matches'])
        for i, m in enumerate(matches, 1):
            subpage_url = f"{SITE_DOMAIN}/match/{m.get('id', i)}"
            matches_text += f"📌 **Match {i}:** {m.get('country','⚽')} {m.get('league','')}\n"
            matches_text += f"⚽ **Teams:** [{m.get('teams','')}]({subpage_url}) *(Tap for LiveScore)*\n"
            matches_text += f"💡 **Tip:** {m.get('tip','')}\n\n"
            
        text = (
            f"⚽ **TODAY'S 99% BANKER ACCUMULATOR TICKET** ⚽\n"
            f"-----------------------------------\n"
            f"{matches_text}"
            f"📊 **Total Combined Odds:** ~{DATA.get('total_odds', '1.64')}\n"
            f"-----------------------------------\n"
            f"🔑 **SportyBet Code:** `{DATA.get('sportybet_code', 'BC982A1')}`\n\n"
            f"⚠️ *Bet responsibly! Manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "📱 SportyBet Booking Code":
        text = (
            f"📱 **SPORTYBET BOOKING CODE** 📱\n\n"
            f"🔑 **Code:** `{DATA.get('sportybet_code', 'BC982A1')}` (Tap to copy)\n"
            f"🌐 **Platform:** SportyBet.com\n\n"
            f"👉 [Click Here to Load Slip on SportyBet]({DATA.get('affiliate_link', 'https://www.sportybet.com/ng/')})"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "👑 VIP Group Info":
        text = (
            "👑 **WILLYS VIP WINNERS CLUB** 👑\n\n"
            "✅ Daily 1.50 - 2.00 Banker Accumulators\n"
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

def run_bot_loop():
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=30)
        except Exception:
            pass

# ==========================================
# 2. FLASK WEBSITE ENGINE
# ==========================================
app = Flask(__name__)

# MAIN HOME TEMPLATE
HOME_HTML = """
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
        .match { margin-bottom: 12px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #22c55e; text-decoration: none; display: block; color: inherit; }
        .match:hover { background: #1e293b; }
        .match-info { font-size: 14px; font-weight: bold; color: #38bdf8; }
        .tip { color: #22c55e; font-size: 12px; margin-top: 4px; }
        .click-hint { font-size: 10px; color: #64748b; margin-top: 4px; }
        .total-odds { background: #334155; padding: 10px; border-radius: 6px; text-align: center; color: #22c55e; font-weight: bold; margin-top: 10px; font-size: 15px; }
        .code-box { background: #0284c7; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-top: 12px; font-weight: bold; font-size: 14px; }
        .code-box span { background: #0f172a; padding: 4px 10px; border-radius: 4px; font-family: monospace; letter-spacing: 2px; color: #38bdf8; }
        .btn { display: block; width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; cursor: pointer; border: none; }
        .btn-telegram { background-color: #0284c7; color: white; }
        .btn-whatsapp { background-color: #22c55e; color: white; }
        .btn-sporty { background-color: #e11d48; color: white; margin-top: 10px; }
        .footer { color: #64748b; font-size: 11px; margin-top: 25px; line-height: 1.5; }
    </style>
    <script>
        function loadSportyBetSlip(code, affiliateUrl) {
            navigator.clipboard.writeText(code);
            alert("🔑 Booking Code [" + code + "] copied to clipboard! Opening SportyBet...");
            window.open(affiliateUrl, '_blank');
        }
    </script>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>WILLYS MEDIA WORLD</h1>
        <p class="subtitle">🎯 99% Banker Minimum-Odds Accumulator</p>
    </div>
    
    <div class="card">
        <h2>⚽ Today's Accumulator Ticket</h2>
        <p style="font-size:11px; color:#94a3b8; margin-bottom:10px;">💡 <i>Tap any match below to view Internal LiveScore page!</i></p>
        
        {% for match in data.get('matches', []) %}
        <a href="/match/{{ match.get('id', loop.index) }}" class="match">
            <div class="league-badge">{{ match.get('country','') }} - {{ match.get('league','') }}</div>
            <div class="match-info">⚽ {{ match.get('teams','') }}</div>
            <div class="tip">Tip: {{ match.get('tip','') }}</div>
            <div class="click-hint">⚡ Tap to view LiveScore Subpage</div>
        </a>
        {% endfor %}
        
        <div class="total-odds">📊 Combined Ticket Odds: ~{{ data.get('total_odds', '1.64') }}</div>
        
        <div class="code-box">SportyBet Code: <span>{{ data.get('sportybet_code', 'BC982A1') }}</span></div>
        <button onclick="loadSportyBetSlip('{{ data.get('sportybet_code', 'BC982A1') }}', '{{ data.get('affiliate_link', 'https://www.sportybet.com/ng/') }}')" class="btn btn-sporty">🎰 Load Slip on SportyBet</button>
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

# MATCH DETAILS & LIVESCORE SUBPAGE TEMPLATE
MATCH_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ match['teams'] }} - Willys Media World</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; padding: 15px; text-align: center; }
        .container { max-width: 500px; margin: 0 auto; }
        .back-btn { display: inline-block; background: #334155; color: #38bdf8; padding: 8px 15px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; margin-bottom: 15px; text-align: left; }
        .card { background-color: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; text-align: left; }
        .league { font-size: 12px; color: #fbbf24; font-weight: bold; text-transform: uppercase; }
        h1 { color: #ffffff; font-size: 20px; margin: 10px 0; }
        .badge { display: inline-block; background: #22c55e; color: #000; font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px; margin-bottom: 15px; }
        .live-box { background: #0f172a; padding: 15px; border-radius: 10px; border: 1px solid #0284c7; text-align: center; margin-top: 15px; }
        .live-title { color: #38bdf8; font-size: 14px; font-weight: bold; margin-bottom: 8px; }
        .score { font-size: 24px; font-weight: bold; color: #22c55e; letter-spacing: 2px; }
        .status { font-size: 11px; color: #94a3b8; margin-top: 5px; }
        .btn { display: block; width: 100%; padding: 12px; margin-top: 15px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; background: #e11d48; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
<div class="container">
    <div style="text-align:left;">
        <a href="/" class="back-btn">⬅ Back to Accumulator Ticket</a>
    </div>

    <div class="card">
        <div class="league">{{ match['country'] }} - {{ match['league'] }}</div>
        <h1>⚽ {{ match['teams'] }}</h1>
        <div class="badge">Banker Tip: {{ match['tip'] }}</div>
        
        <div class="live-box">
            <div class="live-title">⚡ LIVESCORE CENTER</div>
            <div class="score">0 - 0</div>
            <div class="status">● {{ match['status'] }}</div>
        </div>

        <a href="{{ data.get('affiliate_link', 'https://www.sportybet.com/ng/') }}" target="_blank" class="btn">🎰 Bet Match on SportyBet</a>
    </div>
</div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_HTML, data=DATA)

@app.route('/match/<int:match_id>')
def match_detail(match_id):
    matches = DATA.get('matches', DEFAULT_DATA['matches'])
    selected = next((m for m in matches if m.get('id') == match_id), None)
    if not selected and matches:
        selected = matches[0]
    return render_template_string(MATCH_HTML, match=selected, data=DATA)

if __name__ == '__main__':
    t = threading.Thread(target=run_bot_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
    
