import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import Database

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8267152801:AAHTHTae-KTPcd8xVxEZ3vJEuvk8MstOPn8"     # @BotFather dan oling
ADMIN_IDS = [7399101034]          # @userinfobot dan ID oling

# ===================== SETUP =====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()


# ===================== STATES =====================
class DepositState(StatesGroup):
    choose_crypto = State()
    waiting_amount = State()
    waiting_screenshot = State()

class WithdrawState(StatesGroup):
    choose_crypto = State()
    waiting_address = State()
    waiting_amount = State()

class BroadcastState(StatesGroup):
    waiting_message = State()

class SettingsState(StatesGroup):
    edit_refbonus = State()

# Admin: crypto qo'shish
class AddCryptoState(StatesGroup):
    symbol = State()
    name = State()
    wallet = State()
    min_deposit = State()
    multiplier = State()
    wait_hours = State()

# Admin: crypto tahrirlash
class EditCryptoState(StatesGroup):
    choose_field = State()
    enter_value = State()


# ===================== KLAVIATURALAR =====================
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💰 Depozit"), KeyboardButton(text="📊 Balans")],
        [KeyboardButton(text="📜 Tarix"), KeyboardButton(text="👥 Referal")],
        [KeyboardButton(text="ℹ️ Ma'lumot"), KeyboardButton(text="💸 Yechib olish")]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🪙 Cryptolar"), KeyboardButton(text="💳 Kutayotganlar")],
        [KeyboardButton(text="👤 Foydalanuvchilar"), KeyboardButton(text="📈 Statistika")],
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ], resize_keyboard=True)

def crypto_list_kb(cryptos: list, prefix: str = "dep_crypto"):
    """Crypto tanlash uchun inline tugmalar"""
    buttons = []
    for c in cryptos:
        status = "✅" if c['is_active'] else "❌"
        label = f"{status} {c['symbol']} | x{c['multiplier']} | min:{c['min_deposit']}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}_{c['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_crypto_kb(cryptos: list):
    """Admin uchun crypto boshqaruv tugmalari"""
    buttons = []
    for c in cryptos:
        status = "🟢" if c['is_active'] else "🔴"
        buttons.append([
            InlineKeyboardButton(text=f"{status} {c['symbol']} ({c['name']})",
                                 callback_data=f"acrypto_{c['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="➕ Yangi crypto qo'shish", callback_data="add_crypto")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_crypto_actions_kb(crypto_id: int, is_active: bool):
    toggle_text = "🔴 O'chirish" if is_active else "🟢 Yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_crypto_{crypto_id}"),
         InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_crypto_{crypto_id}")],
        [InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"delete_crypto_{crypto_id}"),
         InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_cryptos")]
    ])


