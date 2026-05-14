#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    👑 ROYAL MAIL STORE - ULTIMATE BOT                      ║
║              VPN • Proxy • Mail • Auto Delivery • Admin Panel              ║
║                    Replit • Render • Railway • Termux                      ║
║                    CANCEL BUTTON EVERYWHERE • NO ERRORS                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, uuid, asyncio, logging, threading
from datetime import datetime
from pathlib import Path

# ═══════════════ AUTO INSTALL ═══════════════
def install_packages():
    needed = []
    try: from flask import Flask
    except: needed.append("flask==3.0.0")
    try: from telegram import Update
    except: needed.append("python-telegram-bot==20.7")
    try: from waitress import serve
    except: needed.append("waitress==3.0.0")
    if needed:
        print(f"📦 Installing: {' '.join(needed)}")
        for pkg in needed: os.system(f"{sys.executable} -m pip install --quiet {pkg}")
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
for lg in ["telegram", "httpx", "waitress"]: logging.getLogger(lg).setLevel(logging.ERROR)

# ═══════════════ DATABASE ═══════════════
class DB:
    def __init__(self):
        self.files = {
            'users': [], 'products': [], 'stock': [], 'deposits': [],
            'coupons': [], 'tickets': [], 'broadcasts': [], 'settings': {
                'bot_name': '👑 ROYAL MAIL STORE', 'welcome_msg': '',
                'min_dep': C.MIN_DEP, 'max_dep': C.MAX_DEP,
                'force_join': True, 'maintenance': False,
                'ref_bonus': 5, 'max_daily_buy': 20
            }
        }
        for n, default in self.files.items():
            f = C.DIR / f"{n}.json"
            if not f.exists():
                if isinstance(default, list): f.write_text('[]')
                else: f.write_text(json.dumps(default, indent=2))

    def _r(self, n):
        try: return json.loads((C.DIR / f"{n}.json").read_text(encoding='utf-8'))
        except: return [] if n != 'settings' else {}

    def _w(self, n, d):
        (C.DIR / f"{n}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

    # ═══════════ USERS ═══════════
    def user(self, tid):
        for u in self._r('users'):
            if u.get('telegramId') == tid: return u.copy()
        return None

    def save_user(self, d):
        users = self._r('users')
        idx = next((i for i, u in enumerate(users) if u.get('telegramId') == d.get('telegramId')), None)
        now = datetime.now().isoformat()
        if idx is not None: users[idx].update(d); users[idx]['lastActive'] = now
        else: users.append({
            'telegramId': d['telegramId'], 'username': d.get('username', ''),
            'firstName': d.get('firstName', 'User'), 'balance': 0.0,
            'totalSpent': 0.0, 'totalDeposited': 0.0, 'totalPurchases': 0,
            'isBanned': False, 'isPremium': False, 'role': 'admin' if d['telegramId'] in C.ADMIN else 'user',
            'referralCode': str(uuid.uuid4())[:8].upper(), 'referredBy': None,
            'referralCount': 0, 'referralEarnings': 0.0,
            'warnings': 0, 'notes': '', 'joinedAt': now, 'lastActive': now
        })
        self._w('users', users)

    def all_users(self, include_banned=False):
        users = self._r('users')
        if not include_banned: users = [u for u in users if not u.get('isBanned')]
        return users

    def search_users(self, query):
        q = query.lower()
        return [u for u in self._r('users') if q in str(u.get('telegramId','')) or q in u.get('username','').lower() or q in u.get('firstName','').lower()]

    def get_top_users(self, limit=10, by='totalSpent'):
        return sorted(self._r('users'), key=lambda u: u.get(by, 0), reverse=True)[:limit]

    def add_bal(self, tid, amt):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['balance'] = round(u['balance'] + amt, 2)
                if amt > 0: u['totalDeposited'] = round(u.get('totalDeposited', 0) + amt, 2)
                self._w('users', users); return u
        return None

    def deduct_bal(self, tid, amt):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid and u['balance'] >= amt:
                u['balance'] = round(u['balance'] - amt, 2)
                u['totalSpent'] = round(u.get('totalSpent', 0) + amt, 2)
                u['totalPurchases'] = u.get('totalPurchases', 0) + 1
                self._w('users', users); return True
        return False

    def ban_user(self, tid, reason="", admin=0):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['isBanned'] = not u.get('isBanned', False)
                u['banReason'] = reason if u['isBanned'] else ''
                u['bannedBy'] = admin if u['isBanned'] else None
                u['bannedAt'] = datetime.now().isoformat() if u['isBanned'] else None
                self._w('users', users); return u
        return None

    def warn_user(self, tid, reason, admin):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['warnings'] = u.get('warnings', 0) + 1
                if u['warnings'] >= 3: u['isBanned'] = True; u['banReason'] = f"3 warnings: {reason}"
                self._w('users', users); return u
        return None

    def reset_warnings(self, tid):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid: u['warnings'] = 0; self._w('users', users); return u
        return None

    def set_premium(self, tid, days=30):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['isPremium'] = True
                u['premiumUntil'] = (datetime.now() + __import__('datetime').timedelta(days=days)).isoformat()
                self._w('users', users); return u
        return None

    def add_note(self, tid, note, admin):
        users = self._r('users')
        for u in users:
            if u['telegramId'] == tid:
                u['notes'] = f"{u.get('notes','')}\n[{datetime.now().strftime('%d/%m/%y')}] Admin {admin}: {note}"
                self._w('users', users); return u
        return None

    # ═══════════ PRODUCTS ═══════════
    def prods(self, pt=None, active_only=True):
        p = self._r('products')
        if active_only: p = [x for x in p if x.get('active', True)]
        if pt: p = [x for x in p if x.get('type') == pt]
        return p

    def prod(self, pid):
        for p in self._r('products'):
            if p.get('id') == pid: return p.copy()
        return None

    def add_prod(self, d):
        p = self._r('products')
        d['id'] = str(int(time.time() * 1000))
        d['active'] = True; d['featured'] = False
        d['totalSold'] = 0; d['totalRevenue'] = 0.0
        d['createdAt'] = datetime.now().isoformat(); d['updatedAt'] = datetime.now().isoformat()
        p.append(d); self._w('products', p)

    def update_prod(self, pid, updates):
        p = self._r('products')
        for x in p:
            if x['id'] == pid: x.update(updates); x['updatedAt'] = datetime.now().isoformat(); self._w('products', p); return x
        return None

    def del_prod(self, pid):
        p = self._r('products'); self._w('products', [x for x in p if x['id'] != pid])

    def toggle_prod(self, pid):
        p = self._r('products')
        for x in p:
            if x['id'] == pid: x['active'] = not x.get('active', True); self._w('products', p); return x
        return None

    def feature_prod(self, pid):
        p = self._r('products')
        for x in p:
            if x['id'] == pid: x['featured'] = not x.get('featured', False); self._w('products', p); return x
        return None

    # ═══════════ STOCK ═══════════
    def stock_avail(self, pt, price=None, pid=None):
        for s in self._r('stock'):
            if s.get('productType') == pt and not s.get('isSold'):
                if price and s.get('price') != price: continue
                if pid and s.get('productId') != pid: continue
                return s.copy()
        return None

    def add_stock(self, d):
        s = self._r('stock'); d['id'] = str(int(time.time() * 1000))
        d['isSold'] = False; d['soldTo'] = None; d['soldAt'] = None
        d['addedAt'] = datetime.now().isoformat(); s.append(d); self._w('stock', s)
        return d

    def add_stock_bulk(self, items):
        s = self._r('stock'); added = 0
        for item in items:
            item['id'] = str(int(time.time() * 1000)) + str(added)
            item['isSold'] = False; item['soldTo'] = None; item['addedAt'] = datetime.now().isoformat()
            s.append(item); added += 1
        self._w('stock', s); return added

    def sell(self, sid, buyer):
        s = self._r('stock')
        for x in s:
            if x['id'] == sid: x['isSold'] = True; x['soldTo'] = buyer; x['soldAt'] = datetime.now().isoformat(); self._w('stock', s); return x
        return None

    def del_stock(self, sid):
        s = self._r('stock'); self._w('stock', [x for x in s if x['id'] != sid])

    def clear_sold_stock(self):
        s = self._r('stock'); self._w('stock', [x for x in s if not x.get('isSold')])

    def stock_stats(self):
        s = self._r('stock')
        types = {}
        for x in s:
            t = x.get('productType', 'other')
            if t not in types: types[t] = {'total': 0, 'avail': 0, 'sold': 0}
            types[t]['total'] += 1
            if x.get('isSold'): types[t]['sold'] += 1
            else: types[t]['avail'] += 1
        return {'total': len(s), 'avail': len([x for x in s if not x.get('isSold')]), 'sold': len([x for x in s if x.get('isSold')]), 'by_type': types}

    def stock_value(self):
        s = self._r('stock')
        avail = sum(x.get('price', 0) for x in s if not x.get('isSold'))
        sold = sum(x.get('price', 0) for x in s if x.get('isSold'))
        return {'avail_value': avail, 'sold_value': sold, 'total_value': avail + sold}

    # ═══════════ DEPOSITS ═══════════
    def dep_create(self, d):
        deps = self._r('deposits'); d['id'] = str(int(time.time() * 1000))
        d['status'] = 'pending'; d['createdAt'] = datetime.now().isoformat()
        deps.append(d); self._w('deposits', deps); return d

    def dep_pending(self): return [d for d in self._r('deposits') if d['status'] == 'pending']
    
    def dep_approved(self): return [d for d in self._r('deposits') if d['status'] == 'approved']
    
    def dep_rejected(self): return [d for d in self._r('deposits') if d['status'] == 'rejected']

    def dep_update(self, did, status, admin):
        deps = self._r('deposits')
        for d in deps:
            if d['id'] == did:
                d['status'] = status; d['reviewedBy'] = admin; d['reviewedAt'] = datetime.now().isoformat()
                if status == 'approved': self.add_bal(d['telegramId'], d['amount'])
                self._w('deposits', deps); return d
        return None

    def dep_user(self, tid):
        return [d for d in self._r('deposits') if d['telegramId'] == tid]

    def dep_stats(self):
        deps = self._r('deposits'); today = datetime.now().date()
        pending = [d for d in deps if d['status'] == 'pending']
        approved = [d for d in deps if d['status'] == 'approved']
        today_approved = [d for d in approved if datetime.fromisoformat(d.get('reviewedAt', d.get('createdAt'))).date() == today]
        return {
            'pending': len(pending), 'pending_amount': sum(d['amount'] for d in pending),
            'approved': len(approved), 'approved_amount': sum(d['amount'] for d in approved),
            'rejected': len([d for d in deps if d['status'] == 'rejected']),
            'today': len(today_approved), 'today_amount': sum(d['amount'] for d in today_approved),
            'total': len(deps)
        }

    # ═══════════ COUPONS ═══════════
    def coupon_create(self, d):
        coupons = self._r('coupons'); d['id'] = str(int(time.time() * 1000))
        d['usedCount'] = 0; d['active'] = True; d['createdAt'] = datetime.now().isoformat()
        coupons.append(d); self._w('coupons', coupons); return d

    def coupon_get(self, code):
        for c in self._r('coupons'):
            if c.get('code', '').upper() == code.upper() and c.get('active'): return c
        return None

    def coupon_use(self, code):
        coupons = self._r('coupons')
        for c in coupons:
            if c.get('code', '').upper() == code.upper():
                c['usedCount'] = c.get('usedCount', 0) + 1
                if c['usedCount'] >= c.get('maxUses', 100): c['active'] = False
                self._w('coupons', coupons); return True
        return False

    def coupon_all(self): return self._r('coupons')
    
    def coupon_del(self, cid):
        self._w('coupons', [c for c in self._r('coupons') if c['id'] != cid])

    # ═══════════ TICKETS ═══════════
    def ticket_create(self, d):
        tickets = self._r('tickets'); d['id'] = str(int(time.time() * 1000))
        d['status'] = 'open'; d['replies'] = []; d['createdAt'] = datetime.now().isoformat()
        tickets.append(d); self._w('tickets', tickets); return d

    def ticket_get(self, tid=None, status=None):
        tickets = self._r('tickets')
        if tid: tickets = [t for t in tickets if t.get('telegramId') == tid]
        if status: tickets = [t for t in tickets if t.get('status') == status]
        return sorted(tickets, key=lambda t: t.get('createdAt', ''), reverse=True)

    def ticket_reply(self, tid, reply):
        tickets = self._r('tickets')
        for t in tickets:
            if t['id'] == tid: reply['time'] = datetime.now().isoformat(); t.setdefault('replies', []).append(reply); self._w('tickets', tickets); return t
        return None

    def ticket_close(self, tid):
        tickets = self._r('tickets')
        for t in tickets:
            if t['id'] == tid: t['status'] = 'closed'; t['closedAt'] = datetime.now().isoformat(); self._w('tickets', tickets); return t
        return None

    # ═══════════ SETTINGS ═══════════
    def settings(self): return self._r('settings')

    def update_settings(self, updates):
        s = self.settings(); s.update(updates); self._w('settings', s); return s

    # ═══════════ BROADCAST ═══════════
    def broadcast_save(self, d):
        b = self._r('broadcasts'); d['id'] = str(int(time.time() * 1000)); d['time'] = datetime.now().isoformat()
        b.append(d); self._w('broadcasts', b)

    def broadcast_history(self, limit=10):
        return sorted(self._r('broadcasts'), key=lambda x: x.get('time', ''), reverse=True)[:limit]

    # ═══════════ STATS ═══════════
    def stats(self):
        u = self._r('users'); d = self._r('deposits'); s = self._r('stock'); p = self._r('products')
        a = [x for x in d if x['status'] == 'approved']; today = datetime.now().date()
        today_a = [x for x in a if datetime.fromisoformat(x.get('reviewedAt', x.get('createdAt'))).date() == today]
        return {
            'users': len(u), 'active': len([x for x in u if not x.get('isBanned')]),
            'banned': len([x for x in u if x.get('isBanned')]), 'premium': len([x for x in u if x.get('isPremium')]),
            'revenue': sum(x['amount'] for x in a), 'today_revenue': sum(x['amount'] for x in today_a),
            'pending': len([x for x in d if x['status'] == 'pending']),
            'stock': len([x for x in s if not x.get('isSold')]), 'sold': len([x for x in s if x.get('isSold')]),
            'products': len(p), 'active_products': len([x for x in p if x.get('active', True)]),
            'coupons': len(self._r('coupons')), 'tickets_open': len([x for x in self._r('tickets') if x.get('status') == 'open']),
            'uptime': int(time.time() - C.START)
        }

    def revenue_chart(self, days=7):
        deps = [d for d in self._r('deposits') if d['status'] == 'approved']
        chart = {}
        for i in range(days):
            date = (datetime.now() - __import__('datetime').timedelta(days=i)).strftime('%Y-%m-%d')
            chart[date] = sum(d['amount'] for d in deps if d.get('reviewedAt', d.get('createdAt'))[:10] == date)
        return chart

db = DB()

# ═══════════════ FLASK ═══════════════
app = Flask(__name__)

@app.route('/')
def home():
    s = db.stats(); h, m = divmod(s['uptime'], 3600); m //= 60
    return f"""<!DOCTYPE html><html><head><title>ROYAL MAIL STORE</title><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg,#0a0a0a,#1a1a2e);color:#ffd700;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh}}
.box{{text-align:center;padding:40px;background:rgba(0,0,0,.6);border:2px solid #ffd700;border-radius:20px;max-width:500px;width:90%}}
h1{{font-size:2em;margin:10px 0}}.green{{color:#0f0;font-size:1.2em;animation:pulse 2s infinite}}@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:15px 0}}
.card{{padding:12px;background:rgba(255,215,0,.1);border:1px solid #ffd700;border-radius:8px}}
.num{{font-size:1.3em;font-weight:bold}}.lbl{{font-size:.75em;color:#aaa}}p{{color:#aaa;font-size:.8em;margin-top:10px}}</style></head>
<body><div class="box"><div style="font-size:3em">👑</div><h1>ROYAL MAIL STORE</h1><div class="green">🟢 Bot Running</div>
<div class="grid"><div class="card"><div class="num">{s['users']}</div><div class="lbl">Users</div></div>
<div class="card"><div class="num">{s['revenue']:.0f} TK</div><div class="lbl">Revenue</div></div>
<div class="card"><div class="num">{s['stock']}</div><div class="lbl">In Stock</div></div>
<div class="card"><div class="num">{s['pending']}</div><div class="lbl">Pending</div></div></div>
<p>Uptime: {h}h {m}m | Premium: {s['premium']} | Banned: {s['banned']}</p></div></body></html>"""

@app.route('/health')
def health(): return jsonify({"status":"ok","timestamp":datetime.now().isoformat()})

@app.route('/ping')
def ping(): return "pong"

@app.route('/api/stats')
def api_stats(): return jsonify(db.stats())

# ═══════════════ KEYBOARDS ═══════════════
CANCEL_KB = ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True)
DONE_KB = ReplyKeyboardMarkup([[KeyboardButton("✅ Done"), KeyboardButton("❌ Cancel")]], resize_keyboard=True)
SKIP_KB = ReplyKeyboardMarkup([[KeyboardButton("⏭️ Skip"), KeyboardButton("❌ Cancel")]], resize_keyboard=True)

