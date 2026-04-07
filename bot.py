import telebot
import requests
import time
from datetime import datetime
import threading
import json
import os
from typing import Dict, List, Optional

# ==================== KONFIGURATSIYA ====================
TOKEN = "8734711674:AAFhT5zzQUTxSw0CzcHYLtZEn9kSjgriFTo"  # Tokeningizni shu yerga yozing
DEFAULT_INTERVAL = 5
DATA_FILE = "user_data.json"  # Foydalanuvchi ma'lumotlari saqlanadigan fayl

bot = telebot.TeleBot(TOKEN)

# Barcha mavjud kripto valyutalar
ALL_COINS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "BNB": "BNBUSDT",
    "SOL": "SOLUSDT",
    "LTC": "LTCUSDT",
    "TON": "TONUSDT",
    "TRX": "TRXUSDT",
    "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "MATIC": "MATICUSDT"
}

# Emoji ID (Premium foydalanuvchi uchun)
EMOJI_IDS = {
    "BTC": "5215277894456089919",
    "ETH": "5215469686220688535",
    "BNB": "5215501052366852398",
    "SOL": "5215644439850028163",
    "LTC": "5215397251597243962",
    "TON": "5215541953340410399",
    "TRX": "5215676493190960888",
    "DOGE": "5215580724010193095"
}

# ==================== FOYDALANUVCHI HOLATI ====================
class UserState:
    """Har bir foydalanuvchi uchun holat (state)"""
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.message_id: Optional[int] = None
        self.active_coins: List[str] = ["BTC", "ETH", "BNB", "SOL"]  # Standart valyutalar
        self.interval: int = DEFAULT_INTERVAL
        self.updater_running: bool = True
        self.updater_thread: Optional[threading.Thread] = None
        self.waiting_for_coin: bool = False  # Valyuta qo'shish kutilmoqda
        self.waiting_for_interval: bool = False  # Interval kiritilishi kutilmoqda

class UserManager:
    """Barcha foydalanuvchilarni boshqarish"""
    def __init__(self):
        self.states: Dict[int, UserState] = {}
        self.load_data()
    
    def get_state(self, chat_id: int) -> UserState:
        if chat_id not in self.states:
            self.states[chat_id] = UserState(chat_id)
        return self.states[chat_id]
    
    def save_data(self):
        """Foydalanuvchi ma'lumotlarini faylga saqlash"""
        data = {}
        for chat_id, state in self.states.items():
            data[chat_id] = {
                "active_coins": state.active_coins,
                "interval": state.interval
            }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    
    def load_data(self):
        """Foydalanuvchi ma'lumotlarini fayldan yuklash"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    for chat_id_str, info in data.items():
                        chat_id = int(chat_id_str)
                        state = UserState(chat_id)
                        state.active_coins = info["active_coins"]
                        state.interval = info["interval"]
                        self.states[chat_id] = state
            except:
                pass

user_manager = UserManager()

# ==================== BINANCE API ====================
def get_prices() -> Dict[str, float]:
    """Binance'dan barcha narxlarni olish"""
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5)
        r.raise_for_status()
        data = r.json()
        prices = {}
        for item in data:
            for coin, symbol in ALL_COINS.items():
                if item["symbol"] == symbol:
                    prices[coin] = float(item["price"])
        return prices
    except requests.RequestException as e:
        print(f"API xatosi: {e}")
        return {}
    except Exception as e:
        print(f"Kutilmagan xato: {e}")
        return {}

def build_message(state: UserState, prices: Dict[str, float]) -> str:
    """Foydalanuvchi tanlagan valyutalar uchun xabar yaratish"""
    now = datetime.now()
    t = now.strftime("%H:%M:%S")
    
    text = "💰 <b>AlphaCryptoPrice</b>\n"
    text += f"📅 {now.strftime('%d.%m.%Y')}\n"
    text += "─" * 20 + "\n\n"
    
    for coin in state.active_coins:
        price = prices.get(coin, 0)
        emoji_id = EMOJI_IDS.get(coin, "")
        if emoji_id:
            icon = f"<tg-emoji emoji-id='{emoji_id}'>🪙</tg-emoji>"
        else:
            icon = "🪙"
        
        # Narxni formatlash
        if price >= 1000:
            price_str = f"${price:,.2f}"
        elif price >= 1:
            price_str = f"${price:,.2f}"
        else:
            price_str = f"${price:.6f}"
        
        text += f"{icon} <b>{coin}</b> → {price_str}\n"
    
    text += "\n" + "─" * 20 + "\n"
    text += f"🕐 Yangilanish: {state.interval} sek\n"
    text += f"🪙 Faol valyutalar: {len(state.active_coins)} ta\n\n"
    text += "<i>/menu - Barcha buyruqlar</i>"
    
    return text

