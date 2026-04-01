import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ======================== SOZLAMALAR ========================
BOT_TOKEN = "8627453491:AAGD5x-mPkxhWdbTWwkn53GxGEPjny_ouvY"
ADMIN_ID = 7399101034  # O'zingizning Telegram ID

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ======================== HOLATLAR ========================
ADD_CAT, ADD_NAME, ADD_PRICE, ADD_DESC = range(4)
EDIT_LIST, EDIT_CHOOSE_FIELD, EDIT_NAME, EDIT_PRICE, EDIT_DESC = range(4, 9)

# ======================== MA'LUMOTLAR ========================
kalyanlar = [
    {"id": 1, "name": "Classic Mix",   "price": 80000, "desc": "Klassik aralashma, engil"},
    {"id": 2, "name": "Double Apple",  "price": 90000, "desc": "Ikki olma aromati"},
    {"id": 3, "name": "Mint Fresh",    "price": 85000, "desc": "Yashil nane, salqin"},
]
ichimliklar = [
    {"id": 1, "name": "Mojito",    "price": 35000, "desc": "Nane va limon bilan"},
    {"id": 2, "name": "Limonad",   "price": 20000, "desc": "Uy usulida tayyorlangan"},
    {"id": 3, "name": "Qora choy", "price": 15000, "desc": "Issiq, shirinlik bilan"},
]
orders = []
next_k_id = 4
next_i_id = 4


def get_list(cat):
    return kalyanlar if cat == "kalyan" else ichimliklar

def get_item(cat, item_id):
    return next((x for x in get_list(cat) if x["id"] == item_id), None)


# ======================== FOYDALANUVCHI ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💨 Kalyanlar", callback_data="menu_kalyan")],
        [InlineKeyboardButton("🍹 Ichimliklar", callback_data="menu_ichimlik")],
        [InlineKeyboardButton("📋 Buyurtmalarim", callback_data="my_orders")],
    ]
    text = "🌿 *Kalyan Bar*'ga xush kelibsiz!\n\nQuyidagi bo'limdan birini tanlang:"
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split("_")[1]
    lst = get_list(cat)
    emoji = "💨" if cat == "kalyan" else "🍹"
    title = "Kalyanlar" if cat == "kalyan" else "Ichimliklar"
    if not lst:
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
        await query.edit_message_text("Hozircha bo'sh.", reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = [[InlineKeyboardButton(f"{emoji} {x['name']} — {x['price']:,} so'm", callback_data=f"info_{cat}_{x['id']}")] for x in lst]
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    await query.edit_message_text(f"{emoji} *{title}:*\n\nBirini tanlang:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def item_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat, item_id = query.data.split("_")
    item = get_item(cat, int(item_id))
    if not item:
        await query.edit_message_text("Topilmadi.")
        return
    emoji = "💨" if cat == "kalyan" else "🍹"
    kb = [
        [InlineKeyboardButton("✅ Buyurtma qilish", callback_data=f"order_{cat}_{item_id}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data=f"menu_{cat}")],
    ]
    await query.edit_message_text(f"{emoji} *{item['name']}*\n\n📝 {item['desc']}\n💰 Narx: *{item['price']:,} so'm*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def order_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat, item_id = query.data.split("_")
    item = get_item(cat, int(item_id))
    if not item:
        await query.edit_message_text("Topilmadi.")
        return
    user = query.from_user
    order = {
        "id": len(orders) + 1,
        "user_id": user.id,
        "username": user.username or user.first_name,
        "cat": "Kalyan" if cat == "kalyan" else "Ichimlik",
        "name": item["name"],
        "price": item["price"],
        "status": "⏳ Kutilmoqda",
    }
    orders.append(order)
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=(f"🔔 *Yangi buyurtma!*\n\n👤 Mijoz: @{order['username']} (ID: {user.id})\n📦 Tur: {order['cat']}\n🔖 Nomi: {order['name']}\n💰 Narx: {order['price']:,} so'm\n🆔 Buyurtma №{order['id']}"), parse_mode="Markdown")
    except Exception:
        pass
    kb = [[InlineKeyboardButton("🔙 Bosh menyuga", callback_data="back_main")]]
    await query.edit_message_text(f"✅ *Buyurtmangiz qabul qilindi!*\n\n📦 {order['cat']}: {order['name']}\n💰 {order['price']:,} so'm\n\nTez orada xizmat ko'rsatiladi! 🙏", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_orders = [o for o in orders if o["user_id"] == query.from_user.id]
    if not user_orders:
        text = "📋 Sizda hali buyurtma yo'q.\n\nMenyudan biror narsa tanlang!"
    else:
        lines = ["📋 *Sizning buyurtmalaringiz:*\n"]
        for o in user_orders:
            lines.append(f"№{o['id']} | {o['cat']} | {o['name']} | {o['price']:,} so'm | {o['status']}")
        text = "\n".join(lines)
    kb = [[InlineKeyboardButton("🔙 Bosh menyuga", callback_data="back_main")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ======================== ADMIN ========================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return
    kb = [
        [InlineKeyboardButton("➕ Qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton("✏️ Tahrirlash", callback_data="admin_edit")],
        [InlineKeyboardButton("❌ O'chirish", callback_data="admin_del")],
        [InlineKeyboardButton("📋 Buyurtmalar", callback_data="admin_orders")],
        [InlineKeyboardButton("🗂 Menyuni ko'rish", callback_data="admin_viewmenu")],
    ]
    await update.message.reply_text("⚙️ *Admin panel*\n\nNimani qilmoqchisiz?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# --- BEKOR QILISH ---

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Bekor qilindi.")
    else:
        await update.message.reply_text("❌ Bekor qilindi.")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Yopildi. /admin — qayta ochish uchun")


# ======================== ASOSIY ========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Qo'shish conversation
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_start, pattern="^admin_add$")],
        states={
            ADD_CAT: [CallbackQueryHandler(add_choose_cat, pattern="^cat_")],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_get_name)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_get_price)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_get_desc)],
        },
        fallbacks=[CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$"), CommandHandler("cancel", cancel_conv)]
    )

    # Tahrirlash conversation
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_start, pattern="^admin_edit$")],
        states={
            EDIT_LIST: [CallbackQueryHandler(edit_show_list, pattern="^ecat_"), CallbackQueryHandler(edit_choose_item, pattern=r"^eid_\d+$")],
            EDIT_CHOOSE_FIELD: [CallbackQueryHandler(edit_choose_field, pattern="^ef_")],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save_name)],
            EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save_price)],
            EDIT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save_desc)],
        },
        fallbacks=[CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$"), CommandHandler("cancel", cancel_conv)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(add_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^menu_(kalyan|ichimlik)$"))
    app.add_handler(CallbackQueryHandler(item_info, pattern=r"^info_(kalyan|ichimlik)_\d+$"))
    app.add_handler(CallbackQueryHandler(order_item, pattern=r"^order_(kalyan|ichimlik)_\d+$"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(cancel_cb, pattern="^cancel_cb$"))

    app.run_polling()


if __name__ == "__main__":
    main()
