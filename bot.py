"""
╔══════════════════════════════════════════════════════╗
║           🍸 PROFESSIONAL BAR BOT (aiogram 3)        ║
║     1 ta faylda: Menyu + Admin panel + Buyurtmalar   ║
╚══════════════════════════════════════════════════════╝

O'rnatish:
    pip install aiogram aiosqlite

Ishga tushirish:
    python bar_bot.py
"""

import asyncio
import logging
import json
import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ════════════════════════════════════════════════════════
#  ⚙️  SOZLAMALAR — BU YERNI TO'LDIRING
# ════════════════════════════════════════════════════════

BOT_TOKEN   = "8627453491:AAFxYm7xrC2iU4BYn_xLZMEqhozrSjV_hoc"   # @BotFather dan oling
ADMIN_IDS   = [7399101034]         # Sizning Telegram ID (@userinfobot dan bilib olasiz)
DB_PATH     = "bar.db"
CURRENCY    = "so'm"

# ════════════════════════════════════════════════════════
#  🗄️  DATABASE
# ════════════════════════════════════════════════════════

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT NOT NULL UNIQUE,
                emoji     TEXT DEFAULT '🍹',
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS drinks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id  INTEGER NOT NULL,
                name         TEXT NOT NULL,
                description  TEXT DEFAULT '',
                price        INTEGER NOT NULL,
                is_available INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS orders (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                username     TEXT,
                table_number TEXT,
                items        TEXT NOT NULL,
                total_price  INTEGER NOT NULL,
                status       TEXT DEFAULT 'new',
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Default kategoriyalar
        for row in [
            ("Kokteylar","🍹"), ("Vino","🍷"), ("Pivo","🍺"),
            ("Viski","🥃"), ("Alkogolsiz","🧃")
        ]:
            await db.execute(
                "INSERT OR IGNORE INTO categories (name, emoji) VALUES (?,?)", row
            )
        await db.commit()

# ── helpers ──
async def db_fetchall(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def db_fetchone(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

async def db_execute(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid

# ── Category ──
async def get_categories(active_only=True):
    q = "SELECT * FROM categories" + (" WHERE is_active=1" if active_only else "") + " ORDER BY id"
    return await db_fetchall(q)

async def add_category(name, emoji="🍹"):
    try:
        await db_execute("INSERT INTO categories (name,emoji) VALUES (?,?)", (name, emoji))
        return True
    except:
        return False

async def delete_category(cid):
    await db_execute("DELETE FROM drinks WHERE category_id=?", (cid,))
    await db_execute("DELETE FROM categories WHERE id=?", (cid,))

async def toggle_category(cid):
    await db_execute(
        "UPDATE categories SET is_active=CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?", (cid,)
    )

# ── Drinks ──
async def get_drinks(category_id, available_only=True):
    q = "SELECT * FROM drinks WHERE category_id=?"
    if available_only: q += " AND is_available=1"
    q += " ORDER BY id"
    return await db_fetchall(q, (category_id,))

async def get_all_drinks():
    return await db_fetchall(
        "SELECT d.*,c.name cat_name,c.emoji cat_emoji FROM drinks d "
        "JOIN categories c ON d.category_id=c.id ORDER BY c.id, d.id"
    )

async def get_drink(did):
    return await db_fetchone("SELECT * FROM drinks WHERE id=?", (did,))

async def add_drink(category_id, name, description, price):
    await db_execute(
        "INSERT INTO drinks (category_id,name,description,price) VALUES (?,?,?,?)",
        (category_id, name, description, price)
    )

async def update_drink_price(did, price):
    await db_execute("UPDATE drinks SET price=? WHERE id=?", (price, did))

async def update_drink_name(did, name):
    await db_execute("UPDATE drinks SET name=? WHERE id=?", (name, did))

async def update_drink_desc(did, desc):
    await db_execute("UPDATE drinks SET description=? WHERE id=?", (desc, did))

async def delete_drink(did):
    await db_execute("DELETE FROM drinks WHERE id=?", (did,))

async def toggle_drink(did):
    await db_execute(
        "UPDATE drinks SET is_available=CASE WHEN is_available=1 THEN 0 ELSE 1 END WHERE id=?", (did,)
    )

# ── Orders ──
async def create_order(user_id, username, table_number, items_dict, total):
    return await db_execute(
        "INSERT INTO orders (user_id,username,table_number,items,total_price) VALUES (?,?,?,?,?)",
        (user_id, username, table_number, json.dumps(items_dict, ensure_ascii=False), total)
    )

async def get_orders(status=None):
    if status:
        return await db_fetchall("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT 30", (status,))
    return await db_fetchall("SELECT * FROM orders ORDER BY id DESC LIMIT 30")

async def set_order_status(oid, status):
    await db_execute("UPDATE orders SET status=? WHERE id=?", (status, oid))

async def get_stats():
    total   = (await db_fetchone("SELECT COUNT(*) c FROM orders"))['c']
    new     = (await db_fetchone("SELECT COUNT(*) c FROM orders WHERE status='new'"))['c']
    done    = (await db_fetchone("SELECT COUNT(*) c FROM orders WHERE status='done'"))['c']
    revenue = (await db_fetchone("SELECT COALESCE(SUM(total_price),0) c FROM orders WHERE status='done'"))['c']
    drinks  = (await db_fetchone("SELECT COUNT(*) c FROM drinks WHERE is_available=1"))['c']
    return total, new, done, revenue, drinks

# ════════════════════════════════════════════════════════
#  ⌨️  KLAVIATURALAR
# ════════════════════════════════════════════════════════

def kb_main():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🍹 Menyu"), KeyboardButton(text="🛒 Savatcha")],
        [KeyboardButton(text="📋 Buyurtmalarim"), KeyboardButton(text="ℹ️ Ma'lumot")]
    ], resize_keyboard=True)

def kb_admin():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🍹 Ichimliklar")],
        [KeyboardButton(text="📁 Kategoriyalar"), KeyboardButton(text="📦 Buyurtmalar")],
        [KeyboardButton(text="👤 Foydalanuvchi rejimi")]
    ], resize_keyboard=True)

