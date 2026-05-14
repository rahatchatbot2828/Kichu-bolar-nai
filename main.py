#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    👑 ROYAL MAIL STORE - 100% WORKING                      ║
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

from flask import Flask, jsonify, render_template_string
from waitress import serve as wsgi_serve
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Defaults
from telegram.constants import ParseMode, ChatMemberStatus

# ═══════════════ CONFIG ═══════════════
class C:
    TOKEN = os.getenv("BOT_TOKEN", "8959981246:AAGBXTogxrrFEg08-seUXv80N6bmLI8ujq8")
    ADMIN = [int(x.strip()) for x in os.getenv("ADMIN_ID", "5507924915").split(",") if x.strip()]
    CHANNEL = os.getenv("CHANNEL_USERNAME", "@RoyalMarketingZone")
    BKASH = os.getenv("BKASH_NUMBER", "01301027106")
    NAGAD = os.getenv("NAGAD_NUMBER", "01301027106")
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

# ═══════════════ DATABASE ═══════════════
class DB:
    def __init__(self):
        self.d = C.DIR
        for n in ['users', 'products', 'stock', 'deposits']:
            f = self.d / f"{n}.json"
            if not f.exists():
                f.write_text('[]')

    def r(self, n):
        try: return json.loads((self.d / f"{n}.json").read_text())
        except: return []

    def w(self, n, d):
        (self.d / f"{n}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str))

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

    def del_prod(self, pid):
        p = self.r('products')
        self.w('products', [x for x in p if x['id'] != pid])

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

@app.route('/')
def home():
    s = db.stats()
    h, m = divmod(s['uptime'], 3600)
    m //= 60
    return f"""<!DOCTYPE html><html><head><title>ROYAL MAIL STORE</title><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg,#0a0a0a,#1a1a2e);color:#ffd700;font-family:system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center}}
.box{{text-align:center;padding:30px;background:rgba(0,0,0,.6);border:2px solid #ffd700;border-radius:20px;max-width:450px;width:90%}}
h1{{font-size:1.8em;margin:10px 0}}.green{{color:#0f0;font-size:1.1em;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:15px 0}}
.card{{padding:10px;background:rgba(255,215,0,.1);border:1px solid #ffd700;border-radius:8px}}
.card .num{{font-size:1.2em;font-weight:bold}}.card .lbl{{font-size:.7em;color:#aaa}}
p{{color:#aaa;font-size:.8em}}</style></head><body><div class="box">
<div style="font-size:2.5em">👑</div><h1>ROYAL MAIL STORE</h1><div class="green">🟢 Bot Running</div>
<div class="grid"><div class="card"><div class="num">{s['users']}</div><div class="lbl">Users</div></div>
<div class="card"><div class="num">{s['revenue']:.0f} TK</div><div class="lbl">Revenue</div></div>
<div class="card"><div class="num">{s['stock']}</div><div class="lbl">Stock</div></div>
<div class="card"><div class="num">{s['pending']}</div><div class="lbl">Pending</div></div></div>
<p>Uptime: {h}h {m}m | Platform: Replit</p></div></body></html>"""

@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/ping')
def ping():
    return "pong"

# ═══════════════ KEYBOARDS ═══════════════
def main_kb(uid):
    admin = uid in C.ADMIN
    rows = [
        [KeyboardButton("🔐 VPN"), KeyboardButton("🌐 Proxy")],
        [KeyboardButton("📧 Mail"), KeyboardButton("💰 Deposit")],
        [KeyboardButton("💳 Balance"), KeyboardButton("ℹ️ Help")]
    ]
    if admin:
        rows.append([KeyboardButton("👑 Admin")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Product"), KeyboardButton("📥 Stock")],
        [KeyboardButton("👥 Users"), KeyboardButton("💰 Pending")],
        [KeyboardButton("📊 Stats"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("🔙 Main")]
    ], resize_keyboard=True)

# ═══════════════ FORCE JOIN ═══════════════
async def check_join(update, context):
    uid = update.effective_user.id
    if uid in C.ADMIN: return True
    try:
        member = await context.bot.get_chat_member(C.CHANNEL, uid)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join", url=f"https://t.me/{C.CHANNEL[1:]}")],
                [InlineKeyboardButton("✅ Joined", callback_data="join_ok")]
            ])
            m = update.message or update.callback_query.message
            await m.reply_text(f"⚠️ Join {C.CHANNEL} first!", reply_markup=kb)
            return False
        return True
    except:
        return True

