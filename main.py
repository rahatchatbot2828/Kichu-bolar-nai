#!/usr/bin/env python3
"""
ROYAL MAIL STORE - Replit Ready
"""
import os, sys, json, time, uuid, asyncio, logging, threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import wraps
from collections import defaultdict

# Auto install
try:
    from flask import Flask, jsonify
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Defaults
    from telegram.constants import ParseMode, ChatMemberStatus
    from telegram.request import HTTPXRequest
except ImportError:
    os.system("pip install python-telegram-bot==20.7 flask waitress")
    from flask import Flask, jsonify
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Defaults
    from telegram.constants import ParseMode, ChatMemberStatus
    from telegram.request import HTTPXRequest

# ═══════════════ CONFIG ═══════════════
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8959981246:AAEzhH4IJKEo7kxd7b3QSUq8-5eGqmNNVsc")
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "5507924915")).split(",") if x.strip()]
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@RoyalMarketingZone")
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01301027106")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01301027106")
    PORT = int(os.getenv("PORT", "8080"))
    DATA_DIR = Path("data")
    MIN_DEPOSIT = int(os.getenv("MIN_DEPOSIT", "10"))
    MAX_DEPOSIT = int(os.getenv("MAX_DEPOSIT", "100"))
    UPTIME_START = time.time()

config = Config()
config.DATA_DIR.mkdir(exist_ok=True)

# ═══════════════ LOGGING ═══════════════
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RoyalMail")