def kb_categories(cats):
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"{c['emoji']} {c['name']}", callback_data=f"cat:{c['id']}")
    b.adjust(2)
    return b.as_markup()

def kb_drinks(drinks):
    b = InlineKeyboardBuilder()
    for d in drinks:
        b.button(text=f"{d['name']} — {d['price']:,} {CURRENCY}", callback_data=f"drink:{d['id']}")
    b.button(text="⬅️ Kategoriyalar", callback_data="back:cats")
    b.adjust(1)
    return b.as_markup()

def kb_drink_detail(did):
    b = InlineKeyboardBuilder()
    b.button(text="🛒 Savatga qo'shish", callback_data=f"add:{did}")
    b.button(text="⬅️ Orqaga", callback_data="back:cats")
    b.adjust(1)
    return b.as_markup()

def kb_cart(has_items=True):
    b = InlineKeyboardBuilder()
    if has_items:
        b.button(text="✅ Buyurtma berish", callback_data="checkout")
        b.button(text="🗑 Tozalash", callback_data="clear_cart")
    b.button(text="🍹 Menyuga", callback_data="back:cats")
    b.adjust(1)
    return b.as_markup()

def kb_confirm():
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlash", callback_data="confirm_order")
    b.button(text="❌ Bekor", callback_data="cancel_order")
    b.adjust(2)
    return b.as_markup()

def kb_order_admin(oid):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Bajarildi",  callback_data=f"ord:done:{oid}")
    b.button(text="🚫 Bekor qilish", callback_data=f"ord:cancel:{oid}")
    b.adjust(2)
    return b.as_markup()

def kb_admin_cats(cats):
    b = InlineKeyboardBuilder()
    for c in cats:
        ico = "✅" if c['is_active'] else "❌"
        b.button(text=f"{ico} {c['emoji']} {c['name']}", callback_data=f"ac:{c['id']}")
    b.button(text="➕ Yangi kategoriya", callback_data="ac:new")
    b.adjust(1)
    return b.as_markup()

def kb_admin_cat_detail(cid):
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Yoq/Yoqish",   callback_data=f"acat:toggle:{cid}")
    b.button(text="🗑 O'chirish",     callback_data=f"acat:del:{cid}")
    b.button(text="⬅️ Orqaga",        callback_data="acat:back")
    b.adjust(2)
    return b.as_markup()

def kb_admin_drinks(drinks):
    b = InlineKeyboardBuilder()
    for d in drinks:
        ico = "✅" if d['is_available'] else "❌"
        b.button(text=f"{ico} {d['name']} ({d['cat_name']}) — {d['price']:,}", callback_data=f"ad:{d['id']}")
    b.button(text="➕ Yangi ichimlik", callback_data="ad:new")
    b.button(text="⬅️ Orqaga",         callback_data="adm:back")
    b.adjust(1)
    return b.as_markup()

def kb_admin_drink_detail(did, is_avail):
    b = InlineKeyboardBuilder()
    txt = "🔴 O'chirish" if is_avail else "🟢 Yoqish"
    b.button(text=txt,              callback_data=f"adm_d:toggle:{did}")
    b.button(text="💰 Narx o'zgartir", callback_data=f"adm_d:price:{did}")
    b.button(text="✏️ Nom o'zgartir",  callback_data=f"adm_d:name:{did}")
    b.button(text="📝 Tavsif o'zgartir", callback_data=f"adm_d:desc:{did}")
    b.button(text="🗑 O'chirish",      callback_data=f"adm_d:del:{did}")
    b.button(text="⬅️ Orqaga",         callback_data="ad:back")
    b.adjust(2)
    return b.as_markup()

