import threading
import telebot
from telebot import types
from flask import Flask, render_template_string
import os

# ==========================================
# 1. TELEGRAM BOT ENGINE
# ==========================================
BOT_TOKEN = "8700629519:AAFUXLN7K7XrS0DTMQ_sULOnlAvLIHc-SrU"
bot = telebot.TeleBot(BOT_TOKEN)

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
            "⚽ **TODAY'S SAFE 1.50 - 2.00 ODDS** ⚽\n"
            "-----------------------------------\n"
            "📌 **Match 1:** Real Madrid vs Getafe\n"
            "💡 **Tip:** Real Madrid Win or Draw (1X) @ 1.25\n\n"
            "📌 **Match 2:** Arsenal vs Everton\n"
            "💡 **Tip:** Over 1.5 Goals @ 1.30\n\n"
            "📊 **Total Odds:** ~1.62\n"
            "-----------------------------------\n"
            "⚠️ *Bet responsibly! Always manage your stake.*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "📱 SportyBet Booking Code":
        text = (
            "📱 **SPORTYBET BOOKING CODE** 📱\n\n"
            "🔑 **Code:** `BC982A1` (Tap to copy)\n"
            "🌐 **Platform:** SportyBet.com\n\n"
            "👉 Register on SportyBet using our official link to get 100% deposit bonus!"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "👑 VIP Group Info":
        text = (
            "👑 **WILLYS VIP WINNERS CLUB** 👑\n\n"
            "✅ Daily 1.50 - 2.00 Banker Games\n"
            "✅ 4-Day Rollover Strategy (N5,000 to N50,000)\n"
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
        .odd { background: #22c55e; color: #000; font-weight: bold; padding: 3px 7px; border-radius: 4px; font-size: 12px; }
        .code-box { background: #0284c7; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-top: 12px; font-weight: bold; font-size: 14px; }
        .code-box span { background: #0f172a; padding: 4px 10px; border-radius: 4px; font-family: monospace; letter-spacing: 2px; color: #38bdf8; }
        .btn { display: block; width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; }
        .btn-telegram { background-color: #0284c7; color: white; }
        .btn-whatsapp { background-color: #22c55e; color: white; }
        .footer { color: #64748b; font-size: 11px; margin-top: 25px; line-height: 1.5; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>WILLYS MEDIA WORLD</h1>
        <p class="subtitle">🎯 Daily High-Probability 1.50 - 2.00 Safe Odds</p>
    </div>
    <div class="card">
        <h2>⚽ Today's Safe 2-Odds</h2>
        <div class="match">
            <div>
                <div class="match-info">Real Madrid vs Getafe</div>
                <div class="tip">Tip: Home Win or Draw (1X)</div>
            </div>
            <div class="odd">@ 1.25</div>
        </div>
        <div class="match">
            <div>
                <div class="match-info">Arsenal vs Everton</div>
                <div class="tip">Tip: Over 1.5 Goals</div>
            </div>
            <div class="odd">@ 1.30</div>
        </div>
        <div class="code-box">SportyBet Code: <span>BC982A1</span></div>
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
    return render_template_string(HTML_TEMPLATE)

# Start Bot Thread & Web Server
if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
    