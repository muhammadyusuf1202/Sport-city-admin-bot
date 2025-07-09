import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor


API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'  # <-- Bu yerga o'zingizning bot tokeningizni yozing

from datetime import datetime

# API_TOKEN = 'YOUR_BOT_TOKEN'  # <-- o'zingizning bot tokeningizni yozing


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('sport_city.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            model TEXT,
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

    conn.commit()
    conn.close()

init_db()

# --- STATES ---
class ProductAdd(StatesGroup):
    name = State()
    price = State()
    model = State()
    made_in = State()
    image = State()

class SearchProduct(StatesGroup):
    query = State()


# --- START ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🔐 Panel:\n/add – Mahsulot qo‘shish\n/products – Mahsulotlar ro‘yxati\n/search – Qidiruv")


class EditProduct(StatesGroup):
    model = State()
    name = State()
    price = State()
    made_in = State()
    image = State()

class DeleteProduct(StatesGroup):
    model = State()

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

    await message.answer("🔐Admin Panel:\n/add – Mahsulot qo‘shish\n/products – Mahsulotlar ro‘yxati\n/search – Qidiruv\n/edit – Mahsulot tahrirlash\n/delete – Mahsulot o‘chirish")

# --- ADD PRODUCT ---

@dp.message_handler(commands=['add'])
async def add_product(message: types.Message):
    await message.answer("📦 Mahsulot nomini kiriting:")
    await ProductAdd.name.set()

@dp.message_handler(state=ProductAdd.name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Narxini kiriting:")
    await ProductAdd.price.set()

@dp.message_handler(state=ProductAdd.price)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("🔢 Model nomini kiriting:")
    await ProductAdd.model.set()

@dp.message_handler(state=ProductAdd.model)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("🌍 Qayerda ishlab chiqarilganini kiriting:")
    await ProductAdd.made_in.set()

@dp.message_handler(state=ProductAdd.made_in)
async def add_madein(message: types.Message, state: FSMContext):
    await state.update_data(made_in=message.text)
    await message.answer("🖼 Rasm yuboring:")
    await ProductAdd.image.set()

@dp.message_handler(content_types=ContentType.PHOTO, state=ProductAdd.image)
async def add_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id

    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price, model, made_in, image) VALUES (?, ?, ?, ?, ?)",
                   (data['name'], data['price'], data['model'], data['made_in'], photo_id))
    conn.commit()
    conn.close()

    await message.answer("✅ Mahsulot qo‘shildi!")
    await state.finish()

# --- SHOW PRODUCTS ---
@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    conn = sqlite3.connect('sport_city.db')
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
    await message.answer("🗂 Mahsulotlar ro‘yxati:", reply_markup=kb)


# --- VIEW PRODUCT ---

@dp.callback_query_handler(lambda c: c.data.startswith("view_"))
async def view_product(call: types.CallbackQuery):
    pid = int(call.data.split("_")[1])
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, model, made_in, image FROM products WHERE id=?", (pid,))
    product = cursor.fetchone()
    conn.close()

    if product:
        name, price, model, made_in, image = product
        await bot.send_photo(call.from_user.id, image,
            caption=f"📦 {name}\n💰 Narx: {price} so‘m\n🔢 Model: {model}\n🌍 Ishlab chiqarilgan: {made_in}")
    else:
        await call.message.answer("❌ Mahsulot topilmadi.")


# --- SEARCH COMMAND ---

# --- SEARCH ---

@dp.message_handler(commands=['search'])
async def search_start(message: types.Message):
    await message.answer("🔍 Qidiruv uchun model yoki nomni kiriting:")
    await SearchProduct.query.set()

@dp.message_handler(state=SearchProduct.query)
async def search_product(message: types.Message, state: FSMContext):
    query = message.text
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products WHERE name LIKE ? OR model LIKE ?", (f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    conn.close()

    if results:
        kb = InlineKeyboardMarkup()
        for pid, name in results:
            kb.add(InlineKeyboardButton(text=name, callback_data=f"view_{pid}"))
        await message.answer("🔎 Natijalar:", reply_markup=kb)
    else:
        await message.answer("❌ Hech narsa topilmadi.")
    await state.finish()


# --- RUN ---
# if __name__ == '__main__':

# --- DELETE PRODUCT ---
@dp.message_handler(commands=['delete'])
async def delete_start(message: types.Message):
    await message.answer("❌ O‘chirmoqchi bo‘lgan mahsulot modelini yozing:")
    await DeleteProduct.model.set()

@dp.message_handler(state=DeleteProduct.model)
async def delete_model(message: types.Message, state: FSMContext):
    model = message.text
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE model = ?", (model,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted:
        await message.answer("🗑 Mahsulot o‘chirildi.")
    else:
        await message.answer("❌ Mahsulot topilmadi.")
    await state.finish()

# --- EDIT PRODUCT ---
@dp.message_handler(commands=['edit'])
async def edit_start(message: types.Message):
    await message.answer("✏️ O‘zgartirmoqchi bo‘lgan mahsulot modelini yozing:")
    await EditProduct.model.set()

@dp.message_handler(state=EditProduct.model)
async def edit_model(message: types.Message, state: FSMContext):
    model = message.text
    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE model = ?", (model,))
    product = cursor.fetchone()
    conn.close()

    if product:
        await state.update_data(model=model)
        await message.answer("🆕 Yangi nomni kiriting:")
        await EditProduct.name.set()
    else:
        await message.answer("❌ Mahsulot topilmadi.")
        await state.finish()

@dp.message_handler(state=EditProduct.name)
async def edit_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Yangi narxni kiriting:")
    await EditProduct.price.set()

@dp.message_handler(state=EditProduct.price)
async def edit_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("🌍 Yangi ishlab chiqarilgan joyni kiriting:")
    await EditProduct.made_in.set()

@dp.message_handler(state=EditProduct.made_in)
async def edit_madein(message: types.Message, state: FSMContext):
    await state.update_data(made_in=message.text)
    await message.answer("🖼 Yangi rasm yuboring:")
    await EditProduct.image.set()

@dp.message_handler(content_types=ContentType.PHOTO, state=EditProduct.image)
async def edit_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id

    conn = sqlite3.connect('sport_city.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products
        SET name = ?, price = ?, made_in = ?, image = ?
        WHERE model = ?
    """, (data['name'], data['price'], data['made_in'], photo_id, data['model']))
    conn.commit()
    conn.close()

    await message.answer("✅ Mahsulot yangilandi!")
    await state.finish()

# --- RUN ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