# ==================== YANGILASH FUNKSIYASI ====================
def start_updater(state: UserState):
    """Foydalanuvchi uchun auto-update thread'ini ishga tushirish"""
    if state.updater_thread and state.updater_thread.is_alive():
        return
    
    def updater():
        while state.updater_running:
            try:
                prices = get_prices()
                if prices:
                    msg = build_message(state, prices)
                    try:
                        bot.edit_message_text(
                            msg, 
                            state.chat_id, 
                            state.message_id, 
                            parse_mode="HTML"
                        )
                    except telebot.apihelper.ApiException as e:
                        if "message is not modified" not in str(e):
                            print(f"Xatolik: {e}")
                    except Exception as e:
                        print(f"Kutilmagan xato: {e}")
            except Exception as e:
                print(f"Updater xatosi: {e}")
            
            time.sleep(state.interval)
    
    state.updater_running = True
    state.updater_thread = threading.Thread(target=updater, daemon=True)
    state.updater_thread.start()

def stop_updater(state: UserState):
    """Foydalanuvchi uchun auto-update'ni to'xtatish"""
    state.updater_running = False
    if state.updater_thread:
        state.updater_thread = None

def restart_updater(state: UserState):
    """Auto-update'ni qayta ishga tushirish"""
    stop_updater(state)
    start_updater(state)

# ==================== MENU VA BUYRUQLAR ====================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    # Yangi xabar yuborish
    prices = get_prices()
    if not prices:
        bot.send_message(chat_id, "⚠️ Narxlarni yuklashda xatolik. Qayta urinib ko'ring.")
        return
    
    msg_text = build_message(state, prices)
    sent = bot.send_message(chat_id, msg_text, parse_mode="HTML")
    state.message_id = sent.message_id
    
    # Auto-updater'ni ishga tushirish
    start_updater(state)
    user_manager.save_data()
    
    # Foydalanuvchini kutib olish
    bot.send_message(chat_id, 
        "👋 <b>AlphaCryptoPrice botiga xush kelibsiz!</b>\n\n"
        "💡 /menu - Barcha buyruqlarni ko'rish\n"
        "⚙️ Sizning sozlamalaringiz avtomatik saqlanadi",
        parse_mode="HTML")

@bot.message_handler(commands=['menu'])
def show_menu(message):
    """Asosiy menyu"""
    menu_text = """
📋 <b>ALPHACRYPTOPRICE MENU</b>

🪙 <b>Valyutalar</b>
/add_coin - Yangi valyuta qo'shish
/remove_coin - Valyuta olib tashlash
/my_coins - Faol valyutalarim

⚙️ <b>Sozlamalar</b>
/set_interval - Yangilanish vaqtini o'zgartirish
/stop_updates - Yangilanishlarni to'xtatish
/start_updates - Yangilanishlarni qayta ishga tushirish

ℹ️ <b>Ma'lumot</b>
/status - Bot holati
/help - Yordam
"""
    bot.send_message(message.chat.id, menu_text, parse_mode="HTML")

@bot.message_handler(commands=['add_coin'])
def add_coin(message):
    """Yangi valyuta qo'shish (tasdiqlash bilan)"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    # Mavjud bo'lmagan valyutalar
    available = [c for c in ALL_COINS.keys() if c not in state.active_coins]
    
    if not available:
        bot.send_message(chat_id, "❌ Sizda barcha valyutalar faol! Olib tashlash uchun /remove_coin")
        return
    
    available_list = "\n".join([f"• {c}" for c in available])
    bot.send_message(chat_id, 
        f"➕ <b>Yangi valyuta qo'shish</b>\n\n"
        f"Mavjud valyutalar:\n{available_list}\n\n"
        f"📝 Qaysi valyutani qo'shmoqchisiz? (Masalan: ADA)\n\n"
        f"⚠️ <i>Bekor qilish uchun /cancel</i>",
        parse_mode="HTML")
    
    state.waiting_for_coin = True

@bot.message_handler(commands=['remove_coin'])
def remove_coin(message):
    """Valyuta olib tashlash"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    if len(state.active_coins) <= 1:
        bot.send_message(chat_id, "❌ Kamida 1 ta valyuta faol bo'lishi kerak!")
        return
    
    active_list = "\n".join([f"• {c}" for c in state.active_coins])
    bot.send_message(chat_id,
        f"➖ <b>Valyuta olib tashlash</b>\n\n"
        f"Faol valyutalaringiz:\n{active_list}\n\n"
        f"📝 Qaysi valyutani olib tashlamoqchisiz? (Masalan: DOGE)\n\n"
        f"⚠️ <i>Bekor qilish uchun /cancel</i>",
        parse_mode="HTML")
    
    state.waiting_for_coin = True
    state.waiting_for_remove = True