# ═══════════════ HANDLERS ═══════════════

async def start(update, context):
    if not await check_join(update, context): return
    u = update.effective_user
    db.save_user({'telegramId': u.id, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    await update.message.reply_text(
        f"👑 *ROYAL MAIL STORE*\n\n🔐 VPN | 🌐 Proxy | 📧 Mail\n\n💰 Balance: {db.user(u.id)['balance']:.0f} TK\n💳 Deposit: {C.MIN_DEP}-{C.MAX_DEP} TK\n\n👇 Select:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(u.id)
    )

async def join_ok(update, context):
    q = update.callback_query; await q.answer()
    if await check_join(update, context):
        await q.edit_message_text("✅ Verified!")
        await start(update, context)

async def handle_msg(update, context):
    if not await check_join(update, context): return
    
    uid = update.effective_user.id
    txt = update.message.text.strip()
    u = update.effective_user
    
    db.save_user({'telegramId': uid, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    
    user = db.user(uid)
    if user and user.get('isBanned'):
        await update.message.reply_text("🚫 Banned! Contact admin.")
        return
    
    # State handling
    state = context.user_data.get('state')
    if state:
        return await handle_state(update, context)
    
    # ── MENU ROUTING ──
    if txt == "🔐 VPN":
        await show_cat(update, context, "vpn")
    elif txt == "🌐 Proxy":
        await show_cat(update, context, "proxy")
    elif txt == "📧 Mail":
        await show_cat(update, context, "mail")
    elif txt == "💰 Deposit":
        context.user_data['state'] = 'deposit'
        await update.message.reply_text(
            f"💰 *Deposit*\n\n💳 bKash: `{C.BKASH}`\n💳 Nagad: `{C.NAGAD}`\n\nReply: `Amount TXN_ID`\nExample: `50 ABC123`\nMin: {C.MIN_DEP} TK | Max: {C.MAX_DEP} TK\nSend `cancel` to exit.",
            parse_mode=ParseMode.MARKDOWN
        )
    elif txt == "💳 Balance":
        user = db.user(uid)
        await update.message.reply_text(
            f"💳 *Balance*\n\n💰 {user['balance']:.0f} TK\n📊 Spent: {user['totalSpent']:.0f} TK\n💎 Deposited: {user['totalDeposited']:.0f} TK\n📦 Purchases: {user['totalPurchases']}",
            parse_mode=ParseMode.MARKDOWN
        )
    elif txt == "ℹ️ Help":
        await update.message.reply_text(
            f"ℹ️ *Help*\n\n1️⃣ Choose VPN/Proxy/Mail\n2️⃣ Buy with balance\n3️⃣ Get delivery\n\n💰 Deposit {C.MIN_DEP}-{C.MAX_DEP} TK\n💳 bKash: {C.BKASH}\n📞 {C.CHANNEL}",
            parse_mode=ParseMode.MARKDOWN
        )
    elif txt == "👑 Admin" and uid in C.ADMIN:
        await admin_panel(update, context)
    elif txt == "🔙 Main":
        await update.message.reply_text("🏠 Menu", reply_markup=main_kb(uid))
    elif uid in C.ADMIN:
        await admin_msg(update, context)
    else:
        await update.message.reply_text("Use buttons below 👇", reply_markup=main_kb(uid))

# ── PRODUCTS ──
async def show_cat(update, context, cat):
    prods = db.prods(cat)
    if not prods:
        await update.message.reply_text(f"❌ No {cat.upper()} products yet!")
        return
    kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']:.0f} TK", callback_data=f"buy_{p['id']}")] for p in prods]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    await update.message.reply_text(f"📦 *{cat.upper()}*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def buy_prod(update, context):
    q = update.callback_query; await q.answer()
    
    if q.data == "back_main":
        await q.edit_message_text("🏠")
        await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))
        return
    
    uid = update.effective_user.id
    pid = q.data.replace("buy_", "")
    product = db.prod(pid)
    user = db.user(uid)
    
    if not product: return await q.edit_message_text("❌ Not found!")
    if user['balance'] < product['price']:
        return await q.edit_message_text(f"❌ Balance: {user['balance']:.0f} TK\n💰 Need: {product['price']:.0f} TK")
    
    stock = db.stock_avail(product['type'], product['price'])
    if not stock: return await q.edit_message_text("❌ Out of stock!")
    
    db.pay(uid, product['price'])
    db.sell(stock['id'], uid)
    bal = db.user(uid)['balance']
    
    msg = f"✅ *Purchased!*\n📦 {product['name']}\n💰 {product['price']:.0f} TK\n💳 Balance: {bal:.0f} TK\n\n"
    d = stock['data']
    
    if product['type'] == 'vpn':
        msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`\n📅 {d.get('expireDate','')}"
    elif product['type'] == 'proxy':
        msg += f"🌐 `{d.get('host','')}`:{d.get('port','')}\n👤 `{d.get('username','')}`\n🔑 `{d.get('password','')}`"
    elif product['type'] == 'mail':
        msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`\n🔑 `{d.get('recovery','')}`"
    
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

# ── DEPOSIT ──
async def proc_deposit(update, context):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    if txt.lower() in ['cancel', '❌ cancel']:
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled", reply_markup=main_kb(uid))
        return
    
    # Split: "50 TXN123"
    parts = txt.split(None, 1)
    
    if len(parts) < 2:
        await update.message.reply_text("❌ Format: `50 TXN_ID`\nTry again or `cancel`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        amt = float(parts[0])
    except:
        await update.message.reply_text("❌ Amount must be number!\nTry: `50 TXN123`", parse_mode=ParseMode.MARKDOWN)
        return
    
    txn = parts[1]
    
    if amt < C.MIN_DEP:
        await update.message.reply_text(f"❌ Min: {C.MIN_DEP} TK!\nTry again:", parse_mode=ParseMode.MARKDOWN)
        return
    if amt > C.MAX_DEP:
        await update.message.reply_text(f"❌ Max: {C.MAX_DEP} TK!\nTry again:", parse_mode=ParseMode.MARKDOWN)
        return
    
    dep = db.dep_create({
        'telegramId': uid,
        'username': update.effective_user.username or '',
        'firstName': update.effective_user.first_name or 'User',
        'amount': amt,
        'transactionId': txn,
        'paymentMethod': 'Manual'
    })
    
    context.user_data.clear()
    
    # Notify admin
    for aid in C.ADMIN:
        try:
            await context.bot.send_message(aid,
                f"💰 *New Deposit!*\n\n👤 {update.effective_user.first_name} (`{uid}`)\n💰 {amt:.0f} TK\n🔢 `{txn}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Approve", callback_data=f"app_{dep['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{dep['id']}")
                ]])
            )
        except: pass
    
    await update.message.reply_text(
        f"✅ *Deposit Submitted!*\n\n💰 {amt:.0f} TK\n🔢 `{txn}`\n⏳ Pending approval...",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(uid)
    )

