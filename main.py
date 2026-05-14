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

@app.route('/')
def home():
    s = db.stats()
    h, m = divmod(s['uptime'], 3600); m //= 60
    return f"""<!DOCTYPE html><html><head><title>ROYAL MAIL STORE</title><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0a0a0a;color:#ffd700;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh}}
.box{{text-align:center;padding:30px;border:2px solid #ffd700;border-radius:20px;max-width:450px;width:90%}}
h1{{font-size:1.8em}}.green{{color:#0f0;animation:pulse 2s infinite}}@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:15px 0}}
.card{{padding:10px;background:rgba(255,215,0,.1);border:1px solid #ffd700;border-radius:8px}}
.num{{font-size:1.2em;font-weight:bold}}.lbl{{font-size:.7em;color:#aaa}}
p{{color:#aaa;font-size:.8em}}</style></head><body><div class="box"><div style="font-size:3em">👑</div><h1>ROYAL MAIL STORE</h1><div class="green">🟢 Bot Running</div>
<div class="grid"><div class="card"><div class="num">{s['users']}</div><div class="lbl">Users</div></div>
<div class="card"><div class="num">{s['revenue']:.0f} TK</div><div class="lbl">Revenue</div></div>
<div class="card"><div class="num">{s['stock']}</div><div class="lbl">Stock</div></div>
<div class="card"><div class="num">{s['pending']}</div><div class="lbl">Pending</div></div></div>
<p>Uptime: {h}h {m}m</p></div></body></html>"""

@app.route('/health')
def health():
    return jsonify({"status":"ok"})

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
        [KeyboardButton("🚫 Ban"), KeyboardButton("🔙 Main")]
    ], resize_keyboard=True)

def done_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Done"), KeyboardButton("❌ Cancel")]
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
            m = update.message or (update.callback_query.message if update.callback_query else None)
            if m:
                await m.reply_text(
                    f"⚠️ Join {C.CHANNEL} first!\n\n1️⃣ Click 'Join Channel'\n2️⃣ Join\n3️⃣ Click 'I Joined'",
                    reply_markup=kb
                )
            return False
        return True
    except:
        return True

