import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ===================== CONFIG =====================
BOT_TOKEN = "8627453491:AAGD5x-mPkxhWdbTWwkn53GxGEPjny_ouvY"

ACCEPT_EMOJI_ID = "5323765959444435759"
REJECT_EMOJI_ID = "5325998693898293667"
# ==================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def build_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Accept",
                callback_data="action_accept",
                icon_custom_emoji_id=ACCEPT_EMOJI_ID
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data="action_reject",
                icon_custom_emoji_id=REJECT_EMOJI_ID
            ),
        ]
    ])
    return keyboard


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        text="👋 <b>Welcome!</b>\n\nPlease make your choice:",
        parse_mode="HTML",
        reply_markup=build_keyboard()
    )


@dp.callback_query(lambda c: c.data == "action_accept")
async def accept_handler(callback: types.CallbackQuery):
    await callback.answer("Accepted!", show_alert=False)
    await callback.message.edit_text(
        text="✅ <b>You chose: Accept</b>\n\nAction confirmed!",
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data == "action_reject")
async def reject_handler(callback: types.CallbackQuery):
    await callback.answer("Rejected!", show_alert=False)
    await callback.message.edit_text(
        text="❌ <b>You chose: Reject</b>\n\nAction declined!",
        parse_mode="HTML"
    )


async def main():
    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