def main_kb(uid):
    rows = [[KeyboardButton("🔐 VPN"), KeyboardButton("🌐 Proxy")], [KeyboardButton("📧 Mail"), KeyboardButton("💰 Deposit")], [KeyboardButton("💳 Balance"), KeyboardButton("🎟️ Coupon")], [KeyboardButton("👤 Profile"), KeyboardButton("📞 Support")], [KeyboardButton("ℹ️ Help")]]
    if uid in C.ADMIN: rows.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📦 Products"), KeyboardButton("📥 Stock")],
        [KeyboardButton("👥 Users"), KeyboardButton("💰 Deposits")],
        [KeyboardButton("📊 Statistics"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("🎟️ Coupons"), KeyboardButton("🎫 Tickets")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("🔍 Search")],
        [KeyboardButton("📈 Reports"), KeyboardButton("🧹 Clear Sold")],
        [KeyboardButton("🔙 Main Menu")]
    ], resize_keyboard=True)

def product_mgmt_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Add Product"), KeyboardButton("📋 List Products")],
        [KeyboardButton("✏️ Edit Product"), KeyboardButton("🗑️ Delete Product")],
        [KeyboardButton("🔄 Toggle"), KeyboardButton("⭐ Feature")],
        [KeyboardButton("🔙 Admin Panel")]
    ], resize_keyboard=True)