@bot.message_handler(commands=['my_coins'])
def my_coins(message):
    """Faol valyutalarni ko'rsatish"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    coins_list = "\n".join([f"🪙 {c}" for c in state.active_coins])
    bot.send_message(chat_id,
        f"📊 <b>Sizning faol valyutalaringiz ({len(state.active_coins)} ta)</b>\n\n"
        f"{coins_list}",
        parse_mode="HTML")

@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    """Yangilanish intervalini o'zgartirish"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    bot.send_message(chat_id,
        f"⏱ <b>Yangilanish intervalini o'zgartirish</b>\n\n"
        f"Hozirgi interval: {state.interval} sekund\n\n"
        f"📝 Yangi intervalni soniyalarda kiriting (5-60):\n\n"
        f"⚠️ <i>Bekor qilish uchun /cancel</i>",
        parse_mode="HTML")
    
    state.waiting_for_interval = True

@bot.message_handler(commands=['stop_updates'])
def stop_updates(message):
    """Yangilanishlarni to'xtatish"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    if not state.updater_running:
        bot.send_message(chat_id, "⚠️ Yangilanishlar allaqachon to'xtatilgan!")
        return
    
    stop_updater(state)
    bot.send_message(chat_id, "⏸ Yangilanishlar to'xtatildi. /start_updates bilan qayta ishga tushiring.")

@bot.message_handler(commands=['start_updates'])
def start_updates(message):
    """Yangilanishlarni qayta ishga tushirish"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    if state.updater_running:
        bot.send_message(chat_id, "⚠️ Yangilanishlar allaqachon ishlamoqda!")
        return
    
    start_updater(state)
    bot.send_message(chat_id, "▶️ Yangilanishlar qayta ishga tushirildi!")

@bot.message_handler(commands=['status'])
def status(message):
    """Bot holatini ko'rsatish"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    status_text = f"""
📊 <b>BOT HOLATI</b>

🪙 Faol valyutalar: {len(state.active_coins)} ta
⏱ Yangilanish intervali: {state.interval} sek
🔄 Yangilanish holati: {"✅ Faol" if state.updater_running else "⏸ To'xtatilgan"}
📅 Bot ishga tushgan: <i>Doimiy</i>

<b>Buyruqlar:</b>
/menu - Asosiy menyu
/help - Yordam
"""
    bot.send_message(chat_id, status_text, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def help_command(message):
    """Yordam xabari"""
    help_text = """
📚 <b>ALPHACRYPTOPRICE YORDAM</b>

<b>🪙 Valyutalar bilan ishlash</b>
/add_coin - Yangi valyuta qo'shish (tasdiqlash bilan)
/remove_coin - Valyuta olib tashlash
/my_coins - Faol valyutalarni ko'rish

<b>⚙️ Sozlamalar</b>
/set_interval - Yangilanish vaqtini o'zgartirish (5-60 sek)
/stop_updates - Yangilanishlarni vaqtincha to'xtatish
/start_updates - Yangilanishlarni qayta ishga tushirish

<b>ℹ️ Ma'lumot</b>
/menu - Asosiy menyu
/status - Bot holati
/help - Bu yordam xabari

<b>❗ Muhim:</b>
• Har qanday valyuta qo'shish yoki olib tashlashdan oldin tasdiqlash so'raladi
• Sozlamalaringiz avtomatik saqlanadi
• Kamida 1 ta valyuta faol bo'lishi kerak
"""
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

@bot.message_handler(commands=['cancel'])
def cancel(message):
    """Joriy amalni bekor qilish"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    
    state.waiting_for_coin = False
    state.waiting_for_interval = False
    if hasattr(state, 'waiting_for_remove'):
        state.waiting_for_remove = False
    
    bot.send_message(chat_id, "❌ Amal bekor qilindi. /menu orqali davom eting.")