# ===================== START =====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    db.add_user(user_id, message.from_user.username or "", message.from_user.full_name, referrer_id)

    cryptos = db.get_all_cryptos(only_active=True)
    crypto_names = ", ".join(c['symbol'] for c in cryptos) if cryptos else "Hozircha yo'q"

    await message.answer(
        f"👋 Xush kelibsiz, *{message.from_user.full_name}*!\n\n"
        f"🤖 *Crypto Investment Bot*\n\n"
        f"💡 Qanday ishlaydi:\n"
        f"• Istalgan cryptoda depozit qiling\n"
        f"• Belgilangan vaqt kuting\n"
        f"• Pulingiz ko'paytirib qaytariladi! 🚀\n\n"
        f"🪙 Mavjud cryptolar: *{crypto_names}*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


# ===================== BALANS =====================
@dp.message(F.text == "📊 Balans")
async def show_balance(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Iltimos, /start bosing.")
        return

    active = db.get_active_deposits(message.from_user.id)
    active_text = ""
    for dep in active:
        finish = dep['approved_at'] + timedelta(hours=dep['wait_hours'])
        remaining = finish - datetime.now()
        payout = dep['amount'] * dep['multiplier']
        if remaining.total_seconds() > 0:
            h = int(remaining.total_seconds() // 3600)
            m = int((remaining.total_seconds() % 3600) // 60)
            active_text += f"\n• {dep['amount']} {dep['crypto_symbol']} → {payout:.4f} | ⏳ {h}s {m}m"
        else:
            active_text += f"\n• {dep['amount']} {dep['crypto_symbol']} → {payout:.4f} | ✅ Tayyor"

    await message.answer(
        f"💼 *Hisobingiz*\n\n"
        f"💰 Balans: *{user['balance_usd']:.4f}*\n"
        f"📥 Jami kiritilgan: *{user['total_deposited']:.4f}*\n"
        f"📤 Jami yechilgan: *{user['total_withdrawn']:.4f}*\n"
        f"\n⚡ Aktiv depozitlar:{active_text if active_text else ' Yo`q'}",
        parse_mode="Markdown"
    )


# ===================== DEPOZIT =====================
@dp.message(F.text == "💰 Depozit")
async def deposit_start(message: types.Message, state: FSMContext):
    cryptos = db.get_all_cryptos(only_active=True)
    if not cryptos:
        await message.answer("❌ Hozircha aktiv crypto yo'q. Admin tez orada qo'shadi!")
        return

    await message.answer(
        "🪙 *Qaysi cryptoda depozit qilmoqchisiz?*\n\n"
        "Pastdan tanlang:",
        parse_mode="Markdown",
        reply_markup=crypto_list_kb(cryptos, prefix="dep_crypto")
    )
    await state.set_state(DepositState.choose_crypto)


@dp.callback_query(F.data.startswith("dep_crypto_"), DepositState.choose_crypto)
async def deposit_choose_crypto(callback: types.CallbackQuery, state: FSMContext):
    crypto_id = int(callback.data.split("_")[2])
    crypto = db.get_crypto(crypto_id)
    if not crypto or not crypto['is_active']:
        await callback.answer("Bu crypto hozir mavjud emas!", show_alert=True)
        return

    await state.update_data(crypto_id=crypto_id, crypto=crypto)
    await callback.message.edit_text(
        f"✅ Tanlandi: *{crypto['name']} ({crypto['symbol']})*\n\n"
        f"📌 Minimal miqdor: *{crypto['min_deposit']} {crypto['symbol']}*\n"
        f"📈 Koeffitsient: *x{crypto['multiplier']}*\n"
        f"⏰ Kutish vaqti: *{crypto['wait_hours']} soat*\n\n"
        f"Qancha *{crypto['symbol']}* kiritmoqchisiz?",
        parse_mode="Markdown"
    )
    await state.set_state(DepositState.waiting_amount)


@dp.message(DepositState.waiting_amount)
async def deposit_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        crypto = data['crypto']

        if amount < crypto['min_deposit']:
            await message.answer(
                f"❌ Minimal miqdor *{crypto['min_deposit']} {crypto['symbol']}*! Qayta kiriting:",
                parse_mode="Markdown"
            )
            return

        payout = amount * crypto['multiplier']
        await state.update_data(amount=amount)
        await message.answer(
            f"💳 *To'lov ma'lumotlari*\n\n"
            f"🪙 Crypto: *{crypto['symbol']}*\n"
            f"💰 Miqdor: *{amount} {crypto['symbol']}*\n"
            f"📈 Qaytariladigan: *{payout:.4f} {crypto['symbol']}*\n"
            f"⏰ {crypto['wait_hours']} soatdan keyin\n\n"
            f"📤 Quyidagi manzilga yuboring:\n"
            f"`{crypto['wallet_address']}`\n\n"
            f"📸 To'lovni amalga oshirgach *skrinshotini* yuboring!",
            parse_mode="Markdown"
        )
        await state.set_state(DepositState.waiting_screenshot)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting! Masalan: 0.005")


@dp.message(DepositState.waiting_screenshot)
async def deposit_screenshot(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer(
            "❌ Iltimos, *skrinshot rasm* yuboring!\n_(Matn emas, rasm bo'lishi kerak)_",
            parse_mode="Markdown"
        )
        return

    data = await state.get_data()
    crypto = data['crypto']
    amount = data['amount']
    crypto_id = data['crypto_id']
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    payout = amount * crypto['multiplier']

    dep_id = db.create_deposit(user_id, crypto_id, crypto['symbol'], amount, photo_id)

    for admin_id in ADMIN_IDS:
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{dep_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{dep_id}")
            ]])
            u = message.from_user
            await bot.send_photo(
                admin_id,
                photo=photo_id,
                caption=(
                    f"🆕 *Yangi depozit so'rovi #{dep_id}*\n\n"
                    f"👤 [{u.full_name}](tg://user?id={user_id}) | `{user_id}`\n"
                    f"🪙 Crypto: *{crypto['symbol']}* ({crypto['name']})\n"
                    f"💰 Miqdor: *{amount} {crypto['symbol']}*\n"
                    f"📈 Qaytarish: *{payout:.4f} {crypto['symbol']}* (x{crypto['multiplier']})\n"
                    f"⏰ {crypto['wait_hours']} soatdan keyin\n"
                    f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                ),
                parse_mode="Markdown",
                reply_markup=kb
            )
        except Exception as e:
            logging.error(f"Admin xabari xatosi: {e}")

    await message.answer(
        "✅ *So'rovingiz qabul qilindi!*\n\n"
        f"⏳ Admin skrinshotni ko'rib chiqadi.\n"
        f"Tasdiqlangach *{crypto['wait_hours']} soat*dan keyin "
        f"*{payout:.4f} {crypto['symbol']}* hisobingizga tushadi! 🚀",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await state.clear()


# ===================== TASDIQLASH / RAD ETISH =====================
@dp.callback_query(F.data.startswith("approve_"))
async def approve_deposit(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!")
        return
    dep_id = int(callback.data.split("_")[1])
    deposit = db.get_deposit(dep_id)
    if not deposit:
        await callback.answer("Depozit topilmadi!")
        return
    if deposit['status'] != 'pending':
        await callback.answer("Allaqachon ko'rib chiqilgan!")
        return

    db.approve_deposit(dep_id)
    payout = deposit['amount'] * deposit['multiplier']
    finish = datetime.now() + timedelta(hours=deposit['wait_hours'])

    try:
        await bot.send_message(
            deposit['user_id'],
            f"🎉 *Depozitingiz tasdiqlandi!*\n\n"
            f"🪙 {deposit['amount']} {deposit['crypto_symbol']}\n"
            f"📈 {deposit['wait_hours']} soatdan keyin: *{payout:.4f} {deposit['crypto_symbol']}*\n"
            f"⏰ Tugash vaqti: {finish.strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(e)

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ *TASDIQLANDI*",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Tasdiqlandi!")
    asyncio.create_task(auto_payout(deposit['user_id'], payout, dep_id,
                                    deposit['crypto_symbol'], deposit['wait_hours']))


@dp.callback_query(F.data.startswith("reject_"))
async def reject_deposit(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!")
        return
    dep_id = int(callback.data.split("_")[1])
    deposit = db.get_deposit(dep_id)
    if not deposit:
        await callback.answer("Depozit topilmadi!")
        return
    db.reject_deposit(dep_id)
    try:
        await bot.send_message(
            deposit['user_id'],
            "❌ *Depozitingiz rad etildi.*\nAdmin bilan bog'laning.",
            parse_mode="Markdown"
        )
    except:
        pass
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ *RAD ETILDI*",
        parse_mode="Markdown"
    )
    await callback.answer("❌ Rad etildi!")


# ===================== AVTOMATIK TO'LOV =====================
async def auto_payout(user_id: int, payout: float, dep_id: int,
                      symbol: str, wait_hours: int):
    await asyncio.sleep(wait_hours * 3600)
    db.add_balance(user_id, payout)
    db.mark_paid(dep_id)
    try:
        await bot.send_message(
            user_id,
            f"🎊 *To'lovingiz tayyor!*\n\n"
            f"💰 Hisobingizga *{payout:.4f} {symbol}* qo'shildi!\n"
            f"💸 Yechib olish uchun: 'Yechib olish' tugmasini bosing.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(e)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ Avtomatik to'lov: user {user_id} ga {payout:.4f} {symbol}"
            )
        except:
            pass


# ===================== TARIX =====================
@dp.message(F.text == "📜 Tarix")
async def show_history(message: types.Message):
    history = db.get_user_history(message.from_user.id, limit=10)
    if not history:
        await message.answer("📭 Hali hech qanday tranzaksiya yo'q.")
        return
    status_map = {"pending": "⏳", "approved": "✅", "paid": "💰", "rejected": "❌"}
    text = "📜 *So'nggi 10 ta depozit:*\n\n"
    for h in history:
        emoji = status_map.get(h['status'], "•")
        payout = h['amount'] * h['multiplier']
        text += (f"{emoji} {h['amount']} {h['crypto_symbol']} → {payout:.4f} "
                 f"| {h['created_at'].strftime('%d.%m %H:%M')} | {h['status']}\n")
    await message.answer(text, parse_mode="Markdown")


# ===================== REFERAL =====================
@dp.message(F.text == "👥 Referal")
async def show_referral(message: types.Message):
    user_id = message.from_user.id
    count = db.get_referral_count(user_id)
    earnings = db.get_referral_earnings(user_id)
    bonus = db.get_setting('referral_bonus') or '5'
    info = await bot.get_me()
    link = f"https://t.me/{info.username}?start={user_id}"
    await message.answer(
        f"👥 *Referal tizimi*\n\n"
        f"🔗 Havolangiz:\n`{link}`\n\n"
        f"👤 Taklif qilganlar: *{count}* kishi\n"
        f"💰 Referal daromad: *{earnings:.4f}*\n\n"
        f"💡 Har bir do'stingiz depozit qilganda *{bonus}%* bonus!",
        parse_mode="Markdown"
    )


# ===================== YECHISH =====================
@dp.message(F.text == "💸 Yechib olish")
async def withdraw_start(message: types.Message, state: FSMContext):
    user = db.get_user(message.from_user.id)
    if not user or user['balance_usd'] <= 0:
        await message.answer("❌ Hisobingizda mablag' yo'q!")
        return
    cryptos = db.get_all_cryptos(only_active=True)
    if not cryptos:
        await message.answer("❌ Hozircha aktiv crypto yo'q!")
        return
    await message.answer(
        f"💸 *Pul yechish*\n\n"
        f"💰 Balans: *{user['balance_usd']:.4f}*\n\n"
        f"Qaysi cryptoda yechmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=crypto_list_kb(cryptos, prefix="wd_crypto")
    )
    await state.set_state(WithdrawState.choose_crypto)


@dp.callback_query(F.data.startswith("wd_crypto_"), WithdrawState.choose_crypto)
async def withdraw_choose_crypto(callback: types.CallbackQuery, state: FSMContext):
    crypto_id = int(callback.data.split("_")[2])
    crypto = db.get_crypto(crypto_id)
    await state.update_data(crypto=crypto)
    await callback.message.edit_text(
        f"✅ Tanlandi: *{crypto['symbol']}*\n\n"
        f"📍 {crypto['symbol']} wallet manzilingizni kiriting:",
        parse_mode="Markdown"
    )
    await state.set_state(WithdrawState.waiting_address)


@dp.message(WithdrawState.waiting_address)
async def withdraw_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    user = db.get_user(message.from_user.id)
    data = await state.get_data()
    crypto = data['crypto']
    await message.answer(
        f"💰 Qancha *{crypto['symbol']}* yechmoqchisiz?\n"
        f"_(Mavjud balans: {user['balance_usd']:.4f})_",
        parse_mode="Markdown"
    )
    await state.set_state(WithdrawState.waiting_amount)


@dp.message(WithdrawState.waiting_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        user = db.get_user(message.from_user.id)
        if amount > user['balance_usd']:
            await message.answer("❌ Yetarli mablag' yo'q!")
            return
        if amount <= 0:
            await message.answer("❌ Miqdor 0 dan katta bo'lishi kerak!")
            return
        data = await state.get_data()
        crypto = data['crypto']
        address = data['address']
        db.create_withdrawal(message.from_user.id, crypto['symbol'], amount, address)
        db.deduct_balance(message.from_user.id, amount)
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"💸 *Yechish so'rovi*\n\n"
                    f"👤 [{message.from_user.full_name}](tg://user?id={message.from_user.id})\n"
                    f"🪙 Crypto: *{crypto['symbol']}*\n"
                    f"💰 Miqdor: *{amount} {crypto['symbol']}*\n"
                    f"📍 Manzil: `{address}`",
                    parse_mode="Markdown"
                )
            except:
                pass
        await message.answer(
            "✅ *Yechish so'rovi qabul qilindi!*\n\n"
            "Admin 1-24 soat ichida yuboradi.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Noto'g'ri raqam!")


# ===================== MA'LUMOT =====================
@dp.message(F.text == "ℹ️ Ma'lumot")
async def info(message: types.Message):
    cryptos = db.get_all_cryptos(only_active=True)
    crypto_text = ""
    for c in cryptos:
        crypto_text += f"• {c['symbol']} ({c['name']}) | x{c['multiplier']} | {c['wait_hours']}s | min: {c['min_deposit']}\n"
    if not crypto_text:
        crypto_text = "Hozircha mavjud emas"
    await message.answer(
        f"ℹ️ *Bot haqida*\n\n"
        f"🤖 Crypto Investment Bot\n\n"
        f"🪙 *Mavjud cryptolar:*\n{crypto_text}\n"
        f"👥 Referal bonus: {db.get_setting('referral_bonus') or 5}%\n\n"
        f"📞 Admin: @admin_username",
        parse_mode="Markdown"
    )


# ==================== ADMIN PANEL ====================
@dp.message(Command("admin"))
async def admin_panel(message: types.Mess
