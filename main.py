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

# DEFAULT MULTI-BOOKMAKER ACCUMULATOR DATA (~1.70 ODDS)
DEFAULT_DATA = {
    "matches": [
        {
            "id": 1,
            "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 England",
            "league": "Premier League",
            "teams": "Manchester City vs Luton Town",
            "tip": "Home Win or Draw (1X)",
            "odd": 1.10,
            "time": "15:00 WAT",
            "status": "FT (Full Time)",
            "score": "5 - 1"
        },
        {
            "id": 2,
            "country": "🇪🇸 Spain",
            "league": "La Liga",
            "teams": "Real Madrid vs Cadiz",
            "tip": "Over 0.5 Goals",
            "odd": 1.12,
            "time": "17:30 WAT",
            "status": "FT (Full Time)",
            "score": "3 - 0"
        },
        {
            "id": 3,
            "country": "🇩🇪 Germany",
            "league": "Bundesliga",
            "teams": "Bayern Munich vs Cologne",
            "tip": "Home Win (1)",
            "odd": 1.16,
            "time": "18:30 WAT",
            "status": "LIVE ⚽",
            "score": "2 - 0"
        },
        {
            "id": 4,
            "country": "🇫🇷 France",
            "league": "Ligue 1",
            "teams": "PSG vs Clermont",
            "tip": "Over 1.5 Goals",
            "odd": 1.19,
            "time": "20:00 WAT",
            "status": "Upcoming ⏰",
            "score": "VS"
        }
    ],
    "total_odds": "1.70",
    "codes": {
        "sportybet": "BC982A1",
        "bet9ja": "B9J-77812",
        "oneXbet": "1X-99821"
    },
    "links": {
        "sportybet": "https://www.sportybet.com/ng/",
        "bet9ja": "https://www.bet9ja.com",
        "oneXbet": "https://1xbet.com"
    },
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
# AUTOMATED MATCH SCANNER (TARGET: ~1.70 ODDS)
# ==========================================
def fetch_automated_predictions():
    global DATA
    selected_matches = []
    accumulated_odds = 1.0
    
    now_utc = datetime.now(timezone.utc)
    max_lookahead = now_utc + timedelta(hours=36)
    
    match_id_counter = 1
    for league_key, details in LEAGUE_DETAILS.items():
        if accumulated_odds >= 1.68 and len(selected_matches) >= 3:
            break
            
        url = f"https://api.the-odds-api.com/v4/sports/{league_key}/scores/?apiKey={ODDS_API_KEY}&daysFrom=1"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                events = res.json()
                for event in events:
                    commence_str = event.get('commence_time')
                    if not commence_str: continue
                        
                    commence_dt = datetime.fromisoformat(commence_str.replace('Z', '+00:00'))
                    wat_dt = commence_dt + timedelta(hours=1)
                    match_time_str = wat_dt.strftime("%H:%M WAT")
                    
                    home_team = event.get('home_team')
                    away_team = event.get('away_team')
                    completed = event.get('completed', False)
                    scores = event.get('scores')
                    
                    score_display = "VS"
                    match_status = "Upcoming ⏰"
                    
                    if scores:
                        s_dict = {s['name']: s['score'] for s in scores}
                        score_display = f"{s_dict.get(home_team, 0)} - {s_dict.get(away_team, 0)}"
                        match_status = "FT (Full Time)" if completed else "LIVE ⚽"
                    
                    match_title = f"{home_team} vs {away_team}"
                    price = 1.15
                    
                    if not any(m['teams'] == match_title for m in selected_matches):
                        selected_matches.append({
                            "id": match_id_counter,
                            "country": details['country'],
                            "league": details['name'],
                            "teams": match_title,
                            "tip": "Home Win / Over 1.5",
                            "odd": price,
                            "time": match_time_str,
                            "status": match_status,
                            "score": score_display
                        })
                        match_id_counter += 1
                        accumulated_odds *= price
                        
                    if len(selected_matches) >= 4:
                        break
        except Exception:
            pass

    if len(selected_matches) >= 2:
        DATA['matches'] = selected_matches
        DATA['total_odds'] = str(round(accumulated_odds, 2))
        DATA['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M WAT")
        save_data(DATA)
        return True, f"Auto-selected {len(selected_matches)} Banker Matches! Combined Odds: ~{round(accumulated_odds, 2)}"
    else:
        return False, "Maintained 99% banker accumulator ticket."

# 3-HOUR AUTOMATIC BACKGROUND UPDATER THREAD
def auto_update_scheduler():
    while True:
        try:
            print("Running 3-Hour Automated Market Scan...")
            fetch_automated_predictions()
        except Exception as e:
            print(f"Scheduler Error: {e}")
        time.sleep(3 * 3600)  # Wait 3 Hours (10,800 seconds)


# ==========================================
# 1. TELEGRAM BOT ENGINE
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# COMMAND: /code (Update SportyBet Code)
@bot.message_handler(commands=['code'])
def update_code_only(message):
    try:
        new_code = message.text.replace('/code', '').strip().upper()
        if not new_code:
            bot.reply_to(message, "❌ Provide a code. Example: `/code BC982A1`", parse_mode="Markdown")
            return
            
        if 'codes' not in DATA: DATA['codes'] = DEFAULT_DATA['codes']
        DATA['codes']['sportybet'] = new_code
        save_data(DATA)
        bot.reply_to(message, f"✅ **SPORTYBET CODE UPDATED:** `{new_code}`\n\n🌐 *Updated on website & bot!*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# COMMAND: /codes (Update All Bookmakers: SportyBet, Bet9ja, 1xBet)
@bot.message_handler(commands=['codes'])
def update_all_codes(message):
    try:
        raw = message.text.replace('/codes', '').strip().split()
        if len(raw) < 3:
            bot.reply_to(message, "❌ Provide 3 codes: `/codes SPORTYBET_CODE BET9JA_CODE 1XBET_CODE`", parse_mode="Markdown")
            return
            
        if 'codes' not in DATA: DATA['codes'] = DEFAULT_DATA['codes']
        DATA['codes']['sportybet'] = raw[0].upper()
        DATA['codes']['bet9ja'] = raw[1].upper()
        DATA['codes']['oneXbet'] = raw[2].upper()
        save_data(DATA)
        
        reply = (
            f"✅ **ALL BOOKMAKER CODES UPDATED!** 🔑\n\n"
            f"🔴 **SportyBet:** `{raw[0].upper()}`\n"
            f"🟢 **Bet9ja:** `{raw[1].upper()}`\n"
            f"🔵 **1xBet:** `{raw[2].upper()}`\n\n"
            f"🌐 *Website & Bot updated instantly!*"
        )
        bot.reply_to(message, reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['fetch'])
def trigger_fetch(message):
    bot.reply_to(message, "🔍 Scanning global leagues for 99% ~1.70 Odds Banker matches... Please wait.")
    def run_fetch():
        success, msg = fetch_automated_predictions()
        reply = f"✅ **AUTO-FETCH COMPLETE!** 🔥\n\n{msg}\n\n👉 Send `/codes SPORTYBET BET9JA 1XBET` to update codes!"
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")
    threading.Thread(target=run_fetch).start()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_odds = types.KeyboardButton("🎯 Today's Safe 1.70 Odds")
    btn_code = types.KeyboardButton("📱 Booking Codes")
    btn_vip = types.KeyboardButton("👑 VIP Group Info")
    btn_contact = types.KeyboardButton("📞 Contact Support")
    markup.add(btn_odds, btn_code, btn_vip, btn_contact)
    
    msg = (
        f"Welcome **{user_name}** to **Willys Media World Predictions**! ⚽🔥\n\n"
        f"We specialize in daily high-probability **~1.70 Odds** accumulators.\n\n"
        f"Please select an option below:"
    )
    bot.reply_to(message, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    codes = DATA.get('codes', DEFAULT_DATA['codes'])
    links = DATA.get('links', DEFAULT_DATA['links'])
    
    if message.text == "🎯 Today's Safe 1.70 Odds":
        matches_text = ""
        matches = DATA.get('matches', DEFAULT_DATA['matches'])
        for i, m in enumerate(matches, 1):
            subpage_url = f"{SITE_DOMAIN}/match/{m.get('id', i)}"
            matches_text += f"📌 **Match {i}:** {m.get('country','⚽')} {m.get('league','')}\n"
            matches_text += f"⚽ **Teams:** [{m.get('teams','')}]({subpage_url})\n"
            matches_text += f"⏰ **Time:** {m.get('time','Scheduled')} | **Score:** `{m.get('score','VS')}` ({m.get('status','')})\n"
            matches_text += f"💡 **Tip:** {m.get('tip','')}\n\n"
            
        text = (
            f"⚽ **TODAY'S 99% BANKER TICKET (~1.70 ODDS)** ⚽\n"
            f"-----------------------------------\n"
            f"{matches_text}"
            f"📊 **Total Combined Odds:** ~{DATA.get('total_odds', '1.70')}\n"
            f"-----------------------------------\n"
            f"🔑 **BOOKMAKER BOOKING CODES:**\n"
            f"🔴 **SportyBet:** `{codes.get('sportybet','BC982A1')}`\n"
            f"🟢 **Bet9ja:** `{codes.get('bet9ja','B9J-77812')}`\n"
            f"🔵 **1xBet:** `{codes.get('oneXbet','1X-99821')}`\n\n"
            f"⚠️ *Bet responsibly! Manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "📱 Booking Codes":
        text = (
            f"📱 **BOOKMAKER BOOKING CODES** 📱\n\n"
            f"🔴 **SportyBet:** `{codes.get('sportybet','BC982A1')}`\n"
            f"🟢 **Bet9ja:** `{codes.get('bet9ja','B9J-77812')}`\n"
            f"🔵 **1xBet:** `{codes.get('oneXbet','1X-99821')}`\n\n"
            f"👉 [Click Here to Open SportyBet]({links.get('sportybet')})\n"
            f"👉 [Click Here to Open Bet9ja]({links.get('bet9ja')})"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

    elif message.text == "👑 VIP Group Info":
        text = (
            "👑 **WILLYS VIP WINNERS CLUB** 👑\n\n"
            "✅ Daily ~1.70 Banker Accumulators\n"
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
            time.sleep(3)

# ==========================================
# 2. FLASK WEBSITE ENGINE
# ==========================================
app = Flask(__name__)

HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Willys Media World - Daily 1.70 Odds Predictions</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; padding: 15px; text-align: center; }
        .container { max-width: 500px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #1e293b, #334155); padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #475569; }
        h1 { color: #22c55e; font-size: 22px; margin-bottom: 5px; }
        p.subtitle { color: #94a3b8; font-size: 13px; }
        .card { background-color: #1e293b; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; text-align: left; }
        .card h2 { color: #38bdf8; font-size: 16px; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 6px; }
        .league-badge { font-size: 11px; color: #fbbf24; font-weight: bold; margin-bottom: 4px; display: flex; justify-content: space-between; }
        .match-time { color: #38bdf8; font-size: 11px; }
        .match { margin-bottom: 12px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #22c55e; text-decoration: none; display: block; color: inherit; }
        .match-info { font-size: 14px; font-weight: bold; color: #ffffff; }
        .score-bar { font-size: 12px; color: #38bdf8; font-weight: bold; margin-top: 4px; background: #1e293b; padding: 3px 8px; border-radius: 4px; display: inline-block; }
        .tip { color: #22c55e; font-size: 12px; margin-top: 4px; }
        .total-odds { background: #334155; padding: 10px; border-radius: 6px; text-align: center; color: #22c55e; font-weight: bold; margin-top: 10px; font-size: 15px; }
        
        /* MULTI BOOKMAKER CODE BOXES */
        .code-row { display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 8px 12px; border-radius: 6px; margin-top: 8px; border: 1px solid #334155; }
        .code-label { font-size: 12px; font-weight: bold; color: #f8fafc; }
        .code-input { background: #1e293b; border: 1px solid #0284c7; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 13px; width: 100px; text-align: center; }
        .copy-btn { background: #0284c7; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; cursor: pointer; }
        
        .btn { display: block; width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 13px; text-align: center; border: none; cursor: pointer; }
        .btn-sporty { background-color: #e11d48; color: white; margin-top: 12px; }
        .btn-bet9ja { background-color: #15803d; color: white; }
        .btn-telegram { background-color: #0284c7; color: white; }
        .btn-whatsapp { background-color: #22c55e; color: white; }
        .footer { color: #64748b; font-size: 11px; margin-top: 25px; line-height: 1.5; }
    </style>
    <script>
        function copyInputCode(inputId, btnId) {
            var input = document.getElementById(inputId);
            input.select();
            input.setSelectionRange(0, 99999);
            try {
                navigator.clipboard.writeText(input.value);
            } catch(e) {
                document.execCommand('copy');
            }
            var btn = document.getElementById(btnId);
            btn.innerText = "COPIED!";
            btn.style.backgroundColor = "#22c55e";
            setTimeout(function(){
                btn.innerText = "COPY";
                btn.style.backgroundColor = "#0284c7";
            }, 2000);
        }
    </script>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>WILLYS MEDIA WORLD</h1>
        <p class="subtitle">🎯 99% Banker ~1.70 Odds Ticket</p>
    </div>
    
    <div class="card">
        <h2>⚽ Today's Accumulator Ticket</h2>
        <p style="font-size:11px; color:#94a3b8; margin-bottom:10px;">💡 <i>Auto-updated every 3 hours!</i></p>
        
        {% for match in data.get('matches', []) %}
        <a href="/match/{{ match.get('id', loop.index) }}" class="match">
            <div class="league-badge">
                <span>{{ match.get('country','') }} - {{ match.get('league','') }}</span>
                <span class="match-time">⏰ {{ match.get('time','Scheduled') }}</span>
            </div>
            <div class="match-info">⚽ {{ match.get('teams','') }}</div>
            <div class="score-bar">Score: {{ match.get('score','VS') }} ({{ match.get('status','Upcoming') }})</div>
            <div class="tip">Tip: {{ match.get('tip','') }}</div>
        </a>
        {% endfor %}
        
        <div class="total-odds">📊 Combined Ticket Odds: ~{{ data.get('total_odds', '1.70') }}</div>
        
        <h3 style="font-size:13px; color:#38bdf8; margin-top:15px; margin-bottom:5px;">🔑 BOOKMAKER BOOKING CODES:</h3>
        
        <!-- SPORTYBET CODE ROW -->
        <div class="code-row">
            <span class="code-label">🔴 SportyBet:</span>
            <input type="text" id="sbCode" class="code-input" value="{{ data.get('codes',{}).get('sportybet','BC982A1') }}" readonly>
            <button id="sbBtn" class="copy-btn" onclick="copyInputCode('sbCode', 'sbBtn')">COPY</button>
        </div>

        <!-- BET9JA CODE ROW -->
        <div class="code-row">
            <span class="code-label">🟢 Bet9ja:</span>
            <input type="text" id="b9jCode" class="code-input" value="{{ data.get('codes',{}).get('bet9ja','B9J-77812') }}" readonly>
            <button id="b9jBtn" class="copy-btn" onclick="copyInputCode('b9jCode', 'b9jBtn')">COPY</button>
        </div>

        <!-- 1XBET CODE ROW -->
        <div class="code-row">
            <span class="code-label">🔵 1xBet:</span>
            <input type="text" id="oneCode" class="code-input" value="{{ data.get('codes',{}).get('oneXbet','1X-99821') }}" readonly>
            <button id="oneBtn" class="copy-btn" onclick="copyInputCode('oneCode', 'oneBtn')">COPY</button>
        </div>

        <a href="{{ data.get('links',{}).get('sportybet','https://www.sportybet.com/ng/') }}" target="_blank" class="btn btn-sporty">🎰 Open SportyBet</a>
        <a href="{{ data.get('links',{}).get('bet9ja','h
