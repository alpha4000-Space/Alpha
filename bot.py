import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ======================== SOZLAMALAR ========================
BOT_TOKEN = "8627453491:AAGD5x-mPkxhWdbTWwkn53GxGEPjny_ouvY"
ADMIN_ID = 7399101034  # O'zingizning Telegram ID (@userinfobot dan bilib oling)

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
        [InlineKeyboardButton("💨 Kalyanlar",     callback_data="menu_kalyan")],
        [InlineKeyboardButton("🍹 Ichimliklar",   callback_data="menu_ichimlik")],
        [InlineKeyboardButton("📋 Buyurtmalarim", callback_data="my_orders")],
    ]
    text = "🌿 *Kalyan Bar*'ga xush kelibsiz!\n\nQuyidagi bo'limdan birini tanlang:"
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                       reply_markup=InlineKeyboardMarkup(kb))


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

    kb = [[InlineKeyboardButton(f"{emoji} {x['name']} — {x['price']:,} so'm",
                                 callback_data=f"info_{cat}_{x['id']}")] for x in lst]
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    await query.edit_message_text(f"{emoji} *{title}:*\n\nBirini tanlang:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))


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
    await query.edit_message_text(
        f"{emoji} *{item['name']}*\n\n📝 {item['desc']}\n💰 Narx: *{item['price']:,} so'm*",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )


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
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🔔 *Yangi buyurtma!*\n\n"
                f"👤 Mijoz: @{order['username']} (ID: {user.id})\n"
                f"📦 Tur: {order['cat']}\n"
                f"🔖 Nomi: {order['name']}\n"
                f"💰 Narx: {order['price']:,} so'm\n"
                f"🆔 Buyurtma №{order['id']}"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

    kb = [[InlineKeyboardButton("🔙 Bosh menyuga", callback_data="back_main")]]
    await query.edit_message_text(
        f"✅ *Buyurtmangiz qabul qilindi!*\n\n"
        f"📦 {order['cat']}: {order['name']}\n"
        f"💰 {order['price']:,} so'm\n\n"
        f"Tez orada xizmat ko'rsatiladi! 🙏",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )


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
    await query.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))


# ======================== ADMIN ========================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return
    kb = [
        [InlineKeyboardButton("➕ Qo'shish",        callback_data="admin_add")],
        [InlineKeyboardButton("✏️ Tahrirlash",      callback_data="admin_edit")],
        [InlineKeyboardButton("❌ O'chirish",        callback_data="admin_del")],
        [InlineKeyboardButton("📋 Buyurtmalar",     callback_data="admin_orders")],
        [InlineKeyboardButton("🗂 Menyuni ko'rish",  callback_data="admin_viewmenu")],
    ]
    await update.message.reply_text("⚙️ *Admin panel*\n\nNimani qilmoqchisiz?",
                                     parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(kb))


# --- QO'SHISH ---

async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("💨 Kalyan",   callback_data="cat_kalyan")],
        [InlineKeyboardButton("🍹 Ichimlik", callback_data="cat_ichimlik")],
    ]
    await query.edit_message_text("➕ *Qaysi turga qo'shmoqchisiz?*",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))
    return ADD_CAT


async def add_choose_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["add_cat"] = query.data.split("_")[1]
    await query.edit_message_text("📝 Nomini kiriting:")
    return ADD_NAME


async def add_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_name"] = update.message.text.strip()
    await update.message.reply_text("💰 Narxini kiriting (faqat raqam):\nMasalan: 50000")
    return ADD_PRICE


async def add_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit():
        await update.message.reply_text("❌ Faqat raqam kiriting! Qayta urining:")
        return ADD_PRICE
    context.user_data["add_price"] = int(text)
    await update.message.reply_text("📄 Qisqacha tavsif kiriting:")
    return ADD_DESC


