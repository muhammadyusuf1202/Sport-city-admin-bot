
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import logging

API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]  # Replace with real admin IDs

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

# Database setup
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    name TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    model TEXT,
    price INTEGER,
    made_in TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    location TEXT,
    payment_method TEXT
)
''')
conn.commit()

class OrderStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_location = State()
    waiting_for_confirmation = State()

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)',
                   (message.from_user.id, message.from_user.full_name))
    conn.commit()
    await message.answer("Xush kelibsiz! /products buyrug‘i orqali mahsulotlarni ko‘rishingiz mumkin.")

@dp.message_handler(commands=['products'])
async def list_products(message: types.Message):
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    if not products:
        return await message.answer('Mahsulotlar mavjud emas.')
    for product in products:
        btn = InlineKeyboardMarkup().add(InlineKeyboardButton('Zakaz berish', callback_data=f'order_{product[0]}'))
        await message.answer(f"🛍 {product[1]}\nModel: {product[2]}\nNarx: {product[3]}\nDavlat: {product[4]}",
reply_markup=btn)

@dp.callback_query_handler(lambda c: c.data.startswith('order_'))
async def order_product(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split('_')[1])
    await state.update_data(product_id=product_id)
    await bot.send_message(callback_query.from_user.id, '📍 Manzilingizni matn ko‘rinishida yuboring.')
    await OrderStates.waiting_for_location.set()

@dp.message_handler(state=OrderStates.waiting_for_location)
async def handle_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    data = await state.get_data()
    product_id = data['product_id']
    location = data['location']
    cursor.execute('INSERT INTO orders (user_id, product_id, location, payment_method) VALUES (?, ?, ?, ?)',
                   (message.from_user.id, product_id, location, 'Naqd'))
    conn.commit()
    cursor.execute('SELECT name FROM products WHERE id=?', (product_id,))
    product_name = cursor.fetchone()[0]
    for admin in ADMIN_IDS:
        await bot.send_message(admin,
            f"🆕 Yangi zakaz:👤 {message.from_user.full_name} (@{message.from_user.username}"
            f"📦 Mahsulot: {product_name}📍 Manzil: {location}💵 To‘lov: Naqd" )
    await message.answer("✅ Buyurtmangiz qabul qilindi!")
    await state.finish()

@dp.message_handler(commands=['add'])
async def add_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Siz admin emassiz!")
    try:
        _, name, model, price, made_in = message.text.split(',')
        cursor.execute('INSERT INTO products (name, model, price, made_in) VALUES (?, ?, ?, ?)',
                       (name.strip(), model.strip(), int(price), made_in.strip()))
        conn.commit()
        await message.answer("✅ Mahsulot muvaffaqiyatli qo‘shildi.")
    except:
        await message.answer("❌ Format noto‘g‘ri. Format: /add nom,model,narx,country")

@dp.message_handler(commands=['edit'])
async def edit_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Siz admin emassiz!")
    try:
        _, id_, name, model, price, made_in = message.text.split(',')
        cursor.execute('UPDATE products SET name=?, model=?, price=?, made_in=? WHERE id=?',
                       (name.strip(), model.strip(), int(price), made_in.strip(), int(id_)))
        conn.commit()
        await message.answer("✅ Mahsulot yangilandi.")
    except:
        await message.answer("❌ Format noto‘g‘ri. Format: /edit id,nom,model,narx,country")

@dp.message_handler(commands=['delete'])
async def delete_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Siz admin emassiz!")
    try:
        _, id_ = message.text.split()
        cursor.execute('DELETE FROM products WHERE id=?', (int(id_),))
        conn.commit()
        await message.answer("🗑 Mahsulot o‘chirildi.")
    except:
        await message.answer("❌ Format: /delete id")

@dp.message_handler(commands=['search_model'])
async def search_by_model(message: types.Message):
    model = message.get_args()
    cursor.execute('SELECT * FROM products WHERE model LIKE ?', ('%' + model + '%',))
    products = cursor.fetchall()
    if not products:
        return await message.answer('Model bo‘yicha topilmadi.')
    for product in products:
        await message.answer(f"🛍 {product[1]}\nModel: {product[2]}\nNarx: {product[3]}\nDavlat: {product[4]}")

@dp.message_handler(commands=['search_nomi'])
async def search_by_name(message: types.Message):
    name = message.get_args()
    cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%' + name + '%',))
    products = cursor.fetchall()
    if not products:
        return await message.answer('Nomi bo‘yicha topilmadi.')
    for product in products:
        await message.answer(f"🛍 {product[1]}\nModel: {product[2]}\nNarx: {product[3]}\nDavlat: {product[4]}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