# ── DEPOSIT APPROVAL ──
async def dep_approve(update, context):
    q = update.callback_query; await q.answer()
    
    if update.effective_user.id not in C.ADMIN: return
    
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
        await q.edit_message_text(f"{'✅ Approved' if status=='approved' else '❌ Rejected'}!")
    else:
        await q.edit_message_text("❌ Deposit not found!")

# ── ADMIN PANEL ──
async def admin_panel(update, context):
    if update.effective_user.id not in C.ADMIN: return
    s = db.stats()
    h, m = divmod(s['uptime'], 3600); m //= 60
    await update.message.reply_text(
        f"👑 *Admin Panel*\n\n👥 Users: {s['users']}\n💰 Revenue: {s['revenue']:.0f} TK\n📦 Stock: {s['stock']}\n⏳ Pending: {s['pending']}\n🕐 {h}h {m}m",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_kb()
    )

async def admin_msg(update, context):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    
    if txt == "➕ Product":
        context.user_data['state'] = 'prod_type'
        await update.message.reply_text("📦 Type: `vpn` `proxy` `mail`\n`cancel` to exit.", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "📥 Stock":
        context.user_data['state'] = 'stock_add'
        await update.message.reply_text("📥 Format: `email|pass|expire|price`\nMultiple lines OK.\n`done` to finish.", parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "👥 Users":
        users = db.all_users()
        msg = f"👥 *Users ({len(users)})*\n\n"
        for u in users[:30]:
            ban = "🚫" if u.get('isBanned') else "✅"
            msg += f"{ban} {u.get('firstName','?')} - {u['balance']:.0f} TK\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif txt == "💰 Pending":
        deps = db.dep_pending()
        if not deps:
            await update.message.reply_text("✅ No pending!")
            return
        for d in deps:
            await update.message.reply_text(
                f"💰 {d.get('firstName','User')} - {d['amount']:.0f} TK\n🔢 `{d['transactionId']}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅", callback_data=f"app_{d['id']}"),
                    InlineKeyboardButton("❌", callback_data=f"rej_{d['id']}")
                ]])
            )
    
    elif txt == "📊 Stats":
        s = db.stats()
        await update.message.reply_text(
            f"📊 *Stats*\n👥 {s['users']} users\n💰 {s['revenue']:.0f} TK revenue\n📦 {s['stock']} in stock\n⏳ {s['pending']} pending",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif txt == "📢 Broadcast":
        context.user_data['state'] = 'broadcast'
        await update.message.reply_text("📢 Send message to broadcast.\n`cancel` to exit.", parse_mode=ParseMode.MARKDOWN)

# ── STATE HANDLER ──
async def handle_state(update, context):
    state = context.user_data.get('state')
    txt = update.message.text.strip()
    uid = update.effective_user.id
    
    if txt.lower() in ['cancel', '❌ cancel']:
        context.user_data.clear()
        kb = admin_kb() if uid in C.ADMIN else main_kb(uid)
        await update.message.reply_text("❌ Cancelled", reply_markup=kb)
        return
    
    if state == 'deposit':
        await proc_deposit(update, context)
    
    elif state == 'prod_type':
        if txt.lower() not in ['vpn', 'proxy', 'mail']:
            await update.message.reply_text("❌ vpn/proxy/mail only!")
            return
        context.user_data['ptype'] = txt.lower()
        context.user_data['state'] = 'prod_name'
        await update.message.reply_text("📝 Product name:")
    
    elif state == 'prod_name':
        context.user_data['pname'] = txt
        context.user_data['state'] = 'prod_price'
        await update.message.reply_text("💰 Price (number):")
    
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
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ *Added!*\n📦 {context.user_data.get('pname','')}\n🏷️ {context.user_data.get('ptype','').upper()}\n💰 {price:.0f} TK",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_kb()
        )
    
    elif state == 'stock_add':
        if txt.lower() in ['done', '✅ done']:
            context.user_data.clear()
            await update.message.reply_text("✅ Done!", reply_markup=admin_kb())
            return
        
        added = 0
        for line in txt.split('\n'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                try:
                    price = float(parts[-1])
                    db.add_stock({
                        'productType': 'vpn',
                        'productName': 'VPN',
                        'data': {'email': parts[0], 'password': parts[1], 'expireDate': parts[2]},
                        'price': price,
                        'addedBy': uid
                    })
                    added += 1
                except:
                    pass
        await update.message.reply_text(f"✅ {added} added! More or `done`.")
    
    elif state == 'broadcast':
        context.user_data.clear()
        users = db.all_users()
        s, f = 0, 0
        m = await update.message.reply_text("📤 Sending...")
        for u in users:
            try:
                await context.bot.send_message(u['telegramId'], f"📢 *Message*\n\n{txt}", parse_mode=ParseMode.MARKDOWN)
                s += 1
            except:
                f += 1
            await asyncio.sleep(0.05)
        await m.edit_text(f"✅ Done! ✅{s} ❌{f}")
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_kb())

# ── CALLBACK ROUTER ──
async def callback_router(update, context):
    q = update.callback_query
    d = q.data
    if d == "join_ok": await join_ok(update, context)
    elif d.startswith("buy_"): await buy_prod(update, context)
    elif d.startswith("app_") or d.startswith("rej_"): await dep_approve(update, context)
    elif d == "back_main":
        await q.edit_message_text("🏠")
        await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))

# ═══════════════ MAIN ═══════════════
def run_bot():
    app_bot = ApplicationBuilder().token(C.TOKEN).defaults(Defaults(parse_mode=ParseMode.MARKDOWN)).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_panel))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app_bot.add_handler(CallbackQueryHandler(callback_router))
    log.info("🤖 Bot running!")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def run_web():
    log.info(f"🌐 Web on port {C.PORT}")
    wsgi_serve(app, host='0.0.0.0', port=C.PORT, threads=2)

def main():
    print("👑 ROYAL MAIL STORE - Starting...")
    if not C.TOKEN:
        print("❌ BOT_TOKEN not set!")
        sys.exit(1)
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()

if __name__ == "__main__":
    main()