async def add_get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_k_id, next_i_id
    cat   = context.user_data["add_cat"]
    name  = context.user_data["add_name"]
    price = context.user_data["add_price"]
    desc  = update.message.text.strip()

    if cat == "kalyan":
        kalyanlar.append({"id": next_k_id, "name": name, "price": price, "desc": desc})
        next_k_id += 1
    else:
        ichimliklar.append({"id": next_i_id, "name": name, "price": price, "desc": desc})
        next_i_id += 1

    label = "Kalyan" if cat == "kalyan" else "Ichimlik"
    await update.message.reply_text(
        f"✅ *{label}* menyuga qo'shildi!\n🔖 {name}\n💰 {price:,} so'm\n📝 {desc}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# --- TAHRIRLASH ---

async def admin_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    kb = [
        [InlineKeyboardButton("💨 Kalyanlar",   callback_data="ecat_kalyan")],
        [InlineKeyboardButton("🍹 Ichimliklar", callback_data="ecat_ichimlik")],
        [InlineKeyboardButton("🔙 Bekor",       callback_data="cancel_conv")],
    ]
    await query.edit_message_text("✏️ *Qaysi turni tahrirlash?*",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_LIST


async def edit_show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split("_")[1]
    context.user_data["edit_cat"] = cat
    lst = get_list(cat)

    if not lst:
        await query.edit_message_text("Bo'sh.")
        return ConversationHandler.END

    kb = [[InlineKeyboardButton(f"{x['name']} — {x['price']:,} so'm",
                                 callback_data=f"eid_{x['id']}")] for x in lst]
    kb.append([InlineKeyboardButton("🔙 Bekor", callback_data="cancel_conv")])
    await query.edit_message_text("✏️ Qaysi elementni tahrirlash?",
                                   reply_markup=InlineKeyboardMarkup(kb))
    return EDIT_LIST


async def edit_choose_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[1])
    cat = context.user_data["edit_cat"]
    item = get_item(cat, item_id)
    if not item:
        await query.edit_message_text("Topilmadi.")
        return ConversationHandler.END

    context.user_data["edit_id"] = item_id
    kb = [
        [InlineKeyboardButton("📝 Nomini o'zgartir",    callback_data="ef_name")],
        [InlineKeyboardButton("💰 Narxini o'zgartir",   callback_data="ef_price")],
        [InlineKeyboardButton("📄 Tavsifini o'zgartir", callback_data="ef_desc")],
        [InlineKeyboardButton("🔙 Bekor",               callback_data="cancel_conv")],
    ]
    await query.edit_message_text(
        f"✏️ *{item['name']}*\n💰 {item['price']:,} so'm\n📝 {item['desc']}\n\nNimani o'zgartirish?",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )
    return EDIT_CHOOSE_FIELD


async def edit_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.split("_")[1]
    context.user_data["edit_field"] = field
    prompts = {
        "name":  "📝 Yangi nomni kiriting:",
        "price": "💰 Yangi narxni kiriting (faqat raqam):",
        "desc":  "📄 Yangi tavsifni kiriting:"
    }
    await query.edit_message_text(prompts[field])
    return {"name": EDIT_NAME, "price": EDIT_PRICE, "desc": EDIT_DESC}[field]


async def edit_save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    item = get_item(context.user_data["edit_cat"], context.user_data["edit_id"])
    old = item["name"]
    item["name"] = update.message.text.strip()
    await update.message.reply_text(f"✅ Nom: *{old}* → *{item['name']}*", parse_mode="Markdown")
    return ConversationHandler.END


async def edit_save_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(" ", "").replace(",", "")
    if not text.isdigit():
        await update.message.reply_text("❌ Faqat raqam! Qayta kiriting:")
        return EDIT_PRICE
    item = get_item(context.user_data["edit_cat"], context.user_data["edit_id"])
    old = item["price"]
    item["price"] = int(text)
    await update.message.reply_text(
        f"✅ *{item['name']}* narxi: {old:,} → *{item['price']:,} so'm*",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def edit_save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    item = get_item(context.user_data["edit_cat"], context.user_data["edit_id"])
    item["desc"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ *{item['name']}* tavsifi yangilandi:\n📝 {item['desc']}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# --- O'CHIRISH ---

async def admin_del_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("💨 Kalyanlar",   callback_data="dcat_kalyan")],
        [InlineKeyboardButton("🍹 Ichimliklar", callback_data="dcat_ichimlik")],
        [InlineKeyboardButton("🔙 Bekor",       callback_data="cancel_cb")],
    ]
    await query.edit_message_text("❌ *Qaysi turdan o'chirish?*",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))


