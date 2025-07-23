import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = "7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU"
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("adminbot.db")
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo TEXT,
    name TEXT,
    model TEXT,
    price TEXT,
    size TEXT,
    madein TEXT
)""")
conn.commit()

STICKERS = {
    "welcome": "CAACAgUAAxkBAAEBhSxkXzS4uRhF_3ELeN78gi5KZ3KZmAAC6wIAAvcCyFYQyiUkyNud6zAE",
    "error": "CAACAgUAAxkBAAEBhTdkXzT0sjgJWk3kGh7iTyIlbEWgXgACfAEAApPjyVZ0cHHPZ3uOWjAE",
    "success": "CAACAgUAAxkBAAEBhTlkXzUV0prBvK_TyeGn6oUpoamf9AACMwADVp29CvbfblxC3KqOMwQ",
}

class AddFSM(StatesGroup):
    photo = State()
    name = State()
    model = State()
    price = State()
    size = State()
    madein = State()

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username
    if username:
        cur.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    if user_id in ADMIN_IDS:
        cur.execute("INSERT OR IGNORE INTO admins (telegram_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    await msg.answer_sticker(STICKERS["welcome"])
    await msg.answer(f"👋 Assalomu alaykum, {msg.from_user.full_name}!\nQuyidagi komandalarni ishlatishingiz mumkin:",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            "/add", "/products", "/edit", "/delete", "/search", "/admins"
        )
    )

@dp.message_handler(commands=["add"])
async def add_start(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer_sticker(STICKERS["error"])
    await msg.answer("🖼 Mahsulot rasmi yuboring:")
    await AddFSM.photo.set()

@dp.message_handler(content_types=["photo"], state=AddFSM.photo)
async def add_photo(msg: types.Message, state: FSMContext):
    await state.update_data(photo=msg.photo[-1].file_id)
    await msg.answer("📛 Mahsulot nomini yuboring:")
    await AddFSM.name.set()

@dp.message_handler(state=AddFSM.name)
async def add_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("📦 Modelini yuboring:")
    await AddFSM.model.set()

@dp.message_handler(state=AddFSM.model)
async def add_model(msg: types.Message, state: FSMContext):
    await state.update_data(model=msg.text)
    await msg.answer("💰 Narxini yuboring:")
    await AddFSM.price.set()

@dp.message_handler(state=AddFSM.price)
async def add_price(msg: types.Message, state: FSMContext):
    await state.update_data(price=msg.text)
    await msg.answer("📐 Razmer (Bor/Yoq):")
    await AddFSM.size.set()

@dp.message_handler(state=AddFSM.size)
async def add_size(msg: types.Message, state: FSMContext):
    await state.update_data(size=msg.text)
    await msg.answer("🏷 Qayerda ishlab chiqarilgan (Made in...):")
    await AddFSM.madein.set()

@dp.message_handler(state=AddFSM.madein)
async def add_done(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    cur.execute("INSERT INTO products (photo, name, model, price, size, madein) VALUES (?, ?, ?, ?, ?, ?)",
        (data["photo"], data["name"], data["model"], data["price"], data["size"], msg.text))
    conn.commit()
    await msg.answer_sticker(STICKERS["success"])
    await msg.answer("✅ Mahsulot qo‘shildi!")
    await state.finish()

@dp.message_handler(commands=["products"])
async def list_products(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer_sticker(STICKERS["error"])
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    if not rows:
        return await msg.answer("🛒 Mahsulotlar yo‘q.")
    for row in rows:
        product_id, photo, name, model, price, size, madein = row
        caption = f"<b>📛 {name}</b>\n📦 Model: {model}\n💰 Narx: {price}\n📐 Razmer: {size}\n🏷 {madein}\n🆔 ID: {product_id}"
        await msg.answer_photo(photo=photo, caption=caption, parse_mode="HTML")

@dp.message_handler(commands=["delete"])
async def delete_product(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer_sticker(STICKERS["error"])
    await msg.answer("🆔 O‘chirmoqchi bo‘lgan mahsulot ID sini yuboring:")

    @dp.message_handler()
    async def do_delete(m: types.Message):
        cur.execute("DELETE FROM products WHERE id = ?", (m.text,))
        conn.commit()
        await m.answer("🗑 O‘chirildi!")

@dp.message_handler(commands=["search"])
async def search_handler(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer_sticker(STICKERS["error"])
    await msg.answer("🔍 Qidiruv uchun model yoki nom kiriting:")

    @dp.message_handler()
    async def do_search(m: types.Message):
        q = f"%{m.text}%"
        cur.execute("SELECT * FROM products WHERE name LIKE ? OR model LIKE ?", (q, q))
        rows = cur.fetchall()
        if not rows:
            return await m.answer("❌ Topilmadi.")
        for row in rows:
            product_id, photo, name, model, price, size, madein = row
            text = f"<b>📛 {name}</b>\n📦 {model}\n💰 {price}\n📐 {size}\n🏷 {madein}"
            await m.answer_photo(photo=photo, caption=text, parse_mode="HTML")

@dp.message_handler(commands=["admins"])
async def admin_list(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer_sticker(STICKERS["error"])
    cur.execute("SELECT * FROM admins")
    admins = cur.fetchall()
    kb = InlineKeyboardMarkup(row_width=1)
    for _, telegram_id, username in admins:
        btn = InlineKeyboardButton(text=f"@{username}", url=f"https://t.me/{username}")
        kb.add(btn)
    await msg.answer("🧑‍💻 Adminlar:", reply_markup=kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)


# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