# ═══════════════ START ═══════════════
async def start(update, context):
    if not await check_join(update, context):
        return
    
    u = update.effective_user
    db.save_user({'telegramId': u.id, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    user = db.user(u.id)
    
    await update.message.reply_text(
        f"👑 *ROYAL MAIL STORE*\n\n🔐 VPN | 🌐 Proxy | 📧 Mail\n\n"
        f"💰 Balance: `{user['balance']:.0f} TK`\n"
        f"💳 Deposit: `{C.MIN_DEP}-{C.MAX_DEP} TK`\n\n"
        f"👇 Select:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(u.id)
    )

async def join_ok(update, context):
    q = update.callback_query
    await q.answer()
    if await check_join(update, context):
        await q.edit_message_text("✅ Verified!")
        await start(update, context)

# ═══════════════ MAIN HANDLER ═══════════════
async def handle_msg(update, context):
    # Force join check
    if not await check_join(update, context):
        return
    
    uid = update.effective_user.id
    txt = update.message.text.strip() if update.message.text else ""
    u = update.effective_user
    
    # Save user
    db.save_user({'telegramId': uid, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    
    # Ban check
    user = db.user(uid)
    if user and user.get('isBanned'):
        await update.message.reply_text("🚫 Banned! Contact admin.")
        return
    
    # ══════ STATE CHECK ══════
    state = context.user_data.get('state', '')
    
    # Handle Cancel in any state
    if txt in ['❌ Cancel', 'cancel', 'Cancel'] and state:
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled", reply_markup=main_kb(uid))
        return
    
    # Route states
    if state == 'deposit_amount':
        return await deposit_amount(update, context)
    elif state == 'deposit_txn':
        return await deposit_txn(update, context)
    elif state == 'prod_type':
        return await prod_type_step(update, context)
    elif state == 'prod_name':
        return await prod_name_step(update, context)
    elif state == 'prod_price':
        return await prod_price_step(update, context)
    elif state == 'stock_add':
        return await stock_add_step(update, context)
    elif state == 'broadcast':
        return await broadcast_step(update, context)
    elif state == 'ban_user':
        return await ban_step(update, context)
    
    # ══════ MENU ══════
    if txt == "🔐 VPN":
        await show_cat(update, context, "vpn")
    elif txt == "🌐 Proxy":
        await show_cat(update, context, "proxy")
    elif txt == "📧 Mail":
        await show_cat(update, context, "mail")
    elif txt == "💰 Deposit":
        await deposit_menu(update, context)
    elif txt == "💳 Balance":
        await show_balance(update, context)
    elif txt == "❓ Help":
        await show_help(update, context)
    elif txt == "👑 Admin" and uid in C.ADMIN:
        await admin_panel(update, context)
    elif txt == "🔙 Main":
        await update.message.reply_text("🏠 Menu", reply_markup=main_kb(uid))
    elif uid in C.ADMIN:
        await admin_actions(update, context)
    elif txt:  # Only respond if there's text
        await update.message.reply_text("👇 Use buttons:", reply_markup=main_kb(uid))

# ═══════════════ PRODUCTS ═══════════════
async def show_cat(update, context, cat):
    prods = db.prods(cat)
    emoji = {"vpn": "🔐", "proxy": "🌐", "mail": "📧"}.get(cat, "📦")
    
    if not prods:
        await update.message.reply_text(f"{emoji} No {cat.upper()} products yet!")
        return
    
    kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']:.0f} TK", callback_data=f"buy_{p['id']}")] for p in prods]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    
    await update.message.reply_text(
        f"{emoji} *{cat.upper()}*\n\n{len(prods)} products\n👇 Select:",
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
        return await q.edit_message_text("❌ Not found!")
    
    if user['balance'] < product['price']:
        return await q.edit_message_text(
            f"❌ Balance: `{user['balance']:.0f} TK`\n💰 Need: `{product['price']:.0f} TK`\n\nUse 💰 Deposit!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    stock = db.stock_avail(product['type'], product['price'])
    if not stock:
        return await q.edit_message_text("❌ Out of stock!")
    
    db.pay(uid, product['price'])
    db.sell(stock['id'], uid)
    bal = db.user(uid)['balance']
    
    msg = f"✅ *Purchased!*\n📦 {product['name']}\n💰 {product['price']:.0f} TK\n💳 Balance: {bal:.0f} TK\n\n"
    d = stock['data']
    
    if product['type'] == 'vpn':
        msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`\n📅 {d.get('expireDate','')}"
    elif product['type'] == 'proxy':
        msg += f"🌐 `{d.get('host','')}:{d.get('port','')}`\n👤 `{d.get('username','')}`\n🔑 `{d.get('password','')}`"
    elif product['type'] == 'mail':
        msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`\n🔑 `{d.get('recovery','')}`"
    
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

# ═══════════════ DEPOSIT ═══════════════

async def deposit_menu(update, context):
    """Show deposit method selection"""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 bKash", callback_data="dep_bkash"),
         InlineKeyboardButton("💳 Nagad", callback_data="dep_nagad")],
        [InlineKeyboardButton("🚀 Rocket", callback_data="dep_rocket")],
        [InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")]
    ])
    
    await update.message.reply_text(
        f"💰 *Deposit*\n\n"
        f"💳 bKash: `{C.BKASH}`\n"
        f"💳 Nagad: `{C.NAGAD}`\n"
        f"🚀 Rocket: `{C.ROCKET}`\n\n"
        f"Min: `{C.MIN_DEP} TK` | Max: `{C.MAX_DEP} TK`\n\n"
        f"👇 Choose method:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

async def deposit_method_cb(update, context):
    """Callback: Method selected"""
    q = update.callback_query
    await q.answer()
    
    if q.data == "dep_cancel":
        await q.edit_message_text("❌ Cancelled")
        await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))
        return
    
    methods = {
        "dep_bkash": ("bKash", C.BKASH),
        "dep_nagad": ("Nagad", C.NAGAD),
        "dep_rocket": ("Rocket", C.ROCKET),
    }
    
    method, number = methods.get(q.data, ("bKash", C.BKASH))
    
    context.user_data['dep_method'] = method
    context.user_data['dep_number'] = number
    context.user_data['state'] = 'deposit_amount'
    
    await q.edit_message_text(
        f"💳 *{method}*\n\n"
        f"📱 Send to: `{number}`\n\n"
        f"👇 Reply with amount:\n"
        f"Example: `50`\n\n"
        f"Min: `{C.MIN_DEP}` | Max: `{C.MAX_DEP}`\n"
        f"Send `cancel` to exit.",
        parse_mode=ParseMode.MARKDOWN
    )

async def deposit_amount(update, context):
    """State: Get amount"""
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    try:
        amt = float(txt)
    except:
        await update.message.reply_text("❌ Send number only! Example: `50`", parse_mode=ParseMode.MARKDOWN)
        return
    
    if amt < C.MIN_DEP:
        await update.message.reply_text(f"❌ Min: `{C.MIN_DEP} TK`!", parse_mode=ParseMode.MARKDOWN)
        return
    if amt > C.MAX_DEP:
        await update.message.reply_text(f"❌ Max: `{C.MAX_DEP} TK`!", parse_mode=ParseMode.MARKDOWN)
        return
    
    context.user_data['dep_amount'] = amt
    context.user_data['state'] = 'deposit_txn'
    
    await update.message.reply_text(
        f"💰 Amount: `{amt:.0f} TK`\n\n"
        f"🔢 Send Transaction ID:\n"
        f"Example: `ABC123`\n\n"
        f"Send `cancel` to exit.",
        parse_mode=ParseMode.MARKDOWN
    )

async def deposit_txn(update, context):
    """State: Get TXN ID & submit"""
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
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
                f"💰 *New Deposit!*\n\n👤 {update.effective_user.first_name}\n💰 `{amt:.0f} TK`\n💳 {method}\n🔢 `{txn}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅", callback_data=f"app_{dep['id']}"),
                    InlineKeyboardButton("❌", callback_data=f"rej_{dep['id']}")
                ]])
            )
        except: pass
    
    await update.message.reply_text(
        f"✅ *Submitted!*\n\n💰 `{amt:.0f} TK`\n💳 {method}\n🔢 `{txn}`\n\n⏳ Pending...",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(uid)
    )

