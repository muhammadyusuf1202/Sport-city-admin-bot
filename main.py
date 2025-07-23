import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

# Logger
logging.basicConfig(level=logging.INFO)

# Bot setup
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# DB
db = sqlite3.connect('bot.db')
cursor = db.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo TEXT,
    name TEXT,
    model TEXT,
    price TEXT,
    size TEXT,
    made_in TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    username TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT
)''')

db.commit()


# States
class AddProduct(StatesGroup):
    photo = State()
    name = State()
    model = State()
    price = State()
    size = State()
    made_in = State()


class EditProduct(StatesGroup):
    select_id = State()
    field = State()
    new_value = State()


# Utils
def is_admin(user_id):
    return user_id in ADMIN_IDS


# Start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    if is_admin(user_id):
        cursor.execute("INSERT OR IGNORE INTO admins VALUES (?, ?)", (user_id, username))
    else:
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, username))
    db.commit()
    await message.answer("Botga xush kelibsiz!")


# /add
@dp.message_handler(commands=['add'])
async def add_product(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    await message.answer("Mahsulot rasmini yuboring:")
    await AddProduct.photo.set()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddProduct.photo)
async def add_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("Mahsulot nomini kiriting:")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Modelni kiriting:")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.model)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Narxini kiriting:")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.price)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Razmeri (Bor/Yo'q):")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.size)
async def add_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("Made in qayer?")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.made_in)
async def add_madein(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO products (photo, name, model, price, size, made_in) VALUES (?, ?, ?, ?, ?, ?)",
                   (data['photo'], data['name'], data['model'], data['price'], data['size'], message.text))
    db.commit()
    await message.answer("Mahsulot qo‘shildi ✅")
    await state.finish()


# /products
@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Mahsulotlar yo‘q.")
    for row in rows:
        await bot.send_photo(message.chat.id, row[1], caption=f"🏷 {row[2]}\n📦 Model: {row[3]}\n💵 Narx: {row[4]}\n📏 Razmer: {row[5]}\n🏭 Made in: {row[6]}")


# /delete
@dp.message_handler(commands=['delete'])
async def delete_product(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    cursor.execute("SELECT id, name FROM products")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Mahsulotlar yo‘q.")
    buttons = InlineKeyboardMarkup()
    for row in rows:
        buttons.add(InlineKeyboardButton(f"{row[1]} (ID: {row[0]})", callback_data=f"del_{row[0]}"))
    await message.answer("Qaysi mahsulotni o‘chirasiz?", reply_markup=buttons)


@dp.callback_query_handler(lambda c: c.data.startswith("del_"))
async def delete_callback(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[1])
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    await call.message.edit_text("🗑 Mahsulot o‘chirildi.")


# /admins
@dp.message_handler(commands=['admins'])
async def list_admins(message: types.Message):
    cursor.execute("SELECT * FROM admins")
    rows = cursor.fetchall()
    markup = InlineKeyboardMarkup()
    for row in rows:
        markup.add(InlineKeyboardButton(f"{row[1]} (ID: {row[0]})", callback_data="none"))
    await message.answer("Adminlar ro‘yxati:", reply_markup=markup)


# /search
@dp.message_handler(commands=['search'])
async def search_product(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Bu buyruq faqat adminlar uchun.")
    query = message.get_args()
    if not query:
        return await message.answer("🔍 Nomi yoki modeli yozing: /search model yoki nom")
    cursor.execute("SELECT * FROM products WHERE name LIKE ? OR model LIKE ?", (f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    if not results:
        return await message.answer("Hech narsa topilmadi.")
    for row in results:
        await bot.send_photo(message.chat.id, row[1], caption=f"🏷 {row[2]}\n📦 Model: {row[3]}\n💵 Narx: {row[4]}\n📏 Razmer: {row[5]}\n🏭 Made in: {row[6]}")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)




# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]  # Replace with real admin ID
