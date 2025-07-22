import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# TOKEN & ADMIN ID
BOT_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241] 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# SQLite baza
conn = sqlite3.connect('admin_panel.db')
cursor = conn.cursor()

# Bazani yaratish
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    model TEXT,
    price INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    name TEXT,
    is_admin INTEGER
)
""")

conn.commit()


# --- Foydalanuvchini bazaga yozish ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    is_admin = 1 if telegram_id in ADMIN_IDS else 0
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, name, is_admin) VALUES (?, ?, ?)", (telegram_id, name, is_admin))
    conn.commit()
    await message.answer("Botga xush kelibsiz! Admin komandalarni ishlatish uchun: /add /products /delete /update /search")


# --- Add Product FSM ---
class AddProduct(StatesGroup):
    name = State()
    model = State()
    price = State()


@dp.message_handler(commands=['add'])
async def add_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Siz admin emassiz.")
    await message.answer("Mahsulot nomini kiriting:")
    await AddProduct.name.set()


@dp.message_handler(state=AddProduct.name)
async def add_model(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Modelini kiriting:")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.model)
async def add_price(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Narxini kiriting (son):")
    await AddProduct.next()


@dp.message_handler(state=AddProduct.price)
async def add_finish(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        return await message.answer("Narx noto‘g‘ri formatda. Qayta kiriting:")
    
    data = await state.get_data()
    cursor.execute("INSERT INTO products (name, model, price) VALUES (?, ?, ?)", (data['name'], data['model'], price))
    conn.commit()
    await message.answer("✅ Mahsulot qo‘shildi!", reply_markup=ReplyKeyboardRemove())
    await state.finish()


# --- Show Products ---
@dp.message_handler(commands=['products'])
async def list_products(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    cursor.execute("SELECT id, name, model, price FROM products")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("Mahsulotlar topilmadi.")
    for r in rows:
        await message.answer(f"ID: {r[0]}\nNomi: {r[1]}\nModel: {r[2]}\nNarxi: {r[3]} so'm")


# --- Delete Product ---
@dp.message_handler(commands=['delete'])
async def delete_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("O‘chirmoqchi bo‘lgan mahsulot ID sini yuboring:")

    @dp.message_handler(lambda msg: msg.text.isdigit())
    async def confirm_delete(msg: types.Message):
        product_id = int(msg.text)
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        await msg.answer("🗑 Mahsulot o‘chirildi!")


# --- Update Product ---
class UpdateProduct(StatesGroup):
    id = State()
    name = State()
    model = State()
    price = State()

@dp.message_handler(commands=['update'])
async def update_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Yangilamoqchi bo‘lgan mahsulot ID sini yuboring:")
    await UpdateProduct.id.set()

@dp.message_handler(state=UpdateProduct.id)
async def update_name(message: types.Message, state: FSMContext):
    await state.update_data(id=int(message.text))
    await message.answer("Yangi nomi:")
    await UpdateProduct.next()

@dp.message_handler(state=UpdateProduct.name)
async def update_model(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Yangi modeli:")
    await UpdateProduct.next()

@dp.message_handler(state=UpdateProduct.model)
async def update_price(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Yangi narxi:")
    await UpdateProduct.next()

@dp.message_handler(state=UpdateProduct.price)
async def update_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        price = int(message.text)
    except:
        return await message.answer("Narx noto‘g‘ri.")
    cursor.execute("UPDATE products SET name=?, model=?, price=? WHERE id=?", 
                   (data['name'], data['model'], price, data['id']))
    conn.commit()
    await message.answer("Mahsulot yangilandi!")
    await state.finish()


# --- Admins ro‘yxati ---
@dp.message_handler(commands=['admins'])
async def show_admins(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    cursor.execute("SELECT name, telegram_id FROM users WHERE is_admin=1")
    rows = cursor.fetchall()
    text = "👮‍♂️ Adminlar ro‘yxati:\n\n" + "\n".join([f"{r[0]} - {r[1]}" for r in rows])
    await message.answer(text)


# --- Search by name or model ---
@dp.message_handler(commands=['search'])
async def search_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Qidirilayotgan nom yoki modelni kiriting:")

    @dp.message_handler()
    async def search_by_text(msg: types.Message):
        text = msg.text
        cursor.execute("SELECT id, name, model, price FROM products WHERE name LIKE ? OR model LIKE ?", 
                       (f"%{text}%", f"%{text}%"))
        rows = cursor.fetchall()
        if not rows:
            await msg.answer("Hech nima topilmadi.")
        else:
            for r in rows:
                await msg.answer(f"ID: {r[0]}\nNomi: {r[1]}\nModel: {r[2]}\nNarxi: {r[3]} so'm")


# --- Bot ishga tushadi ---
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)


# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]  # Replace with real admin ID
