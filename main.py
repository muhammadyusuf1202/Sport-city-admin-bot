# from aiogram import executor
import sqlite3
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Bot token va admin IDlari
API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# SQLite bazasini tashkil etish
conn = sqlite3.connect("bot_db.sqlite3")
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
    admin_id INTEGER,
    image_id TEXT,
    name TEXT,
    model TEXT,
    price TEXT,
    size_status TEXT,
    size_value TEXT,
    made_in TEXT
)""")
conn.commit()

# FSM holatlari: mahsulot qo‘shish bosqichi
class AddProduct(StatesGroup):
    image = State()
    name = State()
    model = State()
    price = State()
    size_status = State()
    size_value = State()
    made_in = State()

# /start komandasi handler
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.full_name
    cur.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (uid, uname))
    conn.commit()
    if uid in ADMIN_IDS:
        cur.execute("INSERT OR IGNORE INTO admins (telegram_id, username) VALUES (?, ?)", (uid, uname))
        conn.commit()
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("/add", "/products")
        markup.add("/edit", "/delete")
        markup.add("/search", "/admins")
        await message.answer("👋 Salom, Admin! Quyidagi komandalar mavjud:", reply_markup=markup)
    else:
        await message.answer("👋 Xush kelibsiz! Siz oddiy foydalanuvchisiz.")

# /add komandasi bosilganda
@dp.message_handler(commands=['add'])
async def add_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz.")
    await message.answer("📷 Mahsulot rasmini yuboring:")
    await AddProduct.image.set()
@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddProduct.image)
async def process_image(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(image_id=file_id)
    await message.answer("📝 Mahsulot nomini kiriting:")
    await AddProduct.next()

@dp.message_handler(state=AddProduct.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("🔢 Model nomini kiriting:")
    await AddProduct.next()

@dp.message_handler(state=AddProduct.model)
async def process_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text.strip())
    await message.answer("💰 Narxini kiriting:")
    await AddProduct.next()

@dp.message_handler(state=AddProduct.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Bor", callback_data="size_bor"),
           InlineKeyboardButton("Yo'q", callback_data="size_yoq"))
    await message.answer("📏 Razmer mavjudmi? (Bor/Yo'q)", reply_markup=kb)
    await AddProduct.next()

@dp.callback_query_handler(lambda c: c.data in ["size_bor", "size_yoq"], state=AddProduct.size_status)
async def process_size_status(c: types.CallbackQuery, state: FSMContext):
    status = "Bor" if c.data == "size_bor" else "Yo'q"
    await state.update_data(size_status=status)
    if status == "Bor":
        await bot.send_message(c.from_user.id, "📏 Iltimos, razmer qiymatini kiriting (masalan: 40, M, L):")
        await AddProduct.size_value.set()
    else:
        # agar yo‘q bo‘lsa razmer qiymati "-" bo‘ladi
        await state.update_data(size_value="-")
        await bot.send_message(c.from_user.id, "🏭 Qayerda ishlab chiqarilganligini kiriting:")
        await AddProduct.made_in.set()
    await c.answer()

@dp.message_handler(state=AddProduct.size_value)
async def process_size_value(message: types.Message, state: FSMContext):
    await state.update_data(size_value=message.text.strip())
    await message.answer("🏭 Iltimos, mahsulot qayerda ishlab chiqarilganini kiriting:")
    await AddProduct.next()

@dp.message_handler(state=AddProduct.made_in)
async def process_made_in(message: types.Message, state: FSMContext):
    await state.update_data(made_in=message.text.strip())
    data = await state.get_data()
    cur.execute("""
        INSERT INTO products (admin_id, image_id, name, model, price, size_status, size_value, made_in)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (message.from_user.id,
          data['image_id'], data['name'], data['model'], data['price'],
          data['size_status'], data['size_value'], data['made_in']))
    conn.commit()
    await message.answer("✅ Mahsulot muvaffaqiyatli qo‘shildi!")
    await state.finish()
