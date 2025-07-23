import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
import asyncio

API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]
bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ===== STICKERS =====
STICKER_WELCOME = "CAACAgIAAxkBAAEF8oxkZG7EyNgY3B2uUWoAAZdAbQABTqPyAQACZSoAAulDYUsKSSfzPzQjBA"
STICKER_OK = "CAACAgIAAxkBAAEF8o5kZG7h4CKxqU5dzKD8TZQAAUYbh7YAAu1XAAJWnb0KPHp7rUqHcRskBA"
STICKER_ERROR = "CAACAgIAAxkBAAEF8pBkZG7k0V4rUDeMrdvKhC3lLEaSPgACbhAAAmwsrQo07oMoFeRmRS8E"

# ===== DATABASE =====
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    model TEXT,
    price INTEGER,
    size TEXT,
    made_in TEXT,
    image TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    telegram_id INTEGER PRIMARY KEY
)''')
conn.commit()

# Save user
async def save_user(user: types.User):
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (user.id, user.username))
    conn.commit()

# Add admins
for admin_id in ADMIN_IDS:
    cursor.execute("INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)", (admin_id,))
conn.commit()

# ===== STATES =====
class AddProduct(StatesGroup):
    name = State()
    model = State()
    price = State()
    size = State()
    made_in = State()
    image = State()

# ====== /start ======
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await save_user(message.from_user)
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer_sticker(STICKER_WELCOME)
    if is_admin:
        await message.answer(
            "👋 <b>Admin panelga xush kelibsiz!</b>\n\nQuyidagilar mavjud:\n"
            "/add – ➕ Mahsulot qo‘shish\n"
            "/products – 📦 Barcha mahsulotlar\n"
            "/edit – ✏️ Mahsulotni tahrirlash\n"
            "/delete – ❌ Mahsulotni o‘chirish\n"
            "/admins – 👮‍♂️ Adminlar ro‘yxati\n"
            "/search – 🔍 Qidiruv (nomi yoki model)",
        )
    else:
        await message.answer("🤖 Bu bot adminlar uchun mo‘ljallangan. Siz foydalanuvchisiz.")
        await message.answer_sticker(STICKER_ERROR)

# ====== /add ======
@dp.message(Command("add"))
async def add_product(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz.")
        return
    await state.set_state(AddProduct.name)
    await message.answer("📝 Mahsulot nomini kiriting:")

@dp.message(AddProduct.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.model)
    await message.answer("🔤 Mahsulot modelini kiriting:")

@dp.message(AddProduct.model)
async def add_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("💰 Narxini kiriting (raqam):")

@dp.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❗ Raqam kiriting.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProduct.size)
    await message.answer("📏 Razmer bormi? (Bor/Yo‘q):")

@dp.message(AddProduct.size)
async def add_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text)
    await state.set_state(AddProduct.made_in)
    await message.answer("🌍 Qayerda ishlab chiqarilgan? (Masalan: Made in China):")

@dp.message(AddProduct.made_in)
async def add_made_in(message: Message, state: FSMContext):
    await state.update_data(made_in=message.text)
    await state.set_state(AddProduct.image)
    await message.answer("📸 Mahsulot rasmini yuboring (1 dona):")

@dp.message(AddProduct.image)
async def add_image(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("❗ Rasm yuboring.")
        return
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    cursor.execute('''INSERT INTO products (name, model, price, size, made_in, image)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (data['name'], data['model'], data['price'], data['size'], data['made_in'], file_id))
    conn.commit()
    await message.answer_sticker(STICKER_OK)
    await message.answer("✅ Mahsulot qo‘shildi!")
    await state.clear()

# ====== /products ======
@dp.message(Command("products"))
async def list_products(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz.")
        return
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("📦 Mahsulotlar mavjud emas.")
    for row in rows:
        id, name, model, price, size, made_in, image = row
        caption = f"<b>{name}</b>\nModel: {model}\nNarx: {price} so‘m\nRazmer: {size}\n{made_in}"
        await message.answer_photo(image, caption=caption)

# ====== /delete ======
@dp.message(Command("delete"))
async def delete_product(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz.")
        return
    cursor.execute("SELECT id, name FROM products")
    rows = cursor.fetchall()
    keyboard = InlineKeyboardBuilder()
    for row in rows:
        keyboard.button(text=row[1], callback_data=f"delete_{row[0]}")
    await message.answer("🗑 O‘chirmoqchi bo‘lgan mahsulotni tanlang:", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def confirm_delete(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    await callback.message.answer_sticker(STICKER_OK)
    await callback.message.answer("✅ Mahsulot o‘chirildi.")
    await callback.answer()

# ====== /admins ======
@dp.message(Command("admins"))
async def list_admins(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz.")
        return
    cursor.execute("SELECT telegram_id FROM admins")
    rows = cursor.fetchall()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👮‍♂️ @{(await bot.get_chat(admin[0])).username}", callback_data="noop")] for admin in rows
    ])
    await message.answer("👮‍♂️ Adminlar ro‘yxati:", reply_markup=kb)

# ====== /search ======
@dp.message(Command("search"))
async def search_prompt(message: Message):
    await message.answer("🔎 Nomi yoki modelini kiriting:")

@dp.message(lambda msg: msg.text and not msg.text.startswith("/"))
async def search_products(message: Message):
    text = f"%{message.text}%"
    cursor.execute("SELECT * FROM products WHERE name LIKE ? OR model LIKE ?", (text, text))
    rows = cursor.fetchall()
    if not rows:
        await message.answer("❗ Mahsulot topilmadi.")
        return
    for row in rows:
        id, name, model, price, size, made_in, image = row
        caption = f"<b>{name}</b>\nModel: {model}\nNarx: {price} so‘m\nRazmer: {size}\n{made_in}"
        await message.answer_photo(image, caption=caption)

# ===== MAIN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

