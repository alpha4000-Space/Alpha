import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, MessageEntity
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

# ===================== CONFIG =====================
BOT_TOKEN = "8627453491:AAGD5x-mPkxhWdbTWwkn53GxGEPjny_ouvY"
ADMIN_CHAT_ID = 7399101034       # Admin shaxsiy chat ID
ADMIN_CHANNEL_ID = -100123456789 # Admin kanal ID

ACCEPT_EMOJI_ID = "5323765959444435759"
REJECT_EMOJI_ID = "5325998693898293667"

# Crypto kurslar (manual, o'zingiz yangilaysiz)
RATES = {
    "BTC":  {"buy": 95000, "sell": 94000},
    "ETH":  {"buy": 3500,  "sell": 3450},
    "BNB":  {"buy": 600,   "sell": 590},
    "SOL":  {"buy": 180,   "sell": 175},
    "LTC":  {"buy": 120,   "sell": 118},
    "TON":  {"buy": 5.5,   "sell": 5.3},
    "TRX":  {"buy": 0.13,  "sell": 0.12},
    "DOGE": {"buy": 0.18,  "sell": 0.17},
}
# ==================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Zayavka storage (oddiy dict, production da DB ishlatiladi)
orders = {}
order_counter = 0


# ========== FSM STATES ==========
class OrderState(StatesGroup):
    choose_direction = State()
    choose_crypto    = State()
    enter_amount     = State()
    enter_wallet     = State()
    upload_receipt   = State()


# ========== KEYBOARDS ==========
def main_menu():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💱 Obmen"), KeyboardButton(text="📊 Kurslar")],
        [KeyboardButton(text="📋 Tarixim")]
    ], resize_keyboard=True)
    return kb

def direction_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 So'm → Crypto", callback_data="dir_buy")],
        [InlineKeyboardButton(text="🔴 Crypto → So'm", callback_data="dir_sell")],
    ])
    return kb

def crypto_kb(direction: str):
    coins = list(RATES.keys())
    buttons = []
    row = []
    for i, coin in enumerate(coins):
        row.append(InlineKeyboardButton(text=coin, callback_data=f"coin_{direction}_{coin}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_order_kb(order_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Accept",
                callback_data=f"admin_accept_{order_id}",
                icon_custom_emoji_id=ACCEPT_EMOJI_ID
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"admin_reject_{order_id}",
                icon_custom_emoji_id=REJECT_EMOJI_ID
            ),
        ]
    ])
    return keyboard


# ========== HANDLERS ==========

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Xush kelibsiz!</b>\n\nCrypto obmen botiga xush kelibsiz. Nima qilmoqchisiz?",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.message(F.text == "📊 Kurslar")
async def rates_handler(message: types.Message):
    text = "📊 <b>Joriy kurslar (USD):</b>\n\n"
    for coin, rate in RATES.items():
        text += f"<b>{coin}</b>: Sotib olish ${rate['buy']:,} | Sotish ${rate['sell']:,}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📋 Tarixim")
async def history_handler(message: types.Message):
    user_id = message.from_user.id
    user_orders = [o for o in orders.values() if o["user_id"] == user_id]
    if not user_orders:
        await message.answer("📋 Sizda hali zayavkalar yo'q.")
        return
    text = "📋 <b>Sizning zayavkalaringiz:</b>\n\n"
    for o in user_orders[-10:]:
        status_emoji = "⏳" if o["status"] == "pending" else ("✅" if o["status"] == "accepted" else "❌")
        text += (
            f"{status_emoji} <b>#{o['id']}</b> | {o['direction']} | {o['crypto']}\n"
            f"   Miqdor: <code>{o['amount']}</code>\n"
            f"   Sana: {o['date']}\n\n"
        )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "💱 Obmen")
async def exchange_handler(message: types.Message, state: FSMContext):
    await state.set_state(OrderState.choose_direction)
    await message.answer(
        "💱 <b>Obmen yo'nalishini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=direction_kb()
    )

@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("🏠 Asosiy menyu:", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("dir_"))
async def choose_direction(callback: types.CallbackQuery, state: FSMContext):
    direction = callback.data.split("_")[1]  # buy yoki sell
    label = "So'm → Crypto" if direction == "buy" else "Crypto → So'm"
    await state.update_data(direction=label, dir_code=direction)
    await state.set_state(OrderState.choose_crypto)
    await callback.message.edit_text(
        f"✅ Yo'nalish: <b>{label}</b>\n\n🪙 Cryptoni tanlang:",
        parse_mode="HTML",
        reply_markup=crypto_kb(direction)
    )