@dp.message_handler(commands=['products'])
async def cmd_products(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Bu buyruq faqat adminlar uchun")
    cur.execute("SELECT id, name, model, price, size_status, size_value, made_in, image_id FROM products")
    items = cur.fetchall()
    if not items:
        return await message.answer("📭 Mahsulotlar mavjud emas.")
    for item in items:
        pid, name, model_, price_, sz_stat, sz_val, made_in_, img_id = item
        cap = f"<b>{name}</b>\n📦 Model: {model_}\n💰 Narx: {price_}\n📏 Razmer: {sz_stat} ({sz_val})\n🏷 {made_in_}"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📝 Tahrirlash", callback_data=f"edit_{pid}"))
        kb.add(InlineKeyboardButton("🗑 O‘chirish", callback_data=f"delete_{pid}"))
        await bot.send_photo(message.chat.id, img_id, caption=cap, parse_mode="HTML", reply_markup=kb)
from aiogram.dispatcher.filters.state import State, StatesGroup

class EditProduct(StatesGroup):
    waiting_for_field = State()
    waiting_for_value = State()

@dp.callback_query_handler(lambda c: c.data.startswith("edit_"))
async def callback_edit(c: types.CallbackQuery, state: FSMContext):
    pid = int(c.data.split("_")[1])
    await state.update_data(product_id=pid)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Nomi", callback_data="field_name"))
    kb.add(InlineKeyboardButton("Modeli", callback_data="field_model"))
    kb.add(InlineKeyboardButton("Narxi", callback_data="field_price"))
    kb.add(InlineKeyboardButton("Razmer", callback_data="field_size"))
    kb.add(InlineKeyboardButton("Made In", callback_data="field_made"))
    await c.message.answer("Qaysi maydonni tahrirlaysiz?", reply_markup=kb)
    await EditProduct.waiting_for_field.set()
    await c.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("field_"), state=EditProduct.waiting_for_field)
async def choose_field(c: types.CallbackQuery, state: FSMContext):
    field = c.data.split("_")[1]
    await state.update_data(field=field)
    await bot.send_message(c.from_user.id, f"Iltimos, yangi {field} qiymatini kiriting:")
    await EditProduct.waiting_for_value.set()
    await c.answer()

@dp.message_handler(state=EditProduct.waiting_for_value)
async def process_field_update(message: types.Message, state: FSMContext):
    data = await state.get_data()
    pid = data['product_id']
    fld = data['field']
    val = message.text.strip()
    map_field = {
        "name": "name", "model": "model", "price": "price",
        "size": "size_value", "made": "made_in"
    }
    column = map_field.get(fld)
    if column:
        cur.execute(f"UPDATE products SET {column} = ? WHERE id = ?", (val, pid))
        conn.commit()
        await message.answer("✅ Yangilandi!")
    else:
        await message.answer("❗ Nomuvofiq maydon.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def callback_delete(c: types.CallbackQuery):
    pid = int(c.data.split("_")[1])
    cur.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    await c.message.edit_caption("🗑 Mahsulot o‘chirildi", parse_mode="HTML")
    await c.answer("O‘chirildi")
@dp.message_handler(commands=['search'])
async def cmd_search(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz")
    await message.answer("Qidiriladigan mahsulot nomi yoki modelini yozing:")

@dp.message_handler(lambda m: m.text and not m.text.startswith('/'))
async def search_handler(message: types.Message):
    term = message.text.lower()
    cur.execute("SELECT id, name, model, price, size_status, size_value, made_in, image_id FROM products")
    items = cur.fetchall()
    found = False
    for pid, name, model_, price_, sz_stat, sz_val, made_in_, img in items:
        if term in name.lower() or term in model_.lower():
            cap = f"<b>{name}</b>\n📦 Model: {model_}\n💰 Narx: {price_}\n📏 Razmer: {sz_stat} ({sz_val})\n🏷 {made_in_}"
            await bot.send_photo(message.chat.id, img, caption=cap, parse_mode="HTML")
            found = True
    if not found:
        await message.answer("❌ Mahsulot topilmadi.")

@dp.message_handler(commands=['admins'])
async def cmd_admins(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Faqat adminlar ko‘rishi mumkin")
    cur.execute("SELECT telegram_id, username FROM admins")
    rows = cur.fetchall()
    if not rows:
        return await message.answer("⚠️ Adminlar ro‘yxati bo‘sh.")
    text = "<b>Adminlar ro‘yxati:</b>\n"
    for tid, uname in rows:
        text += f"▫️ @{uname} — ID: <code>{tid}</code>\n"
    await message.answer(text, parse_mode="HTML")
    
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)





# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

