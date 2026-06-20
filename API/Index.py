from flask import Flask, request, render_template_string
import sqlite3
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

app = Flask(__name__)

# ===== PRICING SETTINGS =====
ECOCASH_NUMBER = "0780554072"
ADMIN_NUMBERS = ["0780554072", "0710990619"]
PRICE_TIERS = {1: 10, 2: 50, 3: 100, 4: 99999}
DAILY_LIMIT = 5
FREE_DAYS = 30
# ============================

TZ = ZoneInfo("Africa/Harare")
LAUNCH_DATE = datetime(2026, 6, 21, 12, 0, 0, tzinfo=TZ)
FREE_END_DATE = LAUNCH_DATE + timedelta(days=FREE_DAYS)
DB_FILE = "/tmp/kingsmoke_users.db"

FREE_ROASTS = [
"Wakafanana neWiFi yeTelOne - unobatika but haushande 💨👑",
"Face yako yakaita seZESA load shedding - unpredictable 💨👑",
"Unonhuwirira secombi yeMbare mangwanani 💨👑",
"Brain yako ine 2G network - slow but trying 💨👑",
"Wakavakwa neleftovers dze creation 💨👑",
"Uri opposite ye glow up - unonzi dim down 💨👑",
"Confidence yako > skill yako. Delulu level: Vegeta 💨👑",
"Kana stupid iri sport, unenge uri world champion 💨👑",
"Wakafanana neEcoCash kana pasina network - useless 💨👑",
"Looks dzako dzakaita sebudget yeZim - depreciating daily 💨👑",
"Vibe yako = Monday morning without tea 💨👑",
"Wakafanana nebond note - no one wants you but uri legal 💨👑",
"Personality yako = plain sadza no relish 💨👑",
"Unofamba sewa lost mu Avondale 💨👑",
"Jokes dzako = ZBC news - boring but consistent 💨👑"
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_credits (number TEXT PRIMARY KEY, credits_left INTEGER, unlimited_until TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (user_id TEXT, date TEXT, count INTEGER, PRIMARY KEY (user_id, date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, amount INTEGER, date TEXT)''')
    conn.commit()
    conn.close()

def add_credits(number, amount_paid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if amount_paid == 4:
        expiry = datetime.now(TZ) + timedelta(days=30)
        c.execute("REPLACE INTO user_credits VALUES (?,?,?)", (number, 99999, expiry.strftime("%Y-%m-%d %H:%M:%S")))
    else:
        credits_to_add = PRICE_TIERS.get(amount_paid, 0)
        c.execute("INSERT OR IGNORE INTO user_credits VALUES (?, 0, NULL)", (number,))
        c.execute("UPDATE user_credits SET credits_left = credits_left +? WHERE number =?", (credits_to_add, number))
    c.execute("INSERT INTO payments (number, amount, date) VALUES (?,?,?)", (number, amount_paid, datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_user_credits(number):
    if number in ADMIN_NUMBERS: return 99999, None
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT credits_left, unlimited_until FROM user_credits WHERE number =?", (number,))
    result = c.fetchone()
    conn.close()
    if not result: return 0, None
    credits, unlimited_until = result
    if unlimited_until:
        expiry = datetime.strptime(unlimited_until, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
        if datetime.now(TZ) <= expiry: return 99999, expiry
    return credits, None

def use_one_credit(number):
    credits, unlimited = get_user_credits(number)
    if unlimited: return True
    if credits > 0:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE user_credits SET credits_left = credits_left - 1 WHERE number =?", (number,))
        conn.commit()
        conn.close()
        return True
    return False

def check_free_daily_limit(user_id):
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT count FROM daily_usage WHERE user_id=? AND date=?", (user_id, today))
    result = c.fetchone()
    count = result[0] if result else 0
    conn.close()
    return count < DAILY_LIMIT

def increment_free_usage(user_id):
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO daily_usage VALUES (?,?, COALESCE((SELECT count FROM daily_usage WHERE user_id=? AND date=?), 0) + 1)", (user_id, today, user_id, today))
    conn.commit()
    conn.close()

init_db()

HTML = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>KING SMOKE</title>
<style>
body{font-family:sans-serif;background:#0a0a0a;color:#fff;margin:0;padding:10px;text-align:center}
#chat{height:60vh;overflow-y:auto;border:2px solid #ff6b35;border-radius:10px;padding:10px;margin:10px 0;text-align:left;background:#1a1a1a}
.msg{margin:8px 0;padding:8px;border-radius:8px}.user{background:#ff6b35;color:#000;text-align:right}.bot{background:#333}
input{width:65%;padding:12px;border:none;border-radius:20px;background:#333;color:#fff}
button{padding:12px 20px;border:none;border-radius:20px;background:#ff6b35;color:#000;font-weight:bold;cursor:pointer}
h1{color:#ff6b35;text-shadow:0 0 10px #ff6b35}
</style></head><body>
<h1>👑 KING SMOKE 💨👑</h1>
<p>Free {{free_days}} days | Ecocash: {{ecocash}}</p>
<div id="chat"></div>
<input id="inp" placeholder="Type message..." onkeydown="if(event.key==='Enter')send()">
<button onclick="send()">ROAST 💨</button>
<script>
function add(t,c){let d=document.getElementById('chat');d.innerHTML+=`<div class="msg ${c}">${t}</div>`;d.scrollTop=d.scrollHeight;}
async function send(){let i=document.getElementById('inp'),m=i.value.trim();if(!m)return;add(m,'user');i.value='';let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg:m})});let d=await r.json();add(d.reply,'bot');}
window.onload=()=>add("Ndini KING SMOKE 💨👑 Type anything ndingokuroast. {{daily}} free/day.","bot");
</script></body></html>
'''

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def home(path):
    return render_template_string(HTML, free_days=FREE_DAYS, ecocash=ECOCASH_NUMBER, daily=DAILY_LIMIT)

@app.route('/api/chat', methods=['POST'])
def chat():
    today = datetime.now(TZ)
    data = request.json
    msg = data['msg'].strip()
    user_id = request.headers.get('X-Forwarded-For', request.remote_addr)

    if msg.upper() == "ADMIN":
        return {"reply": f"👑 ADMIN\nADMIN ADD 0782123456 $2\nPay to: {ECOCASH_NUMBER}"}

    if msg.upper().startswith("ADMIN ADD"):
        parts = msg.split()
        if len(parts) == 4 and user_id in ADMIN_NUMBERS:
            amount = int(parts[3].replace("$", ""))
            if amount in PRICE_TIERS:
                add_credits(parts[2], amount)
                pack = "Unlimited 30 days" if amount == 4 else f"{PRICE_TIERS[amount]} msgs"
                return {"reply": f"✅ Added ${amount} to {parts[2]} = {pack} 💨👑"}

    credits, unlimited = get_user_credits(user_id)
    paid_msg = False
    if unlimited or credits > 0:
        if use_one_credit(user_id): paid_msg = True

    if not paid_msg:
        if today <= FREE_END_DATE and check_free_daily_limit(user_id):
            increment_free_usage(user_id)
        else:
            return {"reply": f"🔒 No credits\n💰 TOP UP:\n$1={PRICE_TIERS[1]} | $2={PRICE_TIERS[2]} | $3={PRICE_TIERS[3]} | $4=Unlimited\nPay {ECOCASH_NUMBER} 💨👑"}

    roast = random.choice(FREE_ROASTS)
    credits_left, unlimited = get_user_credits(user_id)
    if unlimited: status = f"👑 UNLIMITED"
    elif credits_left > 0: status = f"💰 Credits: {credits_left}"
    else:
        days_left = (FREE_END_DATE - today).days if today <= FREE_END_DATE else 0
        status = f"💨 FREE: {DAILY_LIMIT}/day | {days_left} days left"

    return {"reply": f"{roast}\n\n{status} 💨👑"}
