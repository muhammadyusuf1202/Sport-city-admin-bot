# To'liq ishlaydigan admin paneli va foydalanuvchi uchun bot kodini tayyorlash

import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from datetime import datetime

API_TOKEN = 'YOUR_BOT_TOKEN'  # <-- bu yerga tokeningizni yozing
ADMINS = [123456789, 987654321]  # <-- admin telegram ID lar

SELLER_CARD = "8600123456789012"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Database
def init_db():
    conn = sqlite3.connect('sport_city.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            model TEXT UNIQUE,
            made_in TEXT,
            image TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            username TEXT,
            first_join TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            product_id INTEGER,
            delivery_type TEXT,
            address TEXT,
            payment_type TEXT,
            user_card TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    return user_id in ADMINS

# --- START ---
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
        await message.answer("🔐 *Admin Panel:*\n/add – Qo‘shish\n/edit – Tahrirlash\n/delete – O‘chirish\n/products – Mahsulotlar", parse_mode="Markdown")
    else:
        await message.answer("👤 Xush kelibsiz! Siz foydalanuvchisiz.\n/products – Mahsulotlar\n/savat – Savat", parse_mode="Markdown")

# --- STATES ---
class AddProductFSM(StatesGroup):
    name = State()
    price = State()
    model = State()
    made_in = State()
    image = State()

@dp.message_handler(commands=['add'])
async def admin_add(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Siz admin emassiz.")
    await message.answer("📦 Mahsulot nomini kiriting:")
    await AddProductFSM.name.set()

@dp.message_handler(state=AddProductFSM.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Narxini kiriting:")
    await AddProductFSM.price.set()

@dp.message_handler(state=AddProductFSM.price)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("🔢 Model nomini kiriting:")
    await AddProductFSM.model.set()

@dp.message_handler(state=AddProductFSM.model)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("🌍 Ishlab chiqarilgan joy:")
    await AddProductFSM.made_in.set()

@dp.message_handler(state=AddProductFSM.made_in)
async def add_madein(message: types.Message, state: FSMContext):
    await state.update_data(made_in=message.text)
    await message.answer("🖼 Rasm yuboring:")
    await AddProductFSM.image.set()

@dp.message_handler(content_types=ContentType.PHOTO, state=AddProductFSM.image)
async def add_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price, model, made_in, image) VALUES (?, ?, ?, ?, ?)",
                   (data['name'], data['price'], data['model'], data['made_in'], photo_id))
    conn.commit()
    conn.close()
    await message.answer("✅ Mahsulot qo‘shildi.")
    await state.finish()

# PRODUCTS – Both Admin and Users
@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()
    conn.close()
    if not products:
        return await message.answer("❌ Mahsulot yo‘q.")

    kb = InlineKeyboardMarkup()
    for pid, name in products:
        kb.add(InlineKeyboardButton(name, callback_data=f"product_{pid}"))
    await message.answer("🛍 Mahsulotlardan tanlang:", reply_markup=kb)

# VIEW PRODUCT – for All
@dp.callback_query_handler(lambda c: c.data.startswith("product_"))
async def view_product(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, model, made_in, image FROM products WHERE id=?", (pid,))
    product = cursor.fetchone()
    conn.close()
    if not product:
        return await call.message.answer("❌ Mahsulot topilmadi.")
    name, price, model, made_in, image = product
    caption = f"📦 {name}\n💰 {price} so‘m\n🔢 {model}\n🌍 {made_in}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Zakaz qilish", callback_data=f"buy_{pid}"))
    await bot.send_photo(call.from_user.id, image, caption=caption, reply_markup=kb)

# BUY
class OrderFSM(StatesGroup):
    delivery = State()
    address = State()
    payment = State()
    user_card = State()
    product_id = State()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def start_order(call: types.CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    await state.update_data(product_id=pid)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("📍 Yetkazib berish", callback_data="delivery"),
           InlineKeyboardButton("🏬 Do‘kondan olish", callback_data="pickup"))
    await call.message.answer("📦 Qanday olishni tanlang:", reply_markup=kb)
    await OrderFSM.delivery.set()

@dp.callback_query_handler(lambda c: c.data in ["delivery", "pickup"], state=OrderFSM.delivery)
async def delivery_type(call: types.CallbackQuery, state: FSMContext):
    if call.data == "delivery":
        await call.message.answer("📍 Manzilni yozing:")
        await state.update_data(delivery_type="Yetkazib berish")
        await OrderFSM.address.set()
    else:
        await call.message.answer("🏬 Do‘kon manzili: Toshkent, Chilonzor 10\nTo‘lov turini tanlang:")
        await state.update_data(delivery_type="Do‘kondan olish", address="-")
        await ask_payment(call.message, state)

@dp.message_handler(state=OrderFSM.address)
async def save_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await ask_payment(message, state)

async def ask_payment(message, state):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("💳 Karta", callback_data="pay_card"),
           InlineKeyboardButton("💵 Naqd", callback_data="pay_cash"))
    await message.answer("💰 To‘lov turini tanlang:", reply_markup=kb)
    await OrderFSM.payment.set()

@dp.callback_query_handler(lambda c: c.data in ["pay_card", "pay_cash"], state=OrderFSM.payment)
async def payment_type(call: types.CallbackQuery, state: FSMContext):
    if call.data == "pay_card":
        await state.update_data(payment_type="Karta")
        await call.message.answer(f"💳 Sotuvchi kartasi: {SELLER_CARD}\n✅ Endi o‘z kartangizni kiriting:")
        await OrderFSM.user_card.set()
    else:
        await state.update_data(payment_type="Naqd", user_card="-")
        await finalize_order(call.message, state)

@dp.message_handler(state=OrderFSM.user_card)
async def save_user_card(message: types.Message, state: FSMContext):
    await state.update_data(user_card=message.text)
    await finalize_order(message, state)

async def finalize_order(message, state):
    data = await state.get_data()
    user = message.from_user
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (telegram_id, product_id, delivery_type, address, payment_type, user_card) VALUES (?, ?, ?, ?, ?, ?)",
                   (user.id, data['product_id'], data['delivery_type'], data['address'], data['payment_type'], data['user_card']))
    conn.commit()
    cursor.execute("SELECT name FROM products WHERE id = ?", (data['product_id'],))
    product_name = cursor.fetchone()[0]
    conn.close()
    await message.answer("✅ Siz mahsulotga zakaz berdingiz!")

    # Adminlarga yuborish
    for admin_id in ADMINS:
        await bot.send_message(admin_id,
            f"📦 Yangi zakaz:\n👤 {user.full_name} (@{user.username})\n🛒 {product_name}\n🚚 {data['delivery_type']}\n📍 {data['address']}\n💰 {data['payment_type']}\n💳 Karta: {data['user_card']}")
    await state.finish()

# SAVAT
@dp.message_handler(commands=['savat'])
async def show_cart(message: types.Message):
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT p.name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.telegram_id = ?", (message.from_user.id,))
    items = cursor.fetchall()
    conn.close()
    if items:
        text = "🛒 Siz olgan mahsulotlar:\n" + "\n".join([f"- {item[0]}" for item in items])
        await message.answer(text)
    else:
        await message.answer("🛒 Savatingiz bo‘sh.")

# RUN
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
