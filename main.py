# Full implementation of user/admin roles, product order, and admin notification

import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentType, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from datetime import datetime

API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMINS = [807995985, 5751536492, 7435391786, 266461241]  # Admin Telegram IDs
SELLER_CARD = "5614 8600 0311 6783"  # Sotuvchining karta raqami

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Database initialization
def init_db():
    conn = sqlite3.connect("sport_city.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            username TEXT,
            first_join TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            model TEXT UNIQUE,
            made_in TEXT,
            image TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            address TEXT,
            payment TEXT,
            method TEXT,
            created_at TEXT,
            user_card TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    return user_id in ADMINS

class OrderFSM(StatesGroup):
    product_id = State()
    method = State()
    address = State()
    payment = State()
    user_card = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username
    joined_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, full_name, username, first_join) VALUES (?, ?, ?, ?)",
                   (user_id, full_name, username, joined_time))
    conn.commit()
    conn.close()

    if is_admin(user_id):
        await message.answer("🔐 Admin Panel:\n/products – Mahsulotlar\n/add – Qo‘shish\n/edit – Tahrirlash\n/delete – O‘chirish")
    else:
        await message.answer("🎉 Xush kelibsiz!\n/products – Mahsulotlar ko‘rish\n/savat – Savatni ko‘rish")

@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    conn = sqlite3.connect("sport_city.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        await message.answer("❌ Mahsulot yo‘q.")
        return

    kb = InlineKeyboardMarkup()
    for pid, name in products:
        kb.add(InlineKeyboardButton(text=name, callback_data=f"view_{pid}"))
    await message.answer("🛍 Mahsulotlardan tanlang:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("view_"))
async def view_product(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    conn = sqlite3.connect("sport_city.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, model, made_in, image FROM products WHERE id=?", (pid,))
    product = cursor.fetchone()
    conn.close()

    if product:
        name, price, model, made_in, image = product
        caption = f"📦 {name}\n💰 {price} so'm\n🔢 {model}\n🌍 {made_in}"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🛒 Zakaz qilish", callback_data=f"order_{pid}"))
        await bot.send_photo(call.from_user.id, image, caption=caption, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def order_product(call: types.CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    await state.update_data(product_id=pid)
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🏪 Do‘konga boraman", callback_data="method_shop"),
        InlineKeyboardButton("🚚 Yetkazib berilsin", callback_data="method_delivery")
    )
    await call.message.answer("Qanday usulda olasiz?", reply_markup=kb)
    await OrderFSM.method.set()

@dp.callback_query_handler(lambda c: c.data.startswith("method_"), state=OrderFSM.method)
async def choose_method(call: types.CallbackQuery, state: FSMContext):
    method = call.data.split("_")[1]
    await state.update_data(method=method)
    if method == "delivery":
        await call.message.answer("Manzilingizni kiriting:")
        await OrderFSM.address.set()
    else:
        await state.update_data(address="Do‘kondan olib ketaman")
        await ask_payment(call.message, state)

@dp.message_handler(state=OrderFSM.address)
async def enter_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await ask_payment(message, state)

async def ask_payment(message, state):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("💳 Karta", callback_data="pay_card"),
        InlineKeyboardButton("💵 Naqd", callback_data="pay_cash")
    )
    await message.answer("To‘lov usulini tanlang:", reply_markup=kb)
    await OrderFSM.payment.set()

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"), state=OrderFSM.payment)
async def enter_payment(call: types.CallbackQuery, state: FSMContext):
    payment = call.data.split("_")[1]
    await state.update_data(payment=payment)

    if payment == "card":
        await call.message.answer(f"💳 Sotuvchining karta raqami: {SELLER_CARD} siz Payme yoki Click orqali to'lashingiz mumkin \nEndi o‘z kartangiz raqamini kiriting:")
        await OrderFSM.user_card.set()
    else:
        await finalize_order(call.message, state, user_card="Naqd")

@dp.message_handler(state=OrderFSM.user_card)
async def get_user_card(message: types.Message, state: FSMContext):
    user_card = message.text
    await finalize_order(message, state, user_card=user_card)

async def finalize_order(message, state, user_card):
    user_data = await state.get_data()
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username or "-"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("sport_city.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, product_id, address, payment, method, created_at, user_card) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, user_data['product_id'], user_data['address'], user_data['payment'], user_data['method'], now, user_card))

    cursor.execute("SELECT name FROM products WHERE id=?", (user_data['product_id'],))
    product_name = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    await message.answer("✅ Zakazingiz qabul qilindi!")
    for admin_id in ADMINS:
        await bot.send_message(admin_id, f"📦 Yangi zakaz!\n👤 {full_name} (@{username})\n🛍 {product_name}\n📍 {user_data['address']}\n💳 To‘lov: {user_data['payment']}\n💳 Foydalanuvchi karta: {user_card}")

    await state.finish()

@dp.message_handler(commands=['savat'])
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("sport_city.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.name, o.created_at, o.payment FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
    """, (user_id,))
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        await message.answer("🛒 Savat bo‘sh.")
        return

    text = "🧾 Sizning zakazlaringiz:\n"
    for name, time, pay in orders:
        text += f"📦 {name}\n🕒 {time}\n💳 {pay}\n\n"
    await message.answer(text)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