def kb_add_drink_cats(cats):
    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(text=f"{c['emoji']} {c['name']}", callback_data=f"newdrink_cat:{c['id']}")
    b.adjust(2)
    return b.as_markup()

def kb_orders_filter():
    b = InlineKeyboardBuilder()
    b.button(text="🆕 Yangi",     callback_data="orders:new")
    b.button(text="✅ Bajarilgan", callback_data="orders:done")
    b.button(text="🚫 Bekor",     callback_data="orders:cancel")
    b.button(text="📋 Hammasi",   callback_data="orders:all")
    b.adjust(2)
    return b.as_markup()

# ════════════════════════════════════════════════════════
#  📦  FSM STATES
# ════════════════════════════════════════════════════════

class OrderForm(StatesGroup):
    table = State()

class AdminAddDrink(StatesGroup):
    cat    = State()
    name   = State()
    desc   = State()
    price  = State()

class AdminAddCat(StatesGroup):
    name  = State()
    emoji = State()

class AdminEditDrink(StatesGroup):
    price = State()
    name  = State()
    desc  = State()

# ════════════════════════════════════════════════════════
#  🤖  ROUTER
# ════════════════════════════════════════════════════════

router = Router()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def fmt_price(p):
    return f"{p:,} {CURRENCY}"

def cart_text(cart: dict):
    if not cart:
        return "🛒 Savatcha bo'sh"
    lines = ["🛒 <b>Savatchangizdagi ichimliklar:</b>\n"]
    total = 0
    for name, (price, qty) in cart.items():
        lines.append(f"• {name} × {qty} = {fmt_price(price * qty)}")
        total += price * qty
    lines.append(f"\n💰 <b>Jami: {fmt_price(total)}</b>")
    return "\n".join(lines)

# ════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    name = msg.from_user.first_name
    if is_admin(msg.from_user.id):
        await msg.answer(
            f"👑 Xush kelibsiz, Admin <b>{name}</b>!\n\n"
            f"Siz admin paneliga kirishingiz mumkin.",
            reply_markup=kb_admin(), parse_mode="HTML"
        )
    else:
        await msg.answer(
            f"🍸 Xush kelibsiz, <b>{name}</b>!\n\n"
            f"Barning menyusini ko'rish uchun <b>🍹 Menyu</b> tugmasini bosing.",
            reply_markup=kb_main(), parse_mode="HTML"
        )

# ════════════════════════════════════════════════════════
#  👤  FOYDALANUVCHI — MENYU
# ════════════════════════════════════════════════════════

@router.message(F.text == "🍹 Menyu")
async def show_menu(msg: Message):
    cats = await get_categories(active_only=True)
    if not cats:
        await msg.answer("😔 Hozircha menyu mavjud emas.")
        return
    await msg.answer("🍸 <b>Kategoriyani tanlang:</b>", reply_markup=kb_categories(cats), parse_mode="HTML")

@router.callback_query(F.data.startswith("cat:"))
async def show_category(cb: CallbackQuery):
    cid = int(cb.data.split(":")[1])
    drinks = await get_drinks(cid, available_only=True)
    if not drinks:
        await cb.answer("😔 Bu kategoriyada ichimlik yo'q", show_alert=True)
        return
    await cb.message.edit_text("🍹 <b>Ichimlikni tanlang:</b>", reply_markup=kb_drinks(drinks), parse_mode="HTML")

@router.callback_query(F.data.startswith("drink:"))
async def show_drink(cb: CallbackQuery):
    did = int(cb.data.split(":")[1])
    d = await get_drink(did)
    if not d:
        await cb.answer("Topilmadi", show_alert=True)
        return
    text = (
        f"🍹 <b>{d['name']}</b>\n\n"
        f"📝 {d['description'] or 'Tavsif yo\'q'}\n\n"
        f"💰 Narxi: <b>{fmt_price(d['price'])}</b>"
    )
    await cb.message.edit_text(text, reply_markup=kb_drink_detail(did), parse_mode="HTML")

@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(cb: CallbackQuery, state: FSMContext):
    did = int(cb.data.split(":")[1])
    d = await get_drink(did)
    if not d:
        await cb.answer("Topilmadi", show_alert=True)
        return
    data = await state.get_data()
    cart = data.get("cart", {})
    key = str(did)
    if key in cart:
        cart[key][1] += 1
    else:
        cart[key] = [d['price'], 1, d['name']]
    await state.update_data(cart=cart)
    await cb.answer(f"✅ {d['name']} savatga qo'shildi!", show_alert=False)