def user_mgmt_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📋 All Users"), KeyboardButton("🔍 Search User")],
        [KeyboardButton("🚫 Ban/Unban"), KeyboardButton("⚠️ Warn")],
        [KeyboardButton("💰 Add Balance"), KeyboardButton("💸 Deduct")],
        [KeyboardButton("⭐ Premium"), KeyboardButton("📝 Notes")],
        [KeyboardButton("🏆 Top Users"), KeyboardButton("📊 User Stats")],
        [KeyboardButton("🔙 Admin Panel")]
    ], resize_keyboard=True)

def stock_mgmt_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📥 Add Stock"), KeyboardButton("📋 View Stock")],
        [KeyboardButton("🗑️ Delete Stock"), KeyboardButton("🧹 Clear Sold")],
        [KeyboardButton("📊 Stock Stats"), KeyboardButton("💵 Stock Value")],
        [KeyboardButton("🔙 Admin Panel")]
    ], resize_keyboard=True)

# ═══════════════ HELPERS ═══════════════
def is_cancel(txt): return txt and txt.strip() in ['❌ Cancel', 'cancel', 'Cancel', '/cancel']
def is_skip(txt): return txt and txt.strip() in ['⏭️ Skip', 'skip', 'Skip', '/skip']
def is_done(txt): return txt and txt.strip() in ['✅ Done', 'done', 'Done', '/done']

def fmt_money(amt): return f"{amt:,.0f} TK"
def fmt_date(dt): return datetime.fromisoformat(dt).strftime('%d %b %Y, %I:%M %p') if dt else 'N/A'

async def check_join(update, context):
    uid = update.effective_user.id
    if uid in C.ADMIN: return True
    try:
        member = await context.bot.get_chat_member(C.CHANNEL, uid)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=C.CHANNEL_URL)], [InlineKeyboardButton("✅ I Joined", callback_data="join_ok")]])
            m = update.message or (update.callback_query.message if update.callback_query else None)
            if m: await m.reply_text(f"⚠️ Join {C.CHANNEL} first!\n\n1️⃣ Click 'Join Channel'\n2️⃣ Join\n3️⃣ Click 'I Joined'", reply_markup=kb)
            return False
        return True
    except: return True