# ==================== MATNLI XABARLARNI QAYTA ISHLASH ====================
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Foydalanuvchi kiritgan matnni qayta ishlash"""
    chat_id = message.chat.id
    state = user_manager.get_state(chat_id)
    text = message.text.upper().strip()
    
    # Interval o'zgartirish
    if state.waiting_for_interval:
        try:
            new_interval = int(text)
            if 5 <= new_interval <= 60:
                # Tasdiqlash so'rash
                bot.send_message(chat_id, 
                    f"⏱ Intervalni {new_interval} sekundga o'zgartirilsinmi?\n\n"
                    f"✅ Ha deb tasdiqlang yoki /cancel")
                
                state.waiting_for_interval = False
                state.pending_interval = new_interval
                state.waiting_for_confirm = True
            else:
                bot.send_message(chat_id, "❌ Interval 5-60 sekund orasida bo'lishi kerak!")
        except ValueError:
            bot.send_message(chat_id, "❌ Iltimos, faqat son kiriting!")
        return
    
    # Tasdiqlash
    if hasattr(state, 'waiting_for_confirm') and state.waiting_for_confirm:
        if text == "HA":
            if hasattr(state, 'pending_interval'):
                old_interval = state.interval
                state.interval = state.pending_interval
                restart_updater(state)
                user_manager.save_data()
                bot.send_message(chat_id, f"✅ Interval {old_interval} → {state.interval} sekundga o'zgartirildi!")
                delattr(state, 'pending_interval')
            elif hasattr(state, 'pending_coin'):
                if state.pending_coin in ALL_COINS:
                    state.active_coins.append(state.pending_coin)
                    restart_updater(state)
                    user_manager.save_data()
                    bot.send_message(chat_id, f"✅ {state.pending_coin} muvaffaqiyatli qo'shildi!")
                delattr(state, 'pending_coin')
            elif hasattr(state, 'pending_remove_coin'):
                if state.pending_remove_coin in state.active_coins:
                    state.active_coins.remove(state.pending_remove_coin)
                    restart_updater(state)
                    user_manager.save_data()
                    bot.send_message(chat_id, f"✅ {state.pending_remove_coin} olib tashlandi!")
                delattr(state, 'pending_remove_coin')
            state.waiting_for_confirm = False
        else:
            bot.send_message(chat_id, "❌ Amal bekor qilindi.")
            state.waiting_for_confirm = False
        return
    
    # Valyuta qo'shish yoki olib tashlash
    if state.waiting_for_coin:
        if text in ALL_COINS:
            if hasattr(state, 'waiting_for_remove') and state.waiting_for_remove:
                if text in state.active_coins:
                    if len(state.active_coins) <= 1:
                        bot.send_message(chat_id, "❌ Kamida 1 ta valyuta qolishi kerak!")
                    else:
                        # Tasdiqlash so'rash
                        bot.send_message(chat_id, 
                            f"❓ {text} ni olib tashlansinmi?\n\n"
                            f"✅ Ha deb yozing yoki /cancel")
                        state.waiting_for_coin = False
                        state.waiting_for_remove = False
                        state.pending_remove_coin = text
                        state.waiting_for_confirm = True
                else:
                    bot.send_message(chat_id, f"❌ {text} sizning faol valyutalaringizda yo'q!")
            else:
                if text in state.active_coins:
                    bot.send_message(chat_id, f"⚠️ {text} allaqachon faol!")
                else:
                    # Tasdiqlash so'rash
                    bot.send_message(chat_id, 
                        f"❓ {text} ni qo'shilsinmi?\n\n"
                        f"✅ Ha deb yozing yoki /cancel")
                    state.waiting_for_coin = False
                    state.pending_coin = text
                    state.waiting_for_confirm = True
        else:
            bot.send_message(chat_id, 
                f"❌ '{text}' noto'g'ri valyuta!\n\n"
                f"Mavjud valyutalar: {', '.join(ALL_COINS.keys())}")
        return

# ==================== BOTNI ISHGA TUSHIRISH ====================
if __name__ == "__main__":
    print("🚀 AlphaCryptoPrice bot ishga tushdi...")
    print(f"📊 {len(ALL_COINS)} ta valyuta mavjud")
    print("⚙️ Bot ishlayapti...")
    
    try:
        bot.infinity_polling(timeout=10)
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi")
    except Exception as e:
        print(f"❌ Bot xatosi: {e}")