# ═══════════════ DATABASE ═══════════════
class DB:
    def __init__(self):
        self.dir = config.DATA_DIR
        self.cache = {}
        for name in ['users','products','stock','deposits','settings','logs']:
            f = self.dir / f"{name}.json"
            if not f.exists(): f.write_text('[]')
    
    def _r(self, name):
        try: return json.loads((self.dir / f"{name}.json").read_text())
        except: return []
    
    def _w(self, name, data):
        (self.dir / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        self.cache.pop(f"r_{name}", None)
    
    def user(self, tid):
        for u in self._r('users'):
            if u.get('telegramId') == tid: return u.copy()
        return None
    
    def save_user(self, data):
        users = self._r('users')
        idx = next((i for i,u in enumerate(users) if u.get('telegramId')==data.get('telegramId')), None)
        now = datetime.now().isoformat()
        if idx is not None:
            users[idx].update(data)
            users[idx]['lastActive'] = now
        else:
            users.append({'telegramId':data['telegramId'],'username':data.get('username',''),'firstName':data.get('firstName',''),'balance':0.0,'totalSpent':0.0,'totalDeposited':0.0,'totalPurchases':0,'isBanned':False,'role':'admin' if data['telegramId'] in config.ADMIN_IDS else 'user','joinedAt':now,'lastActive':now})
        self._w('users', users)
    
    def all_users(self): return self._r('users')
    
    def add_balance(self, tid, amt):
        users = self._r('users')
        for u in users:
            if u['telegramId']==tid:
                u['balance'] = round(u['balance']+amt,2)
                if amt>0: u['totalDeposited'] = round(u.get('totalDeposited',0)+amt,2)
                self._w('users',users)
                return u
        return None
    
    def pay(self, tid, amt):
        users = self._r('users')
        for u in users:
            if u['telegramId']==tid and u['balance']>=amt:
                u['balance'] = round(u['balance']-amt,2)
                u['totalSpent'] = round(u.get('totalSpent',0)+amt,2)
                u['totalPurchases'] = u.get('totalPurchases',0)+1
                self._w('users',users)
                return True
        return False
    
    def products(self, ptype=None):
        p = self._r('products')
        if ptype: return [x for x in p if x.get('type')==ptype and x.get('isActive',True)]
        return [x for x in p if x.get('isActive',True)]
    
    def product(self, pid): return next((p for p in self._r('products') if p.get('id')==pid), None)
    
    def add_product(self, data):
        prods = self._r('products')
        data['id'] = str(int(time.time()*1000))
        data['isActive'] = True
        data['createdAt'] = datetime.now().isoformat()
        prods.append(data)
        self._w('products',prods)
    
    def stock_avail(self, ptype, price=None):
        for s in self._r('stock'):
            if s.get('productType')==ptype and not s.get('isSold'):
                if price is None or s.get('price')==price: return s
        return None
    
    def add_stock(self, data):
        stock = self._r('stock')
        data['id'] = str(int(time.time()*1000))
        data['isSold'] = False
        data['addedAt'] = datetime.now().isoformat()
        stock.append(data)
        self._w('stock',stock)
    
    def sell_stock(self, sid, buyer):
        stock = self._r('stock')
        for s in stock:
            if s['id']==sid:
                s['isSold']=True; s['soldTo']=buyer; s['soldAt']=datetime.now().isoformat()
                self._w('stock',stock)
                return s
        return None
    
    def stock_count(self):
        s = self._r('stock')
        return {'total':len(s),'avail':len([x for x in s if not x['isSold']]),'sold':len([x for x in s if x['isSold']])}
    
    def create_deposit(self, data):
        deps = self._r('deposits')
        data['id'] = str(int(time.time()*1000))
        data['status'] = 'pending'
        data['createdAt'] = datetime.now().isoformat()
        deps.append(data)
        self._w('deposits',deps)
        return data
    
    def pending_deps(self): return [d for d in self._r('deposits') if d['status']=='pending']
    
    def update_dep(self, did, status, admin):
        deps = self._r('deposits')
        for d in deps:
            if d['id']==did:
                d['status']=status; d['reviewedBy']=admin; d['reviewedAt']=datetime.now().isoformat()
                if status=='approved': self.add_balance(d['telegramId'], d['amount'])
                self._w('deposits',deps)
                return d
        return None
    
    def stats(self):
        u = self._r('users'); d = self._r('deposits'); s = self._r('stock')
        a = [x for x in d if x['status']=='approved']
        return {'users':len(u),'revenue':sum(x['amount'] for x in a),'pending':len([x for x in d if x['status']=='pending']),'stock':len([x for x in s if not x['isSold']]),'uptime':int(time.time()-config.UPTIME_START)}

db = DB()

# ═══════════════ FLASK ═══════════════
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    s = db.stats()
    return f"""<!DOCTYPE html><html><head><title>ROYAL MAIL STORE</title><meta charset="utf-8"><style>
body{{background:#0a0a0a;color:#ffd700;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.box{{text-align:center;padding:30px;border:2px solid #ffd700;border-radius:15px}}
h1{{font-size:2em}}.green{{color:#0f0}}p{{color:#aaa}}</style></head>
<body><div class="box"><h1>👑 ROYAL MAIL STORE</h1><p class="green">🟢 Bot Running</p><p>Users: {s['users']} | Revenue: {s['revenue']:.0f} TK | Stock: {s['stock']}</p></div></body></html>"""

@flask_app.route('/health')
def health(): return jsonify({"status":"ok"})

# ═══════════════ KEYBOARDS ═══════════════
def main_kb(uid=None):
    admin = uid in config.ADMIN_IDS if uid else False
    rows = [[KeyboardButton("🔐 VPN"),KeyboardButton("🌐 Proxy")],[KeyboardButton("📧 Mail"),KeyboardButton("💰 Deposit")],[KeyboardButton("💳 Balance"),KeyboardButton("ℹ️ Help")]]
    if admin: rows.append([KeyboardButton("👑 Admin")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([[KeyboardButton("📦 Add Product"),KeyboardButton("📥 Add Stock")],[KeyboardButton("👥 Users"),KeyboardButton("💰 Pending")],[KeyboardButton("📊 Stats"),KeyboardButton("📢 Broadcast")],[KeyboardButton("🔙 Main")]], resize_keyboard=True)

# ═══════════════ HANDLERS ═══════════════
async def start(update, context):
    u = update.effective_user
    db.save_user({'telegramId':u.id,'username':u.username or '','firstName':u.first_name or ''})
    await update.message.reply_text("👑 *ROYAL MAIL STORE*\n\n🔐 VPN | 🌐 Proxy | 📧 Mail\n\nSelect:", parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(u.id))

async def handle_msg(update, context):
    uid = update.effective_user.id; txt = update.message.text.strip()
    u = update.effective_user
    db.save_user({'telegramId':uid,'username':u.username or '','firstName':u.first_name or ''})
    
    user = db.user(uid)
    if user and user.get('isBanned'): await update.message.reply_text("🚫 Banned!"); return
    
    state = context.user_data.get('state')
    if state: return await state_handler(update, context)
    
    if txt=="🔐 VPN": await show_cat(update, context, "vpn")
    elif txt=="🌐 Proxy": await show_cat(update, context, "proxy")
    elif txt=="📧 Mail": await show_cat(update, context, "mail")
    elif txt=="💰 Deposit":
        context.user_data['state']='deposit'
        await update.message.reply_text(f"💰 *Deposit*\n💳 bKash: `{config.BKASH_NUMBER}`\n💳 Nagad: `{config.NAGAD_NUMBER}`\n\nReply: `Amount TXN_ID`", parse_mode=ParseMode.MARKDOWN)
    elif txt=="💳 Balance":
        u = db.user(uid)
        if u: await update.message.reply_text(f"💳 *Balance*\n💰 {u['balance']} TK\n📊 Spent: {u['totalSpent']} TK", parse_mode=ParseMode.MARKDOWN)
    elif txt=="ℹ️ Help":
        await update.message.reply_text(f"ℹ️ *Help*\n💰 Min Deposit: {config.MIN_DEPOSIT} TK\n💳 bKash: {config.BKASH_NUMBER}\n📞 {config.CHANNEL_USERNAME}", parse_mode=ParseMode.MARKDOWN)
    elif txt=="👑 Admin" and uid in config.ADMIN_IDS:
        s = db.stats()
        await update.message.reply_text(f"👑 *Admin*\n👥 {s['users']}\n💰 {s['revenue']:.0f} TK\n📦 {s['stock']}", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb())
    elif uid in config.ADMIN_IDS: await admin_actions(update, context)

async def show_cat(update, context, cat):
    prods = db.products(cat)
    if not prods: await update.message.reply_text(f"❌ No {cat.upper()}!"); return
    kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']} TK", callback_data=f"buy_{p['id']}")] for p in prods]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
    await update.message.reply_text(f"📦 *{cat.upper()}*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def buy_handler(update, context):
    q = update.callback_query; await q.answer()
    if q.data=="menu_back":
        await q.edit_message_text("🏠"); await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))
        return
    uid = update.effective_user.id; pid = q.data.replace("buy_","")
    product = db.product(pid); user = db.user(uid)
    if not product: await q.edit_message_text("❌ Not found!"); return
    if user['balance']<product['price']: await q.edit_message_text(f"❌ Balance: {user['balance']} TK\n💰 Price: {product['price']} TK"); return
    stock = db.stock_avail(product['type'], product['price'])
    if not stock: await q.edit_message_text("❌ Out of stock!"); return
    db.pay(uid, product['price']); db.sell_stock(stock['id'], uid)
    bal = db.user(uid)['balance']
    msg = f"✅ *Purchased!*\n📦 {product['name']}\n💰 {product['price']} TK\n💳 Balance: {bal} TK\n\n"
    d = stock['data']
    if product['type']=='vpn': msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`"
    elif product['type']=='proxy': msg += f"🌐 `{d.get('host','')}`:{d.get('port','')}\n👤 `{d.get('username','')}`\n🔑 `{d.get('password','')}`"
    elif product['type']=='mail': msg += f"📧 `{d.get('email','')}`\n🔐 `{d.get('password','')}`"
    await q.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

async def process_deposit(update, context):
    uid = update.effective_user.id; txt = update.message.text.strip()
    parts = txt.split()
    if len(parts)<2: await update.message.reply_text("❌ Format: `50 TXN123`"); return
    try: amt = float(parts[0])
    except: await update.message.reply_text("❌ Invalid!"); return
    txn = ' '.join(parts[1:])
    if amt<config.MIN_DEPOSIT or amt>config.MAX_DEPOSIT: await update.message.reply_text(f"❌ {config.MIN_DEPOSIT}-{config.MAX_DEPOSIT} TK!"); return
    dep = db.create_deposit({'telegramId':uid,'username':update.effective_user.username or '','firstName':update.effective_user.first_name or '','amount':amt,'transactionId':txn,'paymentMethod':'Manual'})
    context.user_data.clear()
    for aid in config.ADMIN_IDS:
        try: await context.bot.send_message(aid, f"💰 *New Deposit*\n👤 {update.effective_user.first_name}\n💰 {amt} TK\n🔢 `{txn}`", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅",callback_data=f"app_{dep['id']}"),InlineKeyboardButton("❌",callback_data=f"rej_{dep['id']}")]]))
        except: pass
    await update.message.reply_text(f"✅ *Submitted!*\n💰 {amt} TK\n⏳ Pending...", parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(uid))

async def handle_approval(update, context):
    q = update.callback_query; await q.answer()
    if update.effective_user.id not in config.ADMIN_IDS: return
    data = q.data; status = "approved" if data.startswith("app_") else "rejected"; did = data.split("_",1)[1]
    dep = db.update_dep(did, status, update.effective_user.id)
    if dep:
        try: await context.bot.send_message(dep['telegramId'], f"{'✅' if status=='approved' else '❌'} Deposit {status}!\n💰 {dep['amount']} TK", parse_mode=ParseMode.MARKDOWN)
        except: pass
        await q.edit_message_text(f"{'✅' if status=='approved' else '❌'} {status}!")

async def admin_actions(update, context):
    txt = update.message.text.strip(); uid = update.effective_user.id
    if txt=="📦 Add Product":
        context.user_data['state']='add_product'; context.user_data['step']=1
        await update.message.reply_text("📦 Type: `vpn` `proxy` `mail`")
    elif txt=="📥 Add Stock":
        context.user_data['state']='add_stock'
        await update.message.reply_text("📥 Format: `email|pass|expire|price`\n`done` to finish.")
    elif txt=="👥 Users":
        users = db.all_users()
        msg = f"👥 *Users ({len(users)})*\n" + "\n".join([f"{'🚫' if u.get('isBanned') else '✅'} {u.get('firstName','')} - {u['balance']} TK" for u in users[:20]])
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    elif txt=="💰 Pending":
        deps = db.pending_deps()
        if not deps: await update.message.reply_text("✅ None!"); return
        for d in deps:
            await update.message.reply_text(f"💰 {d['firstName']} - {d['amount']} TK\n🔢 `{d['transactionId']}`", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅",callback_data=f"app_{d['id']}"),InlineKeyboardButton("❌",callback_data=f"rej_{d['id']}")]]))
    elif txt=="📊 Stats":
        s = db.stats(); await update.message.reply_text(f"📊 *Stats*\n👥 {s['users']}\n💰 {s['revenue']:.0f} TK\n📦 {s['stock']}", parse_mode=ParseMode.MARKDOWN)
    elif txt=="📢 Broadcast":
        context.user_data['state']='broadcast'; await update.message.reply_text("📢 Message:")
    elif txt=="🔙 Main": await update.message.reply_text("🏠 Menu", reply_markup=main_kb(uid))

async def state_handler(update, context):
    state = context.user_data.get('state'); txt = update.message.text.strip(); uid = update.effective_user.id
    if txt=="❌ Cancel": context.user_data.clear(); await update.message.reply_text("❌ Cancelled", reply_markup=main_kb(uid) if uid not in config.ADMIN_IDS else admin_kb()); return
    if state=='deposit': await process_deposit(update, context)
    elif state=='add_product':
        step = context.user_data.get('step',1)
        if step==1:
            if txt not in ['vpn','proxy','mail']: await update.message.reply_text("❌ vpn/proxy/mail!"); return
            context.user_data['ptype']=txt; context.user_data['step']=2
            await update.message.reply_text("📝 Name:")
        elif step==2:
            context.user_data['pname']=txt; context.user_data['step']=3
            await update.message.reply_text("💰 Price:")
        elif step==3:
            try: price=float(txt)
            except: await update.message.reply_text("❌ Number!"); return
            db.add_product({'type':context.user_data['ptype'],'name':context.user_data['pname'],'price':price})
            context.user_data.clear()
            await update.message.reply_text(f"✅ Added!\n📦 {context.user_data.get('pname','')}\n💰 {price} TK", reply_markup=admin_kb())
    elif state=='add_stock':
        if txt.lower() in ['done','✅ done']: context.user_data.clear(); await update.message.reply_text("✅ Done!", reply_markup=admin_kb()); return
        added=0
        for line in txt.split('\n'):
            parts=[p.strip() for p in line.split('|')]
            if len(parts)>=4: db.add_stock({'productType':'vpn','productName':'VPN','data':{'email':parts[0],'password':parts[1],'expireDate':parts[2]},'price':float(parts[3]),'addedBy':uid}); added+=1
        await update.message.reply_text(f"✅ {added} added! More or Done.")
    elif state=='broadcast':
        context.user_data.clear(); users=db.all_users(); s=f=0
        m=await update.message.reply_text("📤 Sending...")
        for u in users:
            try: await context.bot.send_message(u['telegramId'], txt, parse_mode=ParseMode.MARKDOWN); s+=1
            except: f+=1
            await asyncio.sleep(0.05)
        await m.edit_text(f"✅ Done!\n✅ {s}\n❌ {f}")
        await update.message.reply_text("👑 Admin", reply_markup=admin_kb())

async def callback_router(update, context):
    q=update.callback_query; d=q.data
    if d.startswith("buy_"): await buy_handler(update, context)
    elif d.startswith("app_") or d.startswith("rej_"): await handle_approval(update, context)
    elif d=="menu_back": await q.edit_message_text("🏠"); await context.bot.send_message(q.message.chat.id, "Menu:", reply_markup=main_kb(update.effective_user.id))

# ═══════════════ MAIN ═══════════════
def run_bot():
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    app = ApplicationBuilder().token(config.BOT_TOKEN).defaults(Defaults(parse_mode=ParseMode.MARKDOWN)).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(callback_router))
    logger.info("🤖 Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def run_web():
    from waitress import serve
    logger.info(f"🌐 Web on port {config.PORT}")
    serve(flask_app, host='0.0.0.0', port=config.PORT, threads=2)

def main():
    print("👑 ROYAL MAIL STORE - Starting...")
    if not config.BOT_TOKEN: print("❌ BOT_TOKEN missing!"); sys.exit(1)
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()

if __name__ == "__main__":
    main()