@dp.callback_query(F.data.startswith("coin_"))
async def choose_crypto(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    direction = parts[1]
    coin = parts[2]
    rate = RATES[coin]["buy"] if direction == "buy" else RATES[coin]["sell"]
    await state.update_data(crypto=coin, rate=rate)
    await state.set_state(OrderState.enter_amount)
    await callback.message.edit_text(
        f"🪙 <b>{coin}</b> tanlandi\n"
        f"💵 Kurs: <b>${rate:,}</b>\n\n"
        f"💰 Miqdorni kiriting (USD da):",
        parse_mode="HTML"
    )

@dp.message(OrderState.enter_amount)
async def enter_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Iltimos, to'g'ri raqam kiriting. Masalan: <code>100</code>", parse_mode="HTML")
        return

    data = await state.get_data()
    rate = data["rate"]
    uzs = amount * rate * 12000  # taxminiy UZS (1 USD = 12000 so'm)

    await state.update_data(amount=amount)
    await state.set_state(OrderState.enter_wallet)

    dir_code = data.get("dir_code")
    if dir_code == "buy":
        await message.answer(
            f"💰 Miqdor: <b>${amount:,}</b>\n"
            f"💵 To'lash kerak: <b>~{uzs:,.0f} so'm</b>\n\n"
            f"📬 <b>Crypto wallet manzilingizni kiriting:</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"💰 Miqdor: <b>${amount:,}</b>\n"
            f"💵 Olasiz: <b>~{uzs:,.0f} so'm</b>\n\n"
            f"🏦 <b>Pul qabul qiladigan karta yoki hisobingizni kiriting:</b>",
            parse_mode="HTML"
        )

@dp.message(OrderState.enter_wallet)
async def enter_wallet(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    await state.set_state(OrderState.upload_receipt)
    await message.answer(
        "📸 <b>To'lov chekini (screenshot) yuboring:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(OrderState.upload_receipt, F.photo)
async def upload_receipt(message: types.Message, state: FSMContext):
    global order_counter
    order_counter += 1
    order_id = order_counter

    data = await state.get_data()
    user = message.from_user
    photo_id = message.photo[-1].file_id
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    order = {
        "id": order_id,
        "user_id": user.id,
        "username": user.username or "N/A",
        "full_name": user.full_name,
        "direction": data["direction"],
        "crypto": data["crypto"],
        "amount": data["amount"],
        "rate": data["rate"],
        "wallet": data["wallet"],
        "photo_id": photo_id,
        "status": "pending",
        "date": now,
        "chat_id": message.chat.id,
    }
    orders[order_id] = order
    await state.clear()

    # Foydalanuvchiga tasdiqlash
    await message.answer(
        f"✅ <b>Zayavkangiz qabul qilindi!</b>\n\n"
        f"🔢 Zayavka raqami: <b>#{order_id}</b>\n"
        f"💱 {data['direction']}\n"
        f"🪙 {data['crypto']} — ${data['amount']:,}\n"
        f"📅 {now}\n\n"
        f"⏳ Admin ko'rib chiqadi va javob beradi.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    # Admin xabari
    admin_text = (
        f"🔔 <b>Yangi zayavka #{order_id}</b>\n\n"
        f"👤 Foydalanuvchi: {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"💱 Yo'nalish: {data['direction']}\n"
        f"🪙 Crypto: {data['crypto']}\n"
        f"💰 Miqdor: ${data['amount']:,}\n"
        f"💵 Kurs: ${data['rate']:,}\n"
        f"📬 Wallet/Karta: <code>{data['wallet']}</code>\n"
        f"📅 Sana: {now}"
    )

    # Admin shaxsiy chatga
    await bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=photo_id,
        caption=admin_text,
        parse_mode="HTML",
        reply_markup=admin_order_kb(order_id)
    )

    # Admin kanalga
    await bot.send_photo(
        chat_id=ADMIN_CHANNEL_ID,
        photo=photo_id,
        caption=admin_text,
        parse_mode="HTML",
        reply_markup=admin_order_kb(order_id)
    )

@dp.message(OrderState.upload_receipt)
async def receipt_not_photo(message: types.Message):
    await message.answer("❗ Iltimos, rasm (screenshot) yuboring.")


# ========== ADMIN ACCEPT / REJECT ==========

@dp.callback_query(F.data.startswith("admin_accept_"))
async def admin_accept(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order = orders.get(order_id)
    if not order:
        await callback.answer("Zayavka topilmadi!", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer("Bu zayavka allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    order["status"] = "accepted"

    await callback.answer("✅ Qabul qilindi!")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ACCEPTED</b> by admin",
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar
    await bot.send_message(
        chat_id=order["chat_id"],
        text=(
            f"✅ <b>Zayavkangiz qabul qilindi!</b>\n\n"
            f"🔢 Zayavka: <b>#{order_id}</b>\n"
            f"💱 {order['direction']} | {order['crypto']} — ${order['amount']:,}\n\n"
            f"💬 Tez orada admin siz bilan bog'lanadi."
        ),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order = orders.get(order_id)
    if not order:
        await callback.answer("Zayavka topilmadi!", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer("Bu zayavka allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    order["status"] = "rejected"

    await callback.answer("❌ Rad etildi!")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>REJECTED</b> by admin",
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar
    await bot.send_message(
        chat_id=order["chat_id"],
        text=(
            f"❌ <b>Zayavkangiz rad etildi.</b>\n\n"
            f"🔢 Zayavka: <b>#{order_id}</b>\n"
            f"💱 {order['direction']} | {order['crypto']} — ${order['amount']:,}\n\n"
            f"❓ Savollar uchun adminga murojaat qiling."
        ),
        parse_mode="HTML"
    )


async def main():
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