async def dep_approve(update, context):
    """Approve/Reject deposit"""
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
            await context.bot.send_message(dep['telegramId'],
                f"{'✅ Approved!' if status=='approved' else '❌ Rejected!'}\n💰 {dep['amount']:.0f} TK",
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass
        await q.edit_message_text(f"{'✅' if status=='approved' else '❌'} {status}!")
    else:
        await q.edit_message_text("❌ Not found!")

# ═══════════════ BALANCE ═══════════════
async def show_balance(update, context):
    u = db.user(update.effective_user.id)
    if u:
        await update.message.reply_text(
            f"💳 *Balance*\n\n💰 `{u['balance']:.0f} TK`\n📊 Spent: `{u['totalSpent']:.0f} TK`\n💎 Deposited: `{u['totalDeposited']:.0f} TK`",
            parse_mode=ParseMode.MARKDOWN
        )

# ═══════════════ HELP ═══════════════
async def show_help(update, context):
    await update.message.reply_text(
        f"❓ *HELP*\n\n"
        f"1️⃣ Choose VPN/Proxy/Mail\n"
        f"2️⃣ Buy with balance\n"
        f"3️⃣ Get delivery\n\n"
        f"💰 *Deposit:*\n"
        f"💳 bKash: `{C.BKASH}`\n"
        f"💳 Nagad: `{C.NAGAD}`\n"
        f"🚀 Rocket: `{C.ROCKET}`\n\n"
        f"📥 Min: `{C.MIN_DEP} TK`\n"
        f"📤 Max: `{C.MAX_DEP} TK`\n\n"
        f"📞 Support: {C.SUPPORT}\n"
        f"📢 Channel: {C.CHANNEL}",
        parse_mode=ParseMode.MARKDOWN
    )

# ═══════════════ ADMIN ═══════════════
async def admin_panel(update, context):
    if update.effective_user.id not in C.ADMIN:
        return
    
    s = db.stats()
    h, m = divmod(s['uptime'], 3600); m //= 60
    
    await update.message.reply_text(
        f"👑 *Admin*\n\n👥 {s['users']} users\n💰 {s['revenue']:.0f} TK\n📦 {s['stock']} stock\n⏳ {s['pending']} pending\n🕐 {h}h {m}m",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_kb()
    )

async def admin_actions(update, context):
    txt = update.message.text.strip()
    
    if txt == "➕ Product":
        context.user_data['state'] = 'prod_type'
        await update.message.reply_text("📦 Type: `vpn` `proxy` `mail`")
    
    elif txt == "📥 Stock":
        context.user_data['state'] = 'stock_add'
        await update.message.reply_text("📥 Format: `email|pass|expire|price`\n`done` to finish.", reply_markup=done_kb())
    
    elif txt == "👥 Users":
        users = db.all_users()
        msg = f"👥 *Users ({len(users)})*\n\n"
        for u in users[:20]:
            msg += f"{'🚫' if u.get('isBanned') else '✅'} {u.get('firstName','?')} - {u['balance']:.0f} TK\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "💰 Pending":
        deps = db.dep_pending()
        if not deps:
            await update.message.reply_text("✅ No pending!")
            return
        for d in deps:
            await update.message.reply_text(
                f"💰 {d.get('firstName','?')} - {d['amount']:.0f} TK\n💳 {d.get('paymentMethod','?')}\n🔢 `{d['transactionId']}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅", callback_data=f"app_{d['id']}"),
                    InlineKeyboardButton("❌", callback_data=f"rej_{d['id']}")
                ]])
            )
    
    elif txt == "📊 Stats":
        s = db.stats()
        await update.message.reply_text(f"📊 *Stats*\n👥 {s['users']}\n💰 {s['revenue']:.0f} TK\n📦 {s['stock']}\n⏳ {s['pending']}", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "📢 Broadcast":
        context.user_data['state'] = 'broadcast'
        await update.message.reply_text("📢 Send message:")
    
    elif txt == "🚫 Ban":
        context.user_data['state'] = 'ban_user'
        await update.message.reply_text("🚫 Send User ID:")

# ═══════════════ STATE FUNCTIONS ═══════════════

async def prod_type_step(update, context):
    txt = update.message.text.strip().lower()
    if txt not in ['vpn', 'proxy', 'mail']:
        await update.message.reply_text("❌ vpn/proxy/mail only!")
        return
    context.user_data['ptype'] = txt
    context.user_data['state'] = 'prod_name'
    await update.message.reply_text("📝 Name:")

async def prod_name_step(update, context):
    context.user_data['pname'] = update.message.text.strip()
    context.user_data['state'] = 'prod_price'
    await update.message.reply_text("💰 Price:")

async def prod_price_step(update, context):
    try:
        price = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Number only!")
        return
    
    db.add_prod({
        'type': context.user_data['ptype'],
        'name': context.user_data['pname'],
        'price': price
    })
    
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Added!\n📦 {context.user_data.get('pname','')}\n💰 {price:.0f} TK",
        reply_markup=admin_kb()
    )