@router.callback_query(F.data == "back:cats")
async def back_to_cats(cb: CallbackQuery):
    cats = await get_categories(active_only=True)
    await cb.message.edit_text("🍸 <b>Kategoriyani tanlang:</b>", reply_markup=kb_categories(cats), parse_mode="HTML")

# ════════════════════════════════════════════════════════
#  🛒  SAVATCHA
# ════════════════════════════════════════════════════════

@router.message(F.text == "🛒 Savatcha")
async def show_cart(msg: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})
    # cart: {str(id): [price, qty, name]}
    display = {v[2]: (v[0], v[1]) for v in cart.values()}
    text = cart_text(display)
    await msg.answer(text, reply_markup=kb_cart(bool(cart)), parse_mode="HTML")

@router.callback_query(F.data == "clear_cart")
async def clear_cart(cb: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await cb.message.edit_text("🗑 Savatcha tozalandi.", reply_markup=kb_cart(False))

@router.callback_query(F.data == "checkout")
async def checkout(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", {})
    if not cart:
        await cb.answer("Savatcha bo'sh!", show_alert=True)
        return
    await cb.message.answer("🪑 Stol raqamingizni kiriting (masalan: 5):")
    await state.set_state(OrderForm.table)

@router.message(OrderForm.table)
async def order_table(msg: Message, state: FSMContext):
    table = msg.text.strip()
    await state.update_data(table=table)
    data = await state.get_data()
    cart = data.get("cart", {})
    display = {v[2]: (v[0], v[1]) for v in cart.values()}
    text = cart_text(display) + f"\n\n🪑 Stol: <b>{table}</b>\n\nTasdiqlaysizmi?"
    await msg.answer(text, reply_markup=kb_confirm(), parse_mode="HTML")

@router.callback_query(F.data == "confirm_order")
async def confirm_order(cb: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cart = data.get("cart", {})
    table = data.get("table", "?")
    if not cart:
        await cb.answer("Savatcha bo'sh!", show_alert=True)
        return

    items_list = {v[2]: {"price": v[0], "qty": v[1]} for v in cart.values()}
    total = sum(v[0]*v[1] for v in cart.values())

    oid = await create_order(
        cb.from_user.id,
        cb.from_user.username or cb.from_user.first_name,
        table, items_list, total
    )

    await state.update_data(cart={})
    await cb.message.edit_text(
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"📋 Buyurtma №{oid}\n"
        f"🪑 Stol: {table}\n"
        f"💰 Jami: {fmt_price(total)}\n\n"
        f"Tez orada xizmatchi yetib keladi!",
        parse_mode="HTML"
    )

    # Adminlarga xabar yuborish
    lines = [f"🆕 <b>Yangi buyurtma №{oid}</b>\n"]
    lines.append(f"👤 @{cb.from_user.username or cb.from_user.first_name}")
    lines.append(f"🪑 Stol: {table}")
    lines.append("")
    for name, v in items_list.items():
        lines.append(f"• {name} × {v['qty']} = {fmt_price(v['price']*v['qty'])}")
    lines.append(f"\n💰 <b>Jami: {fmt_price(total)}</b>")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id, "\n".join(lines),
                reply_markup=kb_order_admin(oid), parse_mode="HTML"
            )
        except:
            pass

@router.callback_query(F.data == "cancel_order")
async def cancel_order(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_text("❌ Buyurtma bekor qilindi.")

# ════════════════════════════════════════════════════════
#  📋  FOYDALANUVCHI BUYURTMALARI
# ════════════════════════════════════════════════════════

@router.message(F.text == "📋 Buyurtmalarim")
async def my_orders(msg: Message):
    orders = await db_fetchall(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (msg.from_user.id,)
    )
    if not orders:
        await msg.answer("📋 Sizda hali buyurtma yo'q.")
        return
    statuses = {"new":"🆕 Yangi","done":"✅ Bajarildi","cancel":"🚫 Bekor"}
    lines = ["📋 <b>Oxirgi buyurtmalaringiz:</b>\n"]
    for o in orders:
        st = statuses.get(o['status'], o['status'])
        lines.append(f"№{o['id']} | {st} | {fmt_price(o['total_price'])} | Stol: {o['table_number']}")
    await msg.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "ℹ️ Ma'lumot")
async def info(msg: Message):
    await msg.answer(
        "🍸 <b>Bizning Bar</b>\n\n"
        "Sifatli ichimliklar va professional xizmat!\n\n"
        "📞 Aloqa: @admin_username",
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════
#  👑  ADMIN PANEL
# ════════════════════════════════════════════════════════

def admin_only(func):
    async def wrapper(msg_or_cb, *args, **kwargs):
        uid = msg_or_cb.from_user.id if hasattr(msg_or_cb, 'from_user') els