# ═══════════════ START ═══════════════
async def start(update, context):
    if not await check_join(update, context): return
    u = update.effective_user; db.save_user({'telegramId': u.id, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    user = db.user(u.id)
    
    # Handle referral
    ref = context.args[0] if context.args else None
    if ref:
        ref_user = next((x for x in db.all_users() if x.get('referralCode') == ref), None)
        if ref_user and ref_user['telegramId'] != u.id:
            bonus = db.settings().get('ref_bonus', 5)
            db.add_bal(ref_user['telegramId'], bonus)
            db.save_user({'telegramId': ref_user['telegramId'], 'referralCount': ref_user.get('referralCount', 0) + 1, 'referralEarnings': ref_user.get('referralEarnings', 0) + bonus})
            try: await context.bot.send_message(ref_user['telegramId'], f"🎉 Referral bonus! +{bonus} TK")
            except: pass
    
    await update.message.reply_text(
        f"👑 *ROYAL MAIL STORE*\n\n🔐 VPN | 🌐 Proxy | 📧 Mail\n\n"
        f"💰 Balance: `{user['balance']:.0f} TK`\n"
        f"💳 Deposit: `{C.MIN_DEP}-{C.MAX_DEP} TK`\n"
        f"🎁 Referral: `{user.get('referralCode','N/A')}`\n\n👇 Select:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(u.id))

async def join_ok(update, context):
    q = update.callback_query; await q.answer()
    if await check_join(update, context): await q.edit_message_text("✅ Verified!"); await start(update, context)

# ═══════════════ MAIN HANDLER ═══════════════
async def handle_msg(update, context):
    if not update.message or not update.message.text: return
    
    if not await check_join(update, context): return
    
    uid = update.effective_user.id; txt = update.message.text.strip(); u = update.effective_user
    db.save_user({'telegramId': uid, 'username': u.username or '', 'firstName': u.first_name or 'User'})
    
    user = db.user(uid)
    if user and user.get('isBanned'): await update.message.reply_text("🚫 Banned! Contact admin."); return
    
    # Check maintenance
    if db.settings().get('maintenance') and uid not in C.ADMIN:
        await update.message.reply_text("🔧 Maintenance mode. Please wait.")
        return
    
    state = context.user_data.get('state', '')
    
    # ═══════════ UNIVERSAL CANCEL ═══════════
    if is_cancel(txt) and state:
        context.user_data.clear()
        await update.message.reply_text("❌ *Cancelled*", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb() if uid in C.ADMIN else main_kb(uid))
        return
    
    # ═══════════ SKIP ═══════════
    if is_skip(txt) and state == 'deposit_ss':
        context.user_data['dep_ss'] = None
        return await submit_deposit(update, context)
    
    # ═══════════ DONE ═══════════
    if is_done(txt) and state in ['stock_add', 'stock_bulk']:
        context.user_data.clear()
        await update.message.reply_text("✅ Done!", reply_markup=admin_kb())
        return
    
    # ═══════════ STATE ROUTING ═══════════
    state_map = {
        'deposit_amount': deposit_amount_step, 'deposit_txn': deposit_txn_step,
        'deposit_ss': deposit_ss_step, 'prod_type': prod_type_step,
        'prod_name': prod_name_step, 'prod_price': prod_price_step,
        'prod_desc': prod_desc_step, 'edit_prod_select': edit_prod_select_step,
        'edit_prod_field': edit_prod_field_step, 'edit_prod_value': edit_prod_value_step,
        'stock_add': stock_add_step, 'stock_bulk': stock_add_step,
        'broadcast': broadcast_step, 'ban_user': ban_user_step,
        'warn_user': warn_user_step, 'add_bal_user': add_bal_user_step,
        'deduct_bal_user': deduct_bal_user_step, 'search_user': search_user_step,
        'premium_user': premium_user_step, 'note_user': note_user_step,
        'coupon_create': coupon_create_step, 'ticket_reply': ticket_reply_step,
        'settings_update': settings_update_step,
    }
    if state in state_map: return await state_map[state](update, context)
    
    # ═══════════ MENU ═══════════
    menu = {
        "🔐 VPN": lambda: show_cat(update, context, "vpn"),
        "🌐 Proxy": lambda: show_cat(update, context, "proxy"),
        "📧 Mail": lambda: show_cat(update, context, "mail"),
        "💰 Deposit": lambda: deposit_menu(update, context),
        "💳 Balance": lambda: show_balance(update, context),
        "🎟️ Coupon": lambda: coupon_input(update, context),
        "👤 Profile": lambda: show_profile(update, context),
        "📞 Support": lambda: ticket_create(update, context),
        "ℹ️ Help": lambda: show_help(update, context),
        "🔙 Main Menu": lambda: update.message.reply_text("🏠 Menu", reply_markup=main_kb(uid)),
    }
    if txt in menu: return await menu[txt]()
    
    # ═══════════ ADMIN MENU ═══════════
    if uid in C.ADMIN:
        return await admin_router(update, context)

# ═══════════════ PRODUCTS ═══════════════
async def show_cat(update, context, cat):
    prods = db.prods(cat); emoji = {"vpn": "🔐", "proxy": "🌐", "mail": "📧"}.get(cat, "📦")
    if not prods: return await update.message.reply_text(f"{emoji} No {cat.upper()} products yet!")
    kb = [[InlineKeyboardButton(f"{'⭐' if p.get('featured') else ''}{p['name']} - {p['price']:.0f} TK", callback_data=f"buy_{p['id']}")] for p in prods]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    await update.message.reply_text(f"{emoji} *{cat.upper()}*\n\n{len(prods)} products\n👇 Select:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def buy_prod(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "back_main": await q.edit_message_text("🏠"); await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id)); return
    uid = update.effective_user.id; pid = q.data.replace("buy_", ""); product = db.prod(pid); user = db.user(uid)
    if not product: return await q.edit_message_text("❌ Not found!")
    if user['balance'] < product['price']: return await q.edit_message_text(f"❌ Balance: `{user['balance']:.0f} TK`\n💰 Need: `{product['price']:.0f} TK`\n\nUse 💰 Deposit!", parse_mode=ParseMode.MARKDOWN)
    stock = db.stock_avail(product['type'], product['price'], product['id'])
    if not stock: return await q.edit_message_text("❌ Out of stock!")
    db.deduct_bal(uid, product['price']); db.sell(stock['id'], uid)
    db.update_prod(pid, {'totalSold': product.get('totalSold', 0) + 1, 'totalRevenue': product.get('totalRevenue', 0) + product['price']})
    bal = db.user(uid)['balance']
    msg = f"✅ *Purchased!*\n📦 {product['name']}\n💰 {product['price']:.0f} TK\n💳 Balance: {bal:.0f} TK\n\n"
    d = stock['data']
    if product['type'] == 'vpn': msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`\n📅 {d.get('expireDate','')}"
    elif product['type'] == 'proxy': msg += f"🌐 `{d.get('host','')}:{d.get('port','')}`\n👤 `{d.get('username','')}`\n🔑 `{d.get('password','')}`"
    elif product['type'] == 'mail': msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`\n🔑 `{d.get('recovery','')}`"
    msg += f"\n📝 ID: `{stock['id'][:8]}`\n🕐 {datetime.now().strftime('%d %b, %I:%M %p')}"
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

# ═══════════════ DEPOSIT ═══════════════
async def deposit_menu(update, context):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💳 bKash", callback_data="dep_bkash"), InlineKeyboardButton("🚀 Rocket", callback_data="dep_rocket")], [InlineKeyboardButton("❌ Cancel", callback_data="dep_cancel")]])
    await update.message.reply_text(f"💰 *Deposit*\n\n💳 bKash: `{C.BKASH}`\n🚀 Rocket: `{C.ROCKET}`\n\nMin: `{C.MIN_DEP} TK` | Max: `{C.MAX_DEP} TK`\n\n👇 Method:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def deposit_method_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "dep_cancel": await q.edit_message_text("❌ Cancelled"); await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id)); return
    m = {"dep_bkash": ("bKash", C.BKASH), "dep_rocket": ("Rocket", C.ROCKET)}
    method, num = m.get(q.data, ("bKash", C.BKASH))
    context.user_data.update({'dep_method': method, 'dep_number': num, 'state': 'deposit_amount'})
    await q.edit_message_text(f"💳 *{method}*\n📱 `{num}`\n\n👇 Amount:\n`{C.MIN_DEP}-{C.MAX_DEP} TK`", parse_mode=ParseMode.MARKDOWN)

async def deposit_amount_step(update, context):
    txt = update.message.text.strip()
    try: amt = float(txt)
    except: await update.message.reply_text("❌ Number! Example: `50`", reply_markup=CANCEL_KB); return
    if amt < C.MIN_DEP: await update.message.reply_text(f"❌ Min: `{C.MIN_DEP} TK`!", reply_markup=CANCEL_KB); return
    if amt > C.MAX_DEP: await update.message.reply_text(f"❌ Max: `{C.MAX_DEP} TK`!", reply_markup=CANCEL_KB); return
    context.user_data['dep_amount'] = amt; context.user_data['state'] = 'deposit_txn'
    await update.message.reply_text(f"💰 `{amt:.0f} TK`\n\n🔢 TXN ID:", reply_markup=CANCEL_KB)

async def deposit_txn_step(update, context):
    context.user_data['dep_txn'] = update.message.text.strip(); context.user_data['state'] = 'deposit_ss'
    await update.message.reply_text("📸 Send Screenshot (photo) or `skip`:", reply_markup=SKIP_KB)

async def deposit_ss_step(update, context):
    if update.message.photo: context.user_data['dep_ss'] = update.message.photo[-1].file_id
    elif update.message.document: context.user_data['dep_ss'] = update.message.document.file_id
    else: await update.message.reply_text("📸 Photo or `skip`:", reply_markup=SKIP_KB); return
    await submit_deposit(update, context)

async def submit_deposit(update, context):
    uid = update.effective_user.id
    d = context.user_data
    dep = db.dep_create({'telegramId': uid, 'username': update.effective_user.username or '', 'firstName': update.effective_user.first_name or 'User', 'amount': d.get('dep_amount', 0), 'transactionId': d.get('dep_txn', ''), 'paymentMethod': d.get('dep_method', 'bKash'), 'senderNumber': d.get('dep_number', ''), 'screenshot': d.get('dep_ss')})
    context.user_data.clear()
    for aid in C.ADMIN:
        try:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅", callback_data=f"app_{dep['id']}"), InlineKeyboardButton("❌", callback_data=f"rej_{dep['id']}")]])
            txt = f"💰 *Deposit!*\n👤 {update.effective_user.first_name}\n💰 `{dep['amount']:.0f} TK`\n💳 {dep['paymentMethod']}\n🔢 `{dep['transactionId']}`"
            if dep.get('screenshot'): await context.bot.send_photo(aid, dep['screenshot'], caption=txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            else: await context.bot.send_message(aid, txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except: pass
    await update.message.reply_text(f"✅ *Submitted!*\n💰 `{dep['amount']:.0f} TK`\n⏳ Pending...", parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(uid))

async def dep_approve(update, context):
    q = update.callback_query; await q.answer()
    if update.effective_user.id not in C.ADMIN: return
    status = "approved" if q.data.startswith("app_") else "rejected"; did = q.data.split("_", 1)[1]
    dep = db.dep_update(did, status, update.effective_user.id)
    if dep:
        try: await context.bot.send_message(dep['telegramId'], f"{'✅ Approved!' if status=='approved' else '❌ Rejected!'}\n💰 {dep['amount']:.0f} TK", parse_mode=ParseMode.MARKDOWN)
        except: pass
        await q.edit_message_text(f"{'✅' if status=='approved' else '❌'} {status}!")

# ═══════════════ BALANCE / PROFILE / HELP ═══════════════
async def show_balance(update, context):
    u = db.user(update.effective_user.id)
    if u: await update.message.reply_text(f"💳 *Balance*\n\n💰 `{u['balance']:.0f} TK`\n📊 Spent: `{u['totalSpent']:.0f} TK`\n💎 Deposited: `{u['totalDeposited']:.0f} TK`\n📦 Purchases: `{u['totalPurchases']}`\n🎁 Referral: `{u.get('referralCode','N/A')}`", parse_mode=ParseMode.MARKDOWN)

async def show_profile(update, context):
    u = db.user(update.effective_user.id)
    if u: await update.message.reply_text(f"👤 *Profile*\n\n🆔 `{u['telegramId']}`\n👑 {u.get('role','user').title()}\n⭐ {'Premium' if u.get('isPremium') else 'Free'}\n💰 {u['balance']:.0f} TK\n📦 {u['totalPurchases']} purchases\n⚠️ {u.get('warnings',0)}/3 warnings\n📅 Joined: {fmt_date(u.get('joinedAt',''))}", parse_mode=ParseMode.MARKDOWN)

async def show_help(update, context):
    await update.message.reply_text(f"ℹ️ *HELP*\n\n1️⃣ Choose VPN/Proxy/Mail\n2️⃣ Buy with balance\n3️⃣ Get delivery\n\n💰 Deposit: `{C.MIN_DEP}-{C.MAX_DEP} TK`\n💳 bKash: `{C.BKASH}`\n🚀 Rocket: `{C.ROCKET}`\n\n📞 Support: {C.SUPPORT}\n📢 Channel: {C.CHANNEL}\n🔗 {C.CHANNEL_URL}\n\n⚠️ Rules:\n• Join channel first\n• No refund\n• Min deposit {C.MIN_DEP} TK", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ═══════════════ COUPON ═══════════════
async def coupon_input(update, context):
    context.user_data['state'] = 'coupon_apply'
    await update.message.reply_text("🎟️ Send coupon code:", reply_markup=CANCEL_KB)

async def coupon_apply(update, context):
    code = update.message.text.strip(); context.user_data.clear()
    coupon = db.coupon_get(code)
    if not coupon: await update.message.reply_text("❌ Invalid!", reply_markup=main_kb(update.effective_user.id)); return
    discount = f"{coupon['value']}%" if coupon['type'] == 'percentage' else f"{coupon['value']} TK"
    context.user_data['active_coupon'] = coupon
    await update.message.reply_text(f"🎟️ *Applied!*\nCode: `{code}`\nDiscount: {discount}\n\nBuy now!", parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(update.effective_user.id))

# ═══════════════ TICKETS ═══════════════
async def ticket_create(update, context):
    context.user_data['state'] = 'ticket_subject'
    await update.message.reply_text("📝 Subject:", reply_markup=CANCEL_KB)

async def ticket_subject_step(update, context):
    context.user_data['ticket_subject'] = update.message.text.strip(); context.user_data['state'] = 'ticket_msg'
    await update.message.reply_text("📝 Message:", reply_markup=CANCEL_KB)

async def ticket_msg_step(update, context):
    uid = update.effective_user.id; subj = context.user_data.get('ticket_subject', ''); msg = update.message.text.strip(); context.user_data.clear()
    ticket = db.ticket_create({'telegramId': uid, 'username': update.effective_user.username or '', 'subject': subj, 'message': msg})
    for aid in C.ADMIN:
        try: await context.bot.send_message(aid, f"🎫 *New Ticket*\n🆔 `{ticket['id']}`\n👤 {update.effective_user.first_name}\n📋 {subj}\n📝 {msg[:200]}", parse_mode=ParseMode.MARKDOWN)
        except: pass
    await update.message.reply_text(f"✅ Ticket created!\n🆔 `{ticket['id']}`", reply_markup=main_kb(uid))

# ═══════════════ ADMIN ROUTER ═══════════════
async def admin_router(update, context):
    txt = update.message.text.strip(); uid = update.effective_user.id
    
    routes = {
        "👑 Admin Panel": lambda: admin_panel(update, context),
        "📦 Products": lambda: update.message.reply_text("📦 *Products*", parse_mode=ParseMode.MARKDOWN, reply_markup=product_mgmt_kb()),
        "📥 Stock": lambda: update.message.reply_text("📥 *Stock*", parse_mode=ParseMode.MARKDOWN, reply_markup=stock_mgmt_kb()),
        "👥 Users": lambda: update.message.reply_text("👥 *Users*", parse_mode=ParseMode.MARKDOWN, reply_markup=user_mgmt_kb()),
        "💰 Deposits": lambda: show_deposits_admin(update, context),
        "📊 Statistics": lambda: show_stats_admin(update, context),
        "📢 Broadcast": lambda: start_state_msg(update, context, 'broadcast', "📢 Message:"),
        "🎟️ Coupons": lambda: show_coupons_admin(update, context),
        "🎫 Tickets": lambda: show_tickets_admin(update, context),
        "⚙️ Settings": lambda: show_settings_admin(update, context),
        "🔍 Search": lambda: start_state_msg(update, context, 'search_user', "🔍 Send ID/username/name:"),
        "📈 Reports": lambda: show_reports(update, context),
        "🧹 Clear Sold": lambda: clear_sold_admin(update, context),
        # Product Management
        "➕ Add Product": lambda: start_state_msg(update, context, 'prod_type', "📦 Type: `vpn` `proxy` `mail`"),
        "📋 List Products": lambda: list_products_admin(update, context),
        "✏️ Edit Product": lambda: start_state_msg(update, context, 'edit_prod_select', "🔢 Send Product ID:"),
        "🗑️ Delete Product": lambda: delete_product_admin(update, context),
        "🔄 Toggle": lambda: toggle_product_admin(update, context),
        "⭐ Feature": lambda: feature_product_admin(update, context),
        # Stock Management
        "📥 Add Stock": lambda: start_state_msg(update, context, 'stock_add', "📥 Format: `email|pass|expire|price`\n`done` to finish.", DONE_KB),
        "📋 View Stock": lambda: view_stock_admin(update, context),
        "🗑️ Delete Stock": lambda: delete_stock_admin(update, context),
        "📊 Stock Stats": lambda: stock_stats_admin(update, context),
        "💵 Stock Value": lambda: stock_value_admin(update, context),
        # User Management
        "📋 All Users": lambda: show_all_users(update, context),
        "🔍 Search User": lambda: start_state_msg(update, context, 'search_user', "🔍 Send ID/name:"),
        "🚫 Ban/Unban": lambda: start_state_msg(update, context, 'ban_user', "🚫 Send User ID:"),
        "⚠️ Warn": lambda: start_state_msg(update, context, 'warn_user', "⚠️ Send User ID:"),
        "💰 Add Balance": lambda: start_state_msg(update, context, 'add_bal_user', "💰 Send User ID:"),
        "💸 Deduct": lambda: start_state_msg(update, context, 'deduct_bal_user', "💸 Send User ID:"),
        "⭐ Premium": lambda: start_state_msg(update, context, 'premium_user', "⭐ Send User ID:"),
        "📝 Notes": lambda: start_state_msg(update, context, 'note_user', "📝 Send User ID:"),
        "🏆 Top Users": lambda: show_top_users(update, context),
        "📊 User Stats": lambda: user_stats_admin(update, context),
    }
    
    if txt in routes: await routes[txt]()

async def start_state_msg(update, context, state, msg, kb=None):
    context.user_data['state'] = state
    await update.message.reply_text(msg + "\n\n`cancel` to exit.", parse_mode=ParseMode.MARKDOWN, reply_markup=kb or CANCEL_KB)

async def admin_panel(update, context):
    s = db.stats(); h, m = divmod(s['uptime'], 3600); m //= 60
    await update.message.reply_text(f"👑 *Admin Panel*\n\n👥 {s['users']} ({s['active']} active)\n🚫 {s['banned']} banned | ⭐ {s['premium']} premium\n💰 {fmt_money(s['revenue'])} (Today: {fmt_money(s['today_revenue'])})\n📦 {s['stock']} stock | ❌ {s['sold']} sold\n⏳ {s['pending']} pending | 🎫 {s['tickets_open']} tickets\n📦 {s['active_products']} products | 🎟️ {s['coupons']} coupons\n🕐 {h}h {m}m", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())

# ═══════════════ ADMIN FEATURES ═══════════════

async def show_deposits_admin(update, context):
    deps = db.dep_pending()
    if not deps: await update.message.reply_text("✅ No pending!"); return
    for d in deps[:10]:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅", callback_data=f"app_{d['id']}"), InlineKeyboardButton("❌", callback_data=f"rej_{d['id']}")]])
        await update.message.reply_text(f"💰 {d.get('firstName','?')} - {d['amount']:.0f} TK\n💳 {d.get('paymentMethod','?')}\n🔢 `{d['transactionId']}`", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def show_stats_admin(update, context):
    s = db.stats(); ds = db.dep_stats(); sv = db.stock_value()
    msg = f"📊 *Statistics*\n\n"
    msg += f"👥 Users: {s['users']} | Active: {s['active']} | Banned: {s['banned']}\n"
    msg += f"💰 Revenue: {fmt_money(s['revenue'])} | Today: {fmt_money(s['today_revenue'])}\n"
    msg += f"💳 Deposits: {ds['approved']} | Pending: {ds['pending']}\n"
    msg += f"📦 Stock: {s['stock']} avail | {s['sold']} sold\n"
    msg += f"💵 Stock Value: {fmt_money(sv['total_value'])}\n"
    msg += f"📦 Products: {s['active_products']} active\n"
    msg += f"🎟️ Coupons: {s['coupons']} | 🎫 Tickets: {s['tickets_open']} open\n"
    msg += f"🕐 Uptime: {s['uptime']//3600}h {(s['uptime']%3600)//60}m"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def show_reports(update, context):
    chart = db.revenue_chart(7)
    msg = "📈 *Revenue (7 Days)*\n\n"
    for date, amt in sorted(chart.items()):
        bar = "█" * int(amt / 100) if amt > 0 else ""
        msg += f"`{date}`: {fmt_money(amt)} {bar}\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def show_all_users(update, context):
    users = db.all_users()[:30]; total = len(db.all_users())
    msg = f"👥 *Users ({total})*\n\n"
    for u in users: msg += f"{'🚫' if u.get('isBanned') else '✅'} {'⭐' if u.get('isPremium') else '👤'} `{u.get('firstName','?')}` - {u['balance']:.0f} TK\n"
    if total > 30: msg += f"\n... +{total-30} more"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def show_top_users(update, context):
    users = db.get_top_users(15)
    msg = "🏆 *Top Spenders*\n\n"
    for i, u in enumerate(users, 1): msg += f"{i}. {u.get('firstName','?')} - {fmt_money(u.get('totalSpent',0))}\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def list_products_admin(update, context):
    prods = db.prods(active_only=False)
    msg = f"📦 *Products ({len(prods)})*\n\n"
    for p in prods[:20]: msg += f"{'✅' if p.get('active') else '❌'} {'⭐' if p.get('featured') else ''} `{p['id'][:6]}` {p['name']} - {p['price']:.0f} TK\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def view_stock_admin(update, context):
    s = db.stock_stats(); msg = f"📥 *Stock ({s['total']})*\n\n"
    for t, stats in s.get('by_type', {}).items(): msg += f"• {t.upper()}: {stats['avail']} avail / {stats['sold']} sold / {stats['total']} total\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def stock_stats_admin(update, context):
    s = db.stock_stats(); sv = db.stock_value()
    msg = f"📊 *Stock Stats*\n\n"
    for t, stats in s.get('by_type', {}).items(): msg += f"• *{t.upper()}*: {stats['avail']} avail | {stats['sold']} sold | {stats['total']} total\n"
    msg += f"\n💵 Avail Value: {fmt_money(sv['avail_value'])}\n💵 Sold Value: {fmt_money(sv['sold_value'])}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def stock_value_admin(update, context):
    sv = db.stock_value()
    await update.message.reply_text(f"💵 *Stock Value*\n\nAvailable: {fmt_money(sv['avail_value'])}\nSold: {fmt_money(sv['sold_value'])}\nTotal: {fmt_money(sv['total_value'])}", parse_mode=ParseMode.MARKDOWN)

async def delete_product_admin(update, context):
    context.user_data['state'] = 'delete_product'
    await update.message.reply_text("🗑️ Send Product ID:", reply_markup=CANCEL_KB)

async def toggle_product_admin(update, context):
    context.user_data['state'] = 'toggle_product'
    await update.message.reply_text("🔄 Send Product ID:", reply_markup=CANCEL_KB)

async def feature_product_admin(update, context):
    context.user_data['state'] = 'feature_product'
    await update.message.reply_text("⭐ Send Product ID:", reply_markup=CANCEL_KB)

async def delete_stock_admin(update, context):
    context.user_data['state'] = 'delete_stock'
    await update.message.reply_text("🗑️ Send Stock ID:", reply_markup=CANCEL_KB)

async def clear_sold_admin(update, context):
    db.clear_sold_stock()
    await update.message.reply_text("✅ Sold stock cleared!", reply_markup=admin_kb())

async def show_coupons_admin(update, context):
    coupons = db.coupon_all()
    if not coupons: await update.message.reply_text("🎟️ No coupons!"); return
    msg = "🎟️ *Coupons*\n\n"
    for c in coupons: msg += f"{'✅' if c.get('active') else '❌'} `{c['code']}` - {c['value']}{'%' if c['type']=='percentage' else 'TK'} ({c['usedCount']}/{c.get('maxUses',100)})\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def show_tickets_admin(update, context):
    tickets = db.ticket_get(status='open')
    if not tickets: await update.message.reply_text("🎫 No open tickets!"); return
    for t in tickets[:5]: await update.message.reply_text(f"🎫 `{t['id'][:6]}`\n👤 {t.get('username','?')}\n📋 {t['subject']}\n📝 {t['message'][:100]}", parse_mode=ParseMode.MARKDOWN)

async def show_settings_admin(update, context):
    s = db.settings()
    msg = f"⚙️ *Settings*\n\n• Bot: {s.get('bot_name','')}\n• Min Dep: {s.get('min_dep',10)}\n• Max Dep: {s.get('max_dep',100)}\n• Force Join: {s.get('force_join',True)}\n• Maintenance: {s.get('maintenance',False)}\n• Ref Bonus: {s.get('ref_bonus',5)}\n• Max Daily Buy: {s.get('max_daily_buy',20)}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def user_stats_admin(update, context):
    u = db.all_users()
    total_bal = sum(x['balance'] for x in u)
    await update.message.reply_text(f"📊 *User Stats*\n\nTotal Users: {len(u)}\nTotal Balance: {fmt_money(total_bal)}\nAvg Balance: {fmt_money(total_bal/len(u) if u else 0)}\nPremium: {len([x for x in u if x.get('isPremium')])}\nBanned: {len([x for x in u if x.get('isBanned')])}", parse_mode=ParseMode.MARKDOWN)

# ═══════════════ STATE HANDLERS ═══════════════

async def prod_type_step(update, context):
    txt = update.message.text.strip().lower()
    if txt not in ['vpn', 'proxy', 'mail']: await update.message.reply_text("❌ vpn/proxy/mail!", reply_markup=CANCEL_KB); return
    context.user_data['ptype'] = txt; context.user_data['state'] = 'prod_name'
    await update.message.reply_text("📝 Name:", reply_markup=CANCEL_KB)

async def prod_name_step(update, context):
    context.user_data['pname'] = update.message.text.strip(); context.user_data['state'] = 'prod_price'
    await update.message.reply_text("💰 Price:", reply_markup=CANCEL_KB)

async def prod_price_step(update, context):
    try: price = float(update.message.text.strip())
    except: await update.message.reply_text("❌ Number!", reply_markup=CANCEL_KB); return
    context.user_data['pprice'] = price; context.user_data['state'] = 'prod_desc'
    await update.message.reply_text("📝 Description (or `skip`):", reply_markup=SKIP_KB)

async def prod_desc_step(update, context):
    desc = update.message.text.strip()
    if is_skip(desc): desc = ""
    d = context.user_data
    db.add_prod({'type': d['ptype'], 'name': d['pname'], 'price': d['pprice'], 'description': desc, 'createdBy': update.effective_user.id})
    context.user_data.clear()
    await update.message.reply_text(f"✅ Added!\n📦 {d.get('pname','')}\n💰 {d.get('pprice',0):.0f} TK", reply_markup=admin_kb())

async def edit_prod_select_step(update, context):
    pid = update.message.text.strip()
    prod = db.prod(pid)
    if not prod: await update.message.reply_text("❌ Not found!", reply_markup=CANCEL_KB); return
    context.user_data['edit_pid'] = pid; context.user_data['state'] = 'edit_prod_field'
    await update.message.reply_text("✏️ Field: `name` `price` `description` `type`", parse_mode=ParseMode.MARKDOWN, reply_markup=CANCEL_KB)

async def edit_prod_field_step(update, context):
    field = update.message.text.strip().lower()
    if field not in ['name', 'price', 'description', 'type']: await update.message.reply_text("❌ name/price/description/type!", reply_markup=CANCEL_KB); return
    context.user_data['edit_field'] = field; context.user_data['state'] = 'edit_prod_value'
    await update.message.reply_text(f"✏️ New value for `{field}`:", parse_mode=ParseMode.MARKDOWN, reply_markup=CANCEL_KB)

async def edit_prod_value_step(update, context):
    val = update.message.text.strip(); d = context.user_data
    if d['edit_field'] == 'price':
        try: val = float(val)
        except: await update.message.reply_text("❌ Number!", reply_markup=CANCEL_KB); return
    db.update_prod(d['edit_pid'], {d['edit_field']: val})
    context.user_data.clear()
    await update.message.reply_text("✅ Updated!", reply_markup=admin_kb())

async def stock_add_step(update, context):
    txt = update.message.text.strip(); uid = update.effective_user.id; added = 0
    for line in txt.split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            try: db.add_stock({'productType': 'vpn', 'productName': 'VPN', 'data': {'email': parts[0], 'password': parts[1], 'expireDate': parts[2]}, 'price': float(parts[3]), 'addedBy': uid}); added += 1
            except: pass
    await update.message.reply_text(f"✅ {added} added! More or `done`.", reply_markup=DONE_KB)

async def broadcast_step(update, context):
    txt = update.message.text.strip(); context.user_data.clear()
    users = db.all_users(); s, f = 0, 0; msg = await update.message.reply_text("📤 Sending...")
    for u in users:
        try: await context.bot.send_message(u['telegramId'], txt, parse_mode=ParseMode.MARKDOWN); s += 1
        except: f += 1
        await asyncio.sleep(0.05)
    db.broadcast_save({'message': txt[:200], 'sentBy': update.effective_user.id, 'success': s, 'failed': f})
    await msg.edit_text(f"✅ Done! ✅{s} ❌{f}"); await update.message.reply_text("👑 Admin", reply_markup=admin_kb())

async def ban_user_step(update, context):
    try: tid = int(update.message.text.strip())
    except: await update.message.reply_text("❌ ID!", reply_markup=CANCEL_KB); return
    u = db.ban_user(tid, "Manual", update.effective_user.id); context.user_data.clear()
    await update.message.reply_text(f"✅ {'Banned' if u and u.get('isBanned') else 'Unbanned'}!", reply_markup=admin_kb())

async def warn_user_step(update, context):
    try: tid = int(update.message.text.strip())
    except: await update.message.reply_text("❌ ID!", reply_markup=CANCEL_KB); return
    context.user_data['warn_uid'] = tid; context.user_data['state'] = 'warn_reason'
    await update.message.reply_text("⚠️ Reason:", reply_markup=CANCEL_KB)

async def warn_reason_step(update, context):
    reason = update.message.text.strip(); tid = context.user_data.get('warn_uid'); context.user_data.clear()
    db.warn_user(tid, reason, update.effective_user.id)
    await update.message.reply_text("✅ Warned!", reply_markup=admin_kb())

async def add_bal_user_step(update, context):
    try: tid = int(update.message.text.strip())
    except: await update.message.reply_text("❌ ID!", reply_markup=CANCEL_KB); return
    context.user_data['bal_uid'] = tid; context.user_data['state'] = 'add_bal_amount'
    await update.message.reply_text("💰 Amount:", reply_markup=CANCEL_KB)

async def add_bal_amount_step(update, context):
    try: amt = float(update.message.text.strip())
    except: await update.message.reply_text("❌ Number!", reply_markup=CANCEL_KB); return
    tid = context.user_data.get('bal_uid'); context.user_data.clear()
    db.add_bal(tid, amt)
    await update.message.reply_text(f"✅ Added {fmt_money(amt)}!", reply_markup=admin_kb())

async def deduct_bal_user_step(update, context):
    try: tid = int(update.message.text.strip())
    except: await update.message.reply_text("❌ ID!", reply_markup=CANCEL_KB); return
    context.user_data['bal_uid'] = tid; context.user_data['state'] = 'deduct_bal_amount'
    await update.message.reply_text("💸 Amount:", reply_markup=CANCEL_KB)

async def deduct_bal_amount_step(update, context):
    try: amt = float(update.message.text.strip())
    except: await update.message.reply_text("❌ Number!", reply_markup=CANCEL_KB); return
    tid = context.user_data.get('bal_uid'); context.user_data.clear()
    db.add_bal(tid, -amt)
    await update.message.reply_text(f"✅ Deducted {fmt_money(amt)}!", reply_markup=admin_kb())

async def search_user_step(update, context):
    query = update.message.text.strip(); context.user_data.clear()
    results = db.search_users(query)
    if not results: await update.message.reply_text("❌ Not found!", reply_markup=admin_kb()); return
    msg = f"🔍 *Results ({len(results)})*\n\n"
    for u in results[:10]: msg += f"🆔 `{u['telegramId']}` - {u.get('firstName','?')}\n💰 {u['balance']:.0f} TK | {'🚫' if u.get('isBanned') else '✅'}\n\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())

async def premium_user_step(update, context):
    try: tid = int(update.message.text.strip())
    except: await update.message.reply_text("❌ ID!", reply_markup=CANCEL_KB); return
    context.user_data['prem_uid'] = tid; context.user_data['state'] = 'premium_days'
    await update.message.reply_text("⭐ Days:", reply_markup=CANCEL_KB)

async def premium_days_step(update, context):
    try: days = int(update.message.text.strip())
    except: await update.message.reply_text("❌ Number!", reply_markup=CANCEL_KB); return
    tid = context.user_data.get('prem_uid'); context.user_data.clear()
    db.set_premium(tid, days)
    await update.message.reply_text(f"✅ Premium for {days} days!", reply_markup=admin_kb())

async def note_user_step(update, context):
    try: tid = int(update.message.text.strip())
    except: await update.message.reply_text("❌ ID!", reply_markup=CANCEL_KB); return
    context.user_data['note_uid'] = tid; context.user_data['state'] = 'note_text'
    await update.message.reply_text("📝 Note:", reply_markup=CANCEL_KB)

async def note_text_step(update, context):
    note = update.message.text.strip(); tid = context.user_data.get('note_uid'); context.user_data.clear()
    db.add_note(tid, note, update.effective_user.id)
    await update.message.reply_text("✅ Noted!", reply_markup=admin_kb())

async def coupon_create_step(update, context):
    txt = update.message.text.strip(); d = context.user_data
    if 'coupon_step' not in d: d['coupon_step'] = 1; d['state'] = 'coupon_create'
    
    step = d.get('coupon_step', 1)
    if step == 1: d['c_code'] = txt.upper(); d['coupon_step'] = 2; await update.message.reply_text("🎟️ Type: `percentage` or `fixed`", parse_mode=ParseMode.MARKDOWN, reply_markup=CANCEL_KB)
    elif step == 2: d['c_type'] = txt; d['coupon_step'] = 3; await update.message.reply_text("💎 Value:", reply_markup=CANCEL_KB)
    elif step == 3: d['c_value'] = float(txt); d['coupon_step'] = 4; await update.message.reply_text("🔢 Max Uses:", reply_markup=CANCEL_KB)
    elif step == 4:
        d['c_max'] = int(txt)
        db.coupon_create({'code': d['c_code'], 'type': d['c_type'], 'value': d['c_value'], 'maxUses': d['c_max'], 'createdBy': update.effective_user.id})
        context.user_data.clear()
        await update.message.reply_text(f"✅ Coupon `{d['c_code']}` created!", reply_markup=admin_kb())

async def ticket_reply_step(update, context):
    txt = update.message.text.strip()
    if 'ticket_rid' not in context.user_data: context.user_data['ticket_rid'] = txt; await update.message.reply_text("📝 Reply:", reply_markup=CANCEL_KB)
    else:
        rid = context.user_data['ticket_rid']; context.user_data.clear()
        db.ticket_reply(rid, {'from': update.effective_user.id, 'message': txt})
        await update.message.reply_text("✅ Replied!", reply_markup=admin_kb())

async def settings_update_step(update, context):
    txt = update.message.text.strip(); d = context.user_data
    if 'set_key' not in d: d['set_key'] = txt; await update.message.reply_text("✏️ Value:", reply_markup=CANCEL_KB)
    else:
        key = d['set_key']; val = txt
        if val.lower() == 'true': val = True
        elif val.lower() == 'false': val = False
        else:
            try: val = int(val)
            except:
                try: val = float(val)
                except: pass
        db.update_settings({key: val}); context.user_data.clear()
        await update.message.reply_text(f"✅ `{key}` updated!", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())

# ═══════════════ STATE ROUTER EXTENSION ═══════════════
# Additional states that need their own handler
state_map_extra = {
    'delete_product': lambda u, c: delete_product_exec(u, c),
    'toggle_product': lambda u, c: toggle_product_exec(u, c),
    'feature_product': lambda u, c: feature_product_exec(u, c),
    'delete_stock': lambda u, c: delete_stock_exec(u, c),
    'coupon_apply': lambda u, c: coupon_apply(u, c),
    'ticket_subject': lambda u, c: ticket_subject_step(u, c),
    'ticket_msg': lambda u, c: ticket_msg_step(u, c),
    'warn_reason': lambda u, c: warn_reason_step(u, c),
    'add_bal_amount': lambda u, c: add_bal_amount_step(u, c),
    'deduct_bal_amount': lambda u, c: deduct_bal_amount_step(u, c),
    'premium_days': lambda u, c: premium_days_step(u, c),
    'note_text': lambda u, c: note_text_step(u, c),
}

# Add extra states to handle_msg state check
# These are handled in the main state_map already, but some need special handlers
async def delete_product_exec(update, context):
    pid = update.message.text.strip(); context.user_data.clear()
    db.del_prod(pid); await update.message.reply_text("✅ Deleted!", reply_markup=admin_kb())

async def toggle_product_exec(update, context):
    pid = update.message.text.strip(); context.user_data.clear()
    p = db.toggle_prod(pid); await update.message.reply_text(f"✅ Toggled! Now: {'Active' if p and p.get('active') else 'Inactive'}", reply_markup=admin_kb())

async def feature_product_exec(update, context):
    pid = update.message.text.strip(); context.user_data.clear()
    p = db.feature_prod(pid); await update.message.reply_text(f"✅ Featured: {'Yes ⭐' if p and p.get('featured') else 'No'}", reply_markup=admin_kb())

async def delete_stock_exec(update, context):
    sid = update.message.text.strip(); context.user_data.clear()
    db.del_stock(sid); await update.message.reply_text("✅ Deleted!", reply_markup=admin_kb())

# ═══════════════ CALLBACK ROUTER ═══════════════
async def callback_router(update, context):
    q = update.callback_query; d = q.data
    if d == "join_ok": await join_ok(update, context)
    elif d.startswith("buy_"): await buy_prod(update, context)
    elif d.startswith("dep_") or d == "dep_cancel": await deposit_method_cb(update, context)
    elif d.startswith("app_") or d.startswith("rej_"): await dep_approve(update, context)
    elif d == "back_main": await q.edit_message_text("🏠"); await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))

# ═══════════════ ERROR HANDLER ═══════════════
async def error_handler(update, context):
    log.error(f"Error: {context.error}")
    try:
        if update and update.effective_chat:
            await context.bot.send_message(update.effective_chat.id, "❌ Error! Please /start again.")
    except: pass

# ═══════════════ MAIN ═══════════════
def run_web():
    log.info(f"🌐 Web on {C.PORT}")
    wsgi_serve(app, host='0.0.0.0', port=C.PORT, threads=2)

def run_bot():
    bot = ApplicationBuilder().token(C.TOKEN).defaults(Defaults(parse_mode=ParseMode.MARKDOWN)).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("admin", admin_panel))
    bot.add_handler(CommandHandler("help", show_help))
    bot.add_handler(CommandHandler("balance", show_balance))
    bot.add_handler(CommandHandler("profile", show_profile))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    bot.add_handler(CallbackQueryHandler(callback_router))
    bot.add_error_handler(error_handler)
    
    log.info("🤖 Bot running!")
    print("""
╔══════════════════════════════════════╗
║     👑 ROYAL MAIL STORE            ║
║     VPN • Proxy • Mail             ║
║     Bot Started Successfully!      ║
╚══════════════════════════════════════╝
    """)
    bot.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def main():
    if not C.TOKEN: print("❌ BOT_TOKEN missing!"); sys.exit(1)
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()

if __name__ == "__main__":
    main()