async def stock_add_step(update, context):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    
    if txt in ['✅ Done', 'done']:
        context.user_data.clear()
        await update.message.reply_text("✅ Done!", reply_markup=admin_kb())
        return
    
    added = 0
    for line in txt.split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            try:
                db.add_stock({
                    'productType': 'vpn',
                    'productName': 'VPN',
                    'data': {'email': parts[0], 'password': parts[1], 'expireDate': parts[2]},
                    'price': float(parts[3]),
                    'addedBy': uid
                })
                added += 1
            except: pass
    
    await update.message.reply_text(f"✅ {added} added! More or Done.", reply_markup=done_kb())

async def broadcast_step(update, context):
    txt = update.message.text.strip()
    context.user_data.clear()
    
    users = db.all_users()
    s, f = 0, 0
    m = await update.message.reply_text("📤 Sending...")
    
    for u in users:
        try:
            await context.bot.send_message(u['telegramId'], txt, parse_mode=ParseMode.MARKDOWN)
            s += 1
        except: f += 1
        await asyncio.sleep(0.05)
    
    await m.edit_text(f"✅ Done! ✅{s} ❌{f}")
    await update.message.reply_text("👑 Admin", reply_markup=admin_kb())

async def ban_step(update, context):
    txt = update.message.text.strip()
    context.user_data.clear()
    try:
        tid = int(txt)
        u = db.ban(tid)
        if u:
            await update.message.reply_text(f"✅ {'Banned' if u.get('isBanned') else 'Unbanned'}!", reply_markup=admin_kb())
        else:
            await update.message.reply_text("❌ Not found!", reply_markup=admin_kb())
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

# ═══════════════ MAIN ═══════════════
def run_web():
    log.info(f"🌐 Web on {C.PORT}")
    wsgi_serve(app, host='0.0.0.0', port=C.PORT, threads=2)

def run_bot():
    bot = ApplicationBuilder()\
        .token(C.TOKEN)\
        .defaults(Defaults(parse_mode=ParseMode.MARKDOWN))\
        .build()
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("admin", admin_panel))
    bot.add_handler(CommandHandler("help", show_help))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    bot.add_handler(CallbackQueryHandler(callback_router))
    bot.add_error_handler(error_handler)
    
    log.info("🤖 Bot running!")
    print("✅ Bot started!")
    bot.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def main():
    print("👑 ROYAL MAIL STORE - Starting...")
    if not C.TOKEN:
        print("❌ BOT_TOKEN missing!")
        sys.exit(1)
    
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()

if __name__ == "__main__":
    main()