async def del_show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split("_")[1]
    lst = get_list(cat)

    if not lst:
        await query.edit_message_text("Bo'sh.")
        return

    kb = [[InlineKeyboardButton(f"❌ {x['name']} — {x['price']:,} so'm",
                                 callback_data=f"ditem_{cat}_{x['id']}")] for x in lst]
    kb.append([InlineKeyboardButton("🔙 Bekor", callback_data="cancel_cb")])
    await query.edit_message_text("❌ Qaysi elementni o'chirish?",
                                   reply_markup=InlineKeyboardMarkup(kb))


async def del_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    cat = parts[1]
    item_id = int(parts[2])
    lst = get_list(cat)
    item = get_item(cat, item_id)
    if not item:
        await query.edit_message_text("Topilmadi.")
        return
    lst.remove(item)
    await query.edit_message_text(f"✅ *{item['name']}* o'chirildi.", parse_mode="Markdown")


# --- BUYURTMALAR ---

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not orders:
        await query.edit_message_text("Hali buyurtma yo'q.")
        return

    lines = ["📋 *Barcha buyurtmalar:*\n"]
    for o in orders:
        lines.append(
            f"№{o['id']} | {o['cat']} | {o['name']} | {o['price']:,} so'm | {o['status']}"
        )
    total = sum(o["price"] for o in orders)
    lines.append(f"\n💰 Jami: *{total:,} so'm*")

    kb = [[InlineKeyboardButton("🔙 Admin panel", callback_data="cancel_cb")]]
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))


# --- MENYUNI KO'RISH (admin) ---

async def admin_viewmenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lines = ["💨 *Kalyanlar:*\n"]
    for x in kalyanlar:
        lines.append(f"• {x['name']} — {x['price']:,} so'm\n  📝 {x['desc']}")

    lines.append("\n🍹 *Ichimliklar:*\n")
    for x in ichimliklar:
        lines.append(f"• {x['name']} — {x['price']:,} so'm\n  📝 {x['desc']}")

    kb = [[InlineKeyboardButton("🔙 Admin panel", callback_data="cancel_cb")]]
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(kb))


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
            ADD_CAT:   [CallbackQueryHandler(add_choose_cat, pattern="^cat_")],
            ADD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_get_name)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_get_price)],
            ADD_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_get_desc)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$"),
            CommandHandler("cancel", cancel_conv),
        ]
    )

    # Tahrirlash conversation
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_start, pattern="^admin_edit$")],
        states={
            EDIT_LIST: [
                CallbackQueryHandler(edit_show_list,   pattern="^ecat_"),
                CallbackQueryHandler(edit_choose_item, pattern=r"^eid_\d+$"),
            ],
            EDIT_CHOOSE_FIELD: [
                CallbackQueryHandler(edit_choose_field, pattern="^ef_"),
            ],
            EDIT_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save_name)],
            EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save_price)],
            EDIT_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save_desc)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$"),
            CommandHandler("cancel", cancel_conv),
        ]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(add_conv)
    app.add_handler(edit_conv)

    # Foydalanuvchi handlerlari
app.add_handler(CallbackQueryHandler(show_menu,  pattern="^menu_(kalyan|ichimlik)$"))
app.add_handler(CallbackQueryHandler(item_info,  pattern=r"^info_(kalyan|ichimlik)_\d+$"))
app.add_handler(CallbackQueryHandler(order_item, pattern=r"^order_(kalyan|ichimlik)_\d+$"))
app.add_handler(CallbackQueryHandler(my_orders,  pattern="^my_orders$"))
app.add_handler(CallbackQueryHandler(start,      pattern="^back_main$"))

# Qo‘shimcha admin handlerlari bo‘lsa shu yerga qo‘shiladi
# masalan: admin_del_start, del_show_list, del_item, admin_orders, admin_viewmenu

# Botni ishga tushirish
app.run_polling()


if __name__ == "__main__":
    main()
