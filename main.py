#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    👑 ROYAL MAIL STORE - ULTIMATE BOT                      ║
║              VPN • Proxy • Mail • Auto Delivery • Admin Panel              ║
║                    Replit • Render • Railway • Termux                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, uuid, asyncio, logging, threading
from datetime import datetime, timedelta
from pathlib import Path

# ═══════════════ AUTO INSTALL ═══════════════
def install_packages():
    needed = []
    try:
        from flask import Flask
    except:
        needed.append("flask==3.0.0")
    try:
        from telegram import Update
    except:
        needed.append("python-telegram-bot==20.7")
    try:
        from waitress import serve
    except:
        needed.append("waitress==3.0.0")
    
    if needed:
        print(f"📦 Installing: {' '.join(needed)}")
        for pkg in needed:
            os.system(f"{sys.executable} -m pip install --quiet {pkg}")
        print("✅ Done! Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

install_packages()

from flask import Flask, jsonify
from waitress import serve as wsgi_serve
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Defaults
from telegram.constants import ParseMode, ChatMemberStatus

# ═══════════════ CONFIG ═══════════════
class C:
    TOKEN = os.getenv("BOT_TOKEN", "8959981246:AAGBXTogxrrFEg08-seUXv80N6bmLI8ujq8")
    ADMIN = [int(x.strip()) for x in os.getenv("ADMIN_ID", "5507924915").split(",") if x.strip()]
    CHANNEL = os.getenv("CHANNEL_USERNAME", "@RoyalMarketingZone")
    CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/RoyalMarketingZone")
    BKASH = os.getenv("BKASH_NUMBER", "01301027106")
    NAGAD = os.getenv("NAGAD_NUMBER", "01301027106")
    ROCKET = os.getenv("ROCKET_NUMBER", "01301027106")
    SUPPORT = os.getenv("SUPPORT_USERNAME", "@villen45")
    PORT = int(os.getenv("PORT", "8080"))
    DIR = Path("data")
    MIN_DEP = int(os.getenv("MIN_DEPOSIT", "10"))
    MAX_DEP = int(os.getenv("MAX_DEPOSIT", "100"))
    START = time.time()

C.DIR.mkdir(exist_ok=True)

# ═══════════════ LOGGING ═══════════════
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger("Bot")
logging.getLogger("telegram").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("waitress").setLevel(logging.ERROR)

# ═══════════════ DATABASE ═══════════════
class DB:
    def __init__(self):
        self.d = C.DIR
        for n in ['users', 'products', 'stock', 'deposits']:
            f = self.d / f"{n}.json"
            if not f.exists():
                f.write_text('[]')

    def r(self, n):
        try: return json.loads((self.d / f"{n}.json").read_text(encoding='utf-8'))
        except: return []

    def w(self, n, d):
        (self.d / f"{n}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

    # ── USERS ──
    def user(self, tid):
        for u in self.r('users'):
            if u.get('telegramId') == tid: return u.copy()
        return None

    def save_user(self, d):
        users = self.r('users')
        idx = next((i for i, u in enumerate(users) if u.get('telegramId') == d.get('telegramId')), None)
        now = datetime.now().isoformat()
        if idx is not None:
            users[idx].update(d)
            users[idx]['lastActive'] = now
        else:
            users.append({
                'telegramId': d['telegramId'], 'username': d.get('username', ''),
                'firstName': d.get('firstName', 'User'), 'balance': 0.0,
                'totalSpent': 0.0, 'totalDeposited': 0.0, 'totalPurchases': 0,
                'isBanned': False, 'joinedAt': now, 'lastActive': now
            })
        self.w('users', users)

    def all_users(self): return self.r('users')

    def add_bal(self, tid, amt):
        users = self.r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['balance'] = round(u['balance'] + amt, 2)
                if amt > 0: u['totalDeposited'] = round(u.get('totalDeposited', 0) + amt, 2)
                self.w('users', users)
                return u
        return None

    def pay(self, tid, amt):
        users = self.r('users')
        for u in users:
            if u['telegramId'] == tid and u['balance'] >= amt:
                u['balance'] = round(u['balance'] - amt, 2)
                u['totalSpent'] = round(u.get('totalSpent', 0) + amt, 2)
                u['totalPurchases'] = u.get('totalPurchases', 0) + 1
                self.w('users', users)
                return True
        return False

    def ban(self, tid):
        users = self.r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['isBanned'] = not u.get('isBanned', False)
                self.w('users', users)
                return u
        return None

    # ── PRODUCTS ──
    def prods(self, pt=None):
        p = self.r('products')
        if pt: return [x for x in p if x.get('type') == pt and x.get('active', True)]
        return [x for x in p if x.get('active', True)]

    def prod(self, pid):
        for p in self.r('products'):
            if p.get('id') == pid: return p.copy()
        return None

    def add_prod(self, d):
        p = self.r('products')
        d['id'] = str(int(time.time() * 1000))
        d['active'] = True
        d['createdAt'] = datetime.now().isoformat()
        p.append(d)
        self.w('products', p)

    # ── STOCK ──
    def stock_avail(self, pt, price=None):
        for s in self.r('stock'):
            if s.get('productType') == pt and not s.get('isSold'):
                if price is None or s.get('price') == price:
                    return s.copy()
        return None

    def add_stock(self, d):
        s = self.r('stock')
        d['id'] = str(int(time.time() * 1000))
        d['isSold'] = False
        d['addedAt'] = datetime.now().isoformat()
        s.append(d)
        self.w('stock', s)

    def sell(self, sid, buyer):
        s = self.r('stock')
        for x in s:
            if x['id'] == sid:
                x['isSold'] = True
                x['soldTo'] = buyer
                x['soldAt'] = datetime.now().isoformat()
                self.w('stock', s)
                return x
        return None

    def stock_stats(self):
        s = self.r('stock')
        return {'total': len(s), 'avail': len([x for x in s if not x.get('isSold')]), 'sold': len([x for x in s if x.get('isSold')])}

    # ── DEPOSITS ──
    def dep_create(self, d):
        deps = self.r('deposits')
        d['id'] = str(int(time.time() * 1000))
        d['status'] = 'pending'
        d['createdAt'] = datetime.now().isoformat()
        deps.append(d)
        self.w('deposits', deps)
        return d

    def dep_pending(self):
        return [d for d in self.r('deposits') if d['status'] == 'pending']

    def dep_update(self, did, status, admin):
        deps = self.r('deposits')
        for d in deps:
            if d['id'] == did:
                d['status'] = status
                d['reviewedBy'] = admin
                d['reviewedAt'] = datetime.now().isoformat()
                if status == 'approved':
                    self.add_bal(d['telegramId'], d['amount'])
                self.w('deposits', deps)
                return d
        return None

    # ── STATS ──
    def stats(self):
        u = self.r('users')
        d = self.r('deposits')
        s = self.r('stock')
        a = [x for x in d if x['status'] == 'approved']
        return {
            'users': len(u), 'revenue': sum(x['amount'] for x in a),
            'pending': len([x for x in d if x['status'] == 'pending']),
            'stock': len([x for x in s if not x['isSold']]),
            'sold': len([x for x in s if x['isSold']]),
            'uptime': int(time.time() - C.START)
        }

db = DB()

# ═══════════════ FLASK ═══════════════
app = Flask(__name__)

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ROYAL MAIL STORE</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{background:linear-gradient(135deg,#0a0a0a,#1a1a2e);color:#ffd700;font-family:system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{text-align:center;padding:40px;background:rgba(0,0,0,.6);border:2px solid #ffd700;border-radius:20px;max-width:480px;width:90%}
h1{font-size:1.8em;margin:10px 0}.green{color:#0f0;font-size:1.2em;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:15px 0}
.card{padding:12px;background:rgba(255,215,0,.1);border:1px solid #ffd700;border-radius:8px}
.card .num{font-size:1.3em;font-weight:bold}.card .lbl{font-size:.75em;color:#aaa}
p{color:#aaa;font-size:.8em;margin-top:10px}a{color:#ffd700;text-decoration:none}
</style></head><body><div class="box"><div style="font-size:3em">👑</div><h1>ROYAL MAIL STORE</h1><div class="green">🟢 Bot is Running</div>
<div class="grid"><div class="card"><div class="num">{users}</div><div class="lbl">Users</div></div>
<div class="card"><div class="num">{revenue} TK</div><div class="lbl">Revenue</div></div>
<div class="card"><div class="num">{stock}</div><div class="lbl">In Stock</div></div>
<div class="card"><div class="num">{pending}</div><div class="lbl">Pending</div></div></div>
<p>Uptime: {uptime} | <a href="https://t.me/RoyalMarketingZone">Channel</a></p></div></body></html>"""

@app.route('/')
def home():
    s = db.stats()
    h, m = divmod(s['uptime'], 3600); m //= 60
    return HTML.format(users=s['users'], revenue=f"{s['revenue']:.0f}", stock=s['stock'], pending=s['pending'], uptime=f"{h}h {m}m")

@app.route('/health')
def health():
    return jsonify({"status":"ok","timestamp":datetime.now().isoformat()})

@app.route('/ping')
def ping():
    return "pong"

# ═══════════════ KEYBOARDS ═══════════════
def main_kb(uid):
    admin = uid in C.ADMIN
    rows = [
        [KeyboardButton("🔐 VPN"), KeyboardButton("🌐 Proxy")],
        [KeyboardButton("📧 Mail"), KeyboardButton("💰 Deposit")],
        [KeyboardButton("💳 Balance"), KeyboardButton("❓ Help")]
    ]
    if admin:
        rows.append([KeyboardButton("👑 Admin")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Product"), KeyboardButton("📥 Stock")],
        [KeyboardButton("👥 Users"), KeyboardButton("💰 Pending")],
        [KeyboardButton("📊 Stats"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("🚫 Ban/Unban"), KeyboardButton("🔙 Main")]
    ], resize_keyboard=True)

# ═══════════════ FORCE JOIN ═══════════════
async def check_join(update, context):
    uid = update.effective_user.id
    if uid in C.ADMIN:
        return True
    try:
        member = await context.bot.get_chat_member(C.CHANNEL, uid)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=C.CHANNEL_URL)],
                [InlineKeyboardButton("✅ I Joined", callback_data="join_ok")]
            ])
            msg = update.message or (update.callback_query.message if update.callback_query else None)
            if msg:
                await msg.reply_text(
                    f"⚠️ *You must join our channel!*\n\n"
                    f"📢 Channel: {C.CHANNEL}\n"
                    f"🔗 {C.CHANNEL_URL}\n\n"
                    f"1️⃣ Click 'Join Channel'\n"
                    f"2️⃣ Join the channel\n"
                    f"3️⃣ Click 'I Joined'",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb,
                    disable_web_page_preview=True
                )
            return False
        return True
    except Exception as e:
        log.error(f"Join check: {e}")
        return True

# ═══════════════ START ═══════════════
async def start(update, context):
    if not await check_join(update, context):
        return
    
    u = update.effective_user
    db.save_user({'telegramId': u.id, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    user = db.user(u.id)
    
    msg = f"""
👑 *WELCOME TO ROYAL MAIL STORE!*

╔════════════════════════════╗
║   🔐 Premium VPN Accounts  ║
║   🌐 Fast Proxy Servers    ║
║   📧 Verified Mail Accounts║
╚════════════════════════════╝

💰 *Your Balance:* `{user['balance']:.0f} TK`
💳 *Min Deposit:* `{C.MIN_DEP} TK`
💳 *Max Deposit:* `{C.MAX_DEP} TK`

📢 *Channel:* {C.CHANNEL}
📞 *Support:* {C.SUPPORT}

👇 *Select an option:*
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(u.id))

async def join_ok(update, context):
    q = update.callback_query
    await q.answer()
    if await check_join(update, context):
        await q.edit_message_text("✅ *Verified! Welcome!*", parse_mode=ParseMode.MARKDOWN)
        await start(update, context)

# ═══════════════ MAIN HANDLER ═══════════════
async def handle_msg(update, context):
    if not await check_join(update, context):
        return
    
    uid = update.effective_user.id
    txt = update.message.text.strip()
    u = update.effective_user
    
    db.save_user({'telegramId': uid, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    
    user = db.user(uid)
    if user and user.get('isBanned'):
        await update.message.reply_text(f"🚫 *You are banned!*\n\nContact support: {C.SUPPORT}", parse_mode=ParseMode.MARKDOWN)
        return
    
    state = context.user_data.get('state')
    if state:
        return await handle_state(update, context)
    
    if txt == "🔐 VPN":
        await show_products(update, context, "vpn")
    elif txt == "🌐 Proxy":
        await show_products(update, context, "proxy")
    elif txt == "📧 Mail":
        await show_products(update, context, "mail")
    elif txt == "💰 Deposit":
        await deposit_start(update, context)
    elif txt == "💳 Balance":
        await show_balance(update, context)
    elif txt == "❓ Help":
        await show_help(update, context)
    elif txt == "👑 Admin" and uid in C.ADMIN:
        await admin_panel(update, context)
    elif txt == "🔙 Main":
        await update.message.reply_text("🏠 Main Menu", reply_markup=main_kb(uid))
    elif uid in C.ADMIN:
        await admin_msg(update, context)
    else:
        await update.message.reply_text("👇 Use buttons below:", reply_markup=main_kb(uid))

# ═══════════════ PRODUCTS ═══════════════
async def show_products(update, context, cat):
    prods = db.prods(cat)
    emoji = {"vpn": "🔐", "proxy": "🌐", "mail": "📧"}.get(cat, "📦")
    
    if not prods:
        await update.message.reply_text(f"{emoji} *No {cat.upper()} products yet!*\n\nAdmin will add soon.", parse_mode=ParseMode.MARKDOWN)
        return
    
    kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']:.0f} TK", callback_data=f"buy_{p['id']}")] for p in prods]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    
    await update.message.reply_text(
        f"{emoji} *{cat.upper()} Products*\n\n📦 {len(prods)} products available\n\n👇 Select to buy:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def buy_prod(update, context):
    q = update.callback_query
    await q.answer()
    
    if q.data == "back_main":
        await q.edit_message_text("🏠")
        await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))
        return
    
    uid = update.effective_user.id
    pid = q.data.replace("buy_", "")
    product = db.prod(pid)
    user = db.user(uid)
    
    if not product:
        return await q.edit_message_text("❌ Product not found!")
    
    if user['balance'] < product['price']:
        return await q.edit_message_text(
            f"❌ *Insufficient Balance!*\n\n💰 Price: `{product['price']:.0f} TK`\n💳 Balance: `{user['balance']:.0f} TK`\n📥 Need: `{product['price'] - user['balance']:.0f} TK` more\n\nUse 💰 Deposit button!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    stock = db.stock_avail(product['type'], product['price'])
    if not stock:
        return await q.edit_message_text("❌ *Out of stock!*", parse_mode=ParseMode.MARKDOWN)
    
    db.pay(uid, product['price'])
    db.sell(stock['id'], uid)
    bal = db.user(uid)['balance']
    
    msg = f"✅ *Purchase Successful!*\n\n📦 *{product['name']}*\n💰 Price: `{product['price']:.0f} TK`\n💳 Balance: `{bal:.0f} TK`\n\n━━━━━━━━━━━━━━━━━━\n\n"
    d = stock['data']
    
    if product['type'] == 'vpn':
        msg += f"📧 *Email:* `{d.get('email','N/A')}`\n🔐 *Password:* `{d.get('password','N/A')}`\n📅 *Expire:* {d.get('expireDate','N/A')}\n"
    elif product['type'] == 'proxy':
        msg += f"🌐 *Host:* `{d.get('host','N/A')}`\n🔌 *Port:* `{d.get('port','N/A')}`\n👤 *User:* `{d.get('username','N/A')}`\n🔑 *Pass:* `{d.get('password','N/A')}`\n"
    elif product['type'] == 'mail':
        msg += f"📧 *Email:* `{d.get('email','N/A')}`\n🔐 *Password:* `{d.get('password','N/A')}`\n🔑 *Recovery:* `{d.get('recovery','N/A')}`\n"
    
    msg += f"\n📝 Order ID: `{stock['id'][:8]}`\n🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n🙏 *Thank you!*"
    
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    for aid in C.ADMIN:
        try:
            await context.bot.send_message(aid, f"📦 *Sale!*\n👤 {user.get('firstName','?')}\n📦 {product['name']}\n💰 {product['price']:.0f} TK", parse_mode=ParseMode.MARKDOWN)
        except: pass

# ═══════════════ DEPOSIT ═══════════════

# Step 1: Choose payment method
async def deposit_start(update, context):
    context.user_data['state'] = 'deposit_method'
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 bKash", callback_data="dep_bkash"),
         InlineKeyboardButton("💳 Nagad", callback_data="dep_nagad")],
        [InlineKeyboardButton("🚀 Rocket", callback_data="dep_rocket")],
        [InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")]
    ])
    
    await update.message.reply_text(
        "💰 *Deposit Funds*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💳 bKash: `{C.BKASH}`\n"
        f"💳 Nagad: `{C.NAGAD}`\n"
        f"🚀 Rocket: `{C.ROCKET}`\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👇 *Choose payment method:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

# Step 2: Show number & ask amount
async def deposit_method_cb(update, context):
    q = update.callback_query
    await q.answer()
    
    if q.data == "dep_cancel":
        context.user_data.clear()
        await q.edit_message_text("❌ Cancelled")
        await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))
        return
    
    # Determine method and number
    method_map = {
        "dep_bkash": ("bKash", C.BKASH),
        "dep_nagad": ("Nagad", C.NAGAD),
        "dep_rocket": ("Rocket", C.ROCKET),
    }
    
    method, number = method_map.get(q.data, ("bKash", C.BKASH))
    
    context.user_data['dep_method'] = method
    context.user_data['dep_number'] = number
    context.user_data['state'] = 'deposit_amount'
    
    await q.edit_message_text(
        f"💳 *{method} Payment*\n\n"
        f"📱 *Send money to:*\n`{number}`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Step 1:* Send the amount\n"
        f"📝 *Step 2:* Get Transaction ID\n"
        f"📝 *Step 3:* Enter amount below\n\n"
        f"👇 *Reply with amount:*\n"
        f"Example: `50` or `100`\n\n"
        f"📥 Min: `{C.MIN_DEP} TK`\n"
        f"📤 Max: `{C.MAX_DEP} TK`\n\n"
        f"Send `cancel` to exit.",
        parse_mode=ParseMode.MARKDOWN
    )

# Step 3: Get amount
async def deposit_amount(update, context):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    if txt.lower() in ['cancel', '❌ cancel']:
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled", reply_markup=main_kb(uid))
        return
    
    try:
        amt = float(txt)
    except:
        await update.message.reply_text(
            "❌ *Invalid amount!*\nSend number only.\nExample: `50`\n\nTry again or `cancel`:",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if amt < C.MIN_DEP:
        await update.message.reply_text(f"❌ Minimum: `{C.MIN_DEP} TK`!\nTry again:", parse_mode=ParseMode.MARKDOWN)
        return
    if amt > C.MAX_DEP:
        await update.message.reply_text(f"❌ Maximum: `{C.MAX_DEP} TK`!\nTry again:", parse_mode=ParseMode.MARKDOWN)
        return
    
    context.user_data['dep_amount'] = amt
    context.user_data['state'] = 'deposit_txn'
    
    method = context.user_data.get('dep_method', 'bKash')
    
    await update.message.reply_text(
        f"💰 Amount: `{amt:.0f} TK`\n"
        f"💳 Method: {method}\n\n"
        f"🔢 *Now send Transaction ID:*\n"
        f"Example: `ABC123456` or `TXN789`\n\n"
        f"Send `cancel` to exit.",
        parse_mode=ParseMode.MARKDOWN
    )

# Step 4: Get TXN ID & submit
async def deposit_txn(update, context):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    if txt.lower() in ['cancel', '❌ cancel']:
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled", reply_markup=main_kb(uid))
        return
    
    txn = txt
    amt = context.user_data.get('dep_amount', 0)
    method = context.user_data.get('dep_method', 'bKash')
    number = context.user_data.get('dep_number', '')
    
    # Create deposit
    dep = db.dep_create({
        'telegramId': uid,
        'username': update.effective_user.username or '',
        'firstName': update.effective_user.first_name or 'User',
        'amount': amt,
        'transactionId': txn,
        'paymentMethod': method,
        'senderNumber': number
    })
    
    context.user_data.clear()
    
    # Notify admin
    for aid in C.ADMIN:
        try:
            await context.bot.send_message(aid,
                f"💰 *New Deposit Request!*\n\n"
                f"👤 User: {update.effective_user.first_name}\n"
                f"🆔 ID: `{uid}`\n"
                f"📱 @{update.effective_user.username or 'N/A'}\n"
                f"💰 Amount: `{amt:.0f} TK`\n"
                f"💳 Method: {method}\n"
                f"📱 Number: `{number}`\n"
                f"🔢 TXN ID: `{txn}`\n"
                f"🕐 {datetime.now().strftime('%d %b, %I:%M %p')}\n\n"
                f"Approve or Reject:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Approve", callback_data=f"app_{dep['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{dep['id']}")
                ]])
            )
        except: pass
    
    await update.message.reply_text(
        f"✅ *Deposit Submitted!*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount: `{amt:.0f} TK`\n"
        f"💳 Method: {method}\n"
        f"🔢 TXN ID: `{txn}`\n"
        f"⏳ Status: *Pending*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🕐 Wait for admin approval.\n"
        f"📞 Support: {C.SUPPORT}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(uid)
    )

# Deposit approval
async def dep_approve(update, context):
    q = update.callback_query
    await q.answer()
    
    if update.effective_user.id not in C.ADMIN:
        return
    
    data = q.data
    status = "approved" if data.startswith("app_") else "rejected"
    did = data.split("_", 1)[1]
    
    dep = db.dep_update(did, status, update.effective_user.id)
    
    if dep:
        try:
            emoji = "✅" if status == "approved" else "❌"
            txt = f"*{emoji} Deposit {status.title()}!*\n\n💰 Amount: `{dep['amount']:.0f} TK`"
            if status == "approved":
                txt += f"\n\n💳 Balance updated! Check with 💳 Balance button."
            await context.bot.send_message(dep['telegramId'], txt, parse_mode=ParseMode.MARKDOWN)
        except: pass
        await q.edit_message_text(f"{emoji} Deposit {status}!\n💰 {dep['amount']:.0f} TK")
    else:
        await q.edit_message_text("❌ Deposit not found!")

# ═══════════════ BALANCE ═══════════════
async def show_balance(update, context):
    uid = update.effective_user.id
    user = db.user(uid)
    if not user:
        await update.message.reply_text("❌ Use /start first!")
        return
    
    await update.message.reply_text(
        f"💳 *Your Balance*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balance: `{user['balance']:.0f} TK`\n"
        f"📊 Total Spent: `{user['totalSpent']:.0f} TK`\n"
        f"💎 Deposited: `{user['totalDeposited']:.0f} TK`\n"
        f"📦 Purchases: `{user['totalPurchases']}`\n"
        f"━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN
    )

# ═══════════════ HELP ═══════════════
async def show_help(update, context):
    msg = f"""
❓ *HELP & INFORMATION*

━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 *HOW TO USE:*

1️⃣ *Choose Product*
   • 🔐 VPN - Premium VPN accounts
   • 🌐 Proxy - Fast proxy servers
   • 📧 Mail - Verified mail accounts

2️⃣ *Buy Product*
   • Select product from list
   • Confirm purchase
   • Get instant delivery!

3️⃣ *Deposit Funds*
   • Click 💰 Deposit
   • Choose bKash / Nagad / Rocket
   • Send money to given number
   • Enter Amount
   • Enter Transaction ID
   • Wait for approval

━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 *PAYMENT NUMBERS:*

💳 *bKash:* `{C.BKASH}`
💳 *Nagad:* `{C.NAGAD}`
🚀 *Rocket:* `{C.ROCKET}`

📥 *Min Deposit:* `{C.MIN_DEP} TK`
📤 *Max Deposit:* `{C.MAX_DEP} TK`

━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 *CONTACT & SUPPORT:*

👤 *Admin:* {C.SUPPORT}
📢 *Channel:* {C.CHANNEL}
🔗 *Join:* {C.CHANNEL_URL}

━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ *RULES:*
• Must join our channel first
• No refund policy
• Minimum deposit {C.MIN_DEP} TK
• One purchase per stock item

💡 *TIPS:*
• Check balance before buying
• Save your purchase details
• Contact support for issues

━━━━━━━━━━━━━━━━━━━━━━━━━━

🙏 *Thank you for using*
👑 *ROYAL MAIL STORE!*
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ═══════════════ ADMIN ═══════════════
async def admin_panel(update, context):
    if update.effective_user.id not in C.ADMIN:
        return
    
    s = db.stats()
    h, m = divmod(s['uptime'], 3600); m //= 60
    
    await update.message.reply_text(
        f"👑 *Admin Panel*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: `{s['users']}`\n"
        f"💰 Revenue: `{s['revenue']:.0f} TK`\n"
        f"📦 Stock: `{s['stock']}` available\n"
        f"❌ Sold: `{s['sold']}`\n"
        f"⏳ Pending: `{s['pending']}`\n"
        f"🕐 Uptime: `{h}h {m}m`\n"
        f"━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_kb()
    )

async def admin_msg(update, context):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    
    if txt == "➕ Product":
        context.user_data['state'] = 'prod_type'
        await update.message.reply_text("📦 *Add Product*\n\nSend type: `vpn` `proxy` `mail`\n`cancel` to exit.", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "📥 Stock":
        context.user_data['state'] = 'stock_add'
        await update.message.reply_text("📥 *Add Stock*\n\nFormat: `email|password|expire|price`\nMultiple lines for bulk add.\n`done` to finish, `cancel` to exit.", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "👥 Users":
        users = db.all_users()
        msg = f"👥 *Users ({len(users)})*\n\n"
        for u in users[:25]:
            ban = "🚫" if u.get('isBanned') else "✅"
            msg += f"{ban} `{u.get('firstName','?')}` - {u['balance']:.0f} TK | ID: `{u['telegramId']}`\n"
        if len(users) > 25:
            msg += f"\n... +{len(users)-25} more"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "💰 Pending":
        deps = db.dep_pending()
        if not deps:
            await update.message.reply_text("✅ No pending deposits!")
            return
        for d in deps:
            await update.message.reply_text(
                f"💰 *Pending*\n\n👤 {d.get('firstName','?')} (`{d['telegramId']}`)\n💰 {d['amount']:.0f} TK\n💳 {d.get('paymentMethod','?')}\n🔢 TXN: `{d['transactionId']}`\n🕐 {d.get('createdAt','')[:19]}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Approve", callback_data=f"app_{d['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{d['id']}")
                ]])
            )
    
    elif txt == "📊 Stats":
        s = db.stats()
        h, m = divmod(s['uptime'], 3600); m //= 60
        await update.message.reply_text(f"📊 *Statistics*\n\n👥 Users: {s['users']}\n💰 Revenue: {s['revenue']:.0f} TK\n📦 Stock: {s['stock']}\n❌ Sold: {s['sold']}\n⏳ Pending: {s['pending']}\n🕐 Uptime: {h}h {m}m", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "📢 Broadcast":
        context.user_data['state'] = 'broadcast'
        await update.message.reply_text("📢 *Broadcast*\n\nSend message to all users.\n`cancel` to exit.", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "🚫 Ban/Unban":
        context.user_data['state'] = 'ban_user'
        await update.message.reply_text("🚫 Send User ID to ban/unban:\n`cancel` to exit.", parse_mode=ParseMode.MARKDOWN)

# ═══════════════ STATE HANDLER ═══════════════
async def handle_state(update, context):
    state = context.user_data.get('state')
    txt = update.message.text.strip()
    uid = update.effective_user.id
    
    if txt.lower() in ['cancel', '❌ cancel']:
        context.user_data.clear()
        kb = admin_kb() if uid in C.ADMIN else main_kb(uid)
        await update.message.reply_text("❌ Cancelled", reply_markup=kb)
        return
    
    # ── DEPOSIT FLOW ──
    if state == 'deposit_amount':
        await deposit_amount(update, context)
    
    elif state == 'deposit_txn':
        await deposit_txn(update, context)
    
    # ── PRODUCT ADD ──
    elif state == 'prod_type':
        if txt.lower() not in ['vpn', 'proxy', 'mail']:
            await update.message.reply_text("❌ Send: vpn, proxy, or mail")
            return
        context.user_data['ptype'] = txt.lower()
        context.user_data['state'] = 'prod_name'
        await update.message.reply_text("📝 Product name:")
    
    elif state == 'prod_name':
        context.user_data['pname'] = txt
        context.user_data['state'] = 'prod_price'
        await update.message.reply_text("💰 Price (number only):")
    
    elif state == 'prod_price':
        try:
            price = float(txt)
        except:
            await update.message.reply_text("❌ Number only!")
            return
        
        db.add_prod({
            'type': context.user_data['ptype'],
            'name': context.user_data['pname'],
            'price': price
        })
        
        ptype = context.user_data.get('ptype', '').upper()
        pname = context.user_data.get('pname', '')
        context.user_data.clear()
        
        await update.message.reply_text(
            f"✅ *Product Added!*\n\n📦 {pname}\n🏷️ {ptype}\n💰 {price:.0f} TK",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_kb()
        )
    
    # ── STOCK ADD ──
    elif state == 'stock_add':
        if txt.lower() in ['done', '✅ done']:
            context.user_data.clear()
            await update.message.reply_text("✅ Stock added!", reply_markup=admin_kb())
            return
        
        added = 0
        for line in txt.split('\n'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                try:
                    price = float(parts[-1])
                    db.add_stock({
                        'productType': 'vpn',
                        'productName': 'VPN Account',
                        'data': {'email': parts[0], 'password': parts[1], 'expireDate': parts[2]},
                        'price': price,
                        'addedBy': uid
                    })
                    added += 1
                except: pass
        
        await update.message.reply_text(
            f"✅ {added} items added!\nSend more or `done`.",
            reply_markup=ReplyKeyboardMarkup([[
                KeyboardButton("✅ Done"), KeyboardButton("❌ Cancel")
            ]], resize_keyboard=True)
        )
    
    # ── BROADCAST ──
    elif state == 'broadcast':
        context.user_data.clear()
        users = db.all_users()
        s, f = 0, 0
        msg = await update.message.reply_text("📤 Sending...")
        
        for u in users:
            try:
                await context.bot.send_message(u['telegramId'], f"📢 *Announcement*\n\n{txt}", parse_mode=ParseMode.MARKDOWN)
                s += 1
            except:
                f += 1
            await asyncio.sleep(0.05)
        
        await msg.edit_text(f"✅ Done!\n✅ {s} sent\n❌ {f} failed")
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_kb())
    
    # ── BAN/UNBAN ──
    elif state == 'ban_user':
        context.user_data.clear()
        try:
            target = int(txt)
            user = db.ban(target)
            if user:
                status = "banned" if user.get('isBanned') else "unbanned"
                await update.message.reply_text(f"✅ User `{target}` {status}!", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())
            else:
                await update.message.reply_text("❌ User not found!", reply_markup=admin_kb())
        except:
            await update.message.reply_text("❌ Invalid ID!", reply_markup=admin_kb())

# ═══════════════ CALLBACK ROUTER ═══════════════
async def callback_router(update, context):
    q = update.callback_query
    d = q.data
    
    if d == "join_ok":
        await join_ok(update, context)
    elif d.startswith("buy_"):
        await buy_prod(update, context)
    elif d.startswith("dep_") or d == "dep_cancel":
        await deposit_method_cb(update, context)
    elif d.startswith("app_") or d.startswith("rej_"):
        await dep_approve(update, context)
    elif d == "back_main":
        await q.edit_message_text("🏠")
        await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))

# ═══════════════ ERROR HANDLER ═══════════════
async def error_handler(update, context):
    log.error(f"Error: {context.error}")
    try:
        if update and update.effective_chat:
            await context.bot.send_message(update.effective_chat.id, "❌ An error occurred. Please try again.")
    except: pass

# ═══════════════ MAIN ═══════════════
def run_web():
    log.info(f"🌐 Web on port {C.PORT}")
    wsgi_serve(app, host='0.0.0.0', port=C.PORT, threads=2)

def run_bot():
    bot_app = ApplicationBuilder()\
        .token(C.TOKEN)\
        .defaults(Defaults(parse_mode=ParseMode.MARKDOWN))\
        .build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("admin", admin_panel))
    bot_app.add_handler(CommandHandler("help", show_help))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    bot_app.add_handler(CallbackQueryHandler(callback_router))
    bot_app.add_error_handler(error_handler)
    
    log.info("🤖 Bot is running!")
    print("✅ Bot started! Press Ctrl+C to stop.")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def main():
    print("""
╔══════════════════════════════════════╗
║     👑 ROYAL MAIL STORE            ║
║     Starting...                     ║
╚══════════════════════════════════════╝
    """)
    
    if not C.TOKEN:
        print("❌ BOT_TOKEN not set!")
        sys.exit(1)
    
    threading.Thread(target=run_web, daemon=True, name="WebServer").start()
    run_bot()

if __name__ == "__main__":
    main()
