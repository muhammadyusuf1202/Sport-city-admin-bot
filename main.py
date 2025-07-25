import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Database
conn = sqlite3.connect("store.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    model TEXT,
    price TEXT,
    image TEXT,
    size TEXT,
    made_in TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)""")
conn.commit()

class AddProduct(StatesGroup):
    name = State()
    model = State()
    price = State()
    image = State()
    size = State()
    madein = State()

class EditProduct(StatesGroup):
    model = State()
    field = State()
    new_value = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    cursor.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    if user_id in ADMIN_IDS:
        cursor.execute("INSERT OR IGNORE INTO admins(user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        await message.answer("👋 Salom, Admin!\nQuyidagilarni ishlatishingiz mumkin:\n"
                             "/add\n/products\n/edit\n/delete\n/search\n/admins")
    else:
        await message.answer("👋 Salom! Botga xush kelibsiz!")

@dp.message_handler(commands='add')
async def add_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz.")
    await message.answer("📝 Mahsulot nomi:")
    await AddProduct.name.set()

@dp.message_handler(state=AddProduct.name)
async def product_model(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📦 Model:")
    await AddProduct.model.set()

@dp.message_handler(state=AddProduct.model)
async def product_price(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("💰 Narx:")
    await AddProduct.price.set()

@dp.message_handler(state=AddProduct.price)
async def product_image(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("🖼 Rasm yuboring:")
    await AddProduct.image.set()

@dp.message_handler(content_types=['photo'], state=AddProduct.image)
async def product_size(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(image=photo_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Bor", "Yo'q")
    await message.answer("📏 Razmer mavjudmi?", reply_markup=markup)
    await AddProduct.size.set()

@dp.message_handler(state=AddProduct.size)
async def product_madein(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("🏷 Qayerda ishlab chiqarilgan?", reply_markup=types.ReplyKeyboardRemove())
    await AddProduct.madein.set()

@dp.message_handler(state=AddProduct.madein)
async def save_product(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO products (name, model, price, image, size, made_in) VALUES (?, ?, ?, ?, ?, ?)",
                   (data['name'], data['model'], data['price'], data['image'], data['size'], message.text))
    conn.commit()
    await message.answer("✅ Mahsulot qo‘shildi.")
    await state.finish()

@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz.")
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    if not products:
        return await message.answer("❌ Mahsulotlar mavjud emas.")
    for p in products:
        await bot.send_photo(message.chat.id, p[4], caption=f"🛍 {p[1]}\n📦 {p[2]}\n💰 {p[3]}\n📏 {p[5]}\n🏷 {p[6]}")

@dp.message_handler(commands=['search'])
async def search(message: types.Message):
    await message.answer("🔍 Qidirilayotgan model yoki nomni yuboring:")

@dp.message_handler(lambda msg: not msg.text.startswith('/'))
async def search_result(message: types.Message):
    text = message.text.lower()
    cursor.execute("SELECT * FROM products WHERE LOWER(name) LIKE ? OR LOWER(model) LIKE ?", (f"%{text}%", f"%{text}%"))
    results = cursor.fetchall()
    if not results:
        return await message.answer("❌ Mos mahsulot topilmadi.")
    for p in results:
        await bot.send_photo(message.chat.id, p[4], caption=f"🛍 {p[1]}\n📦 {p[2]}\n💰 {p[3]}\n📏 {p[5]}\n🏷 {p[6]}")

@dp.message_handler(commands=['admins'])
async def show_admins(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz.")
    cursor.execute("SELECT * FROM admins")
    admins = cursor.fetchall()
    text = "👮 Adminlar:\n\n" + "\n".join([f"{a[1]} ({a[0]})" for a in admins])
    await message.answer(text)

@dp.message_handler(commands=['delete'])
async def delete_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz.")
    await message.answer("🗑 O‘chirmoqchi bo‘lgan model nomini yuboring:")

@dp.message_handler(commands=['edit'])
async def edit_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Siz admin emassiz.")
    await message.answer("✏️ Tahrirlamoqchi bo‘lgan model nomini yuboring:")
    await EditProduct.model.set()

@dp.message_handler(state=EditProduct.model)
async def choose_field(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("name", "model", "price", "size", "made_in")
    await message.answer("🔧 Qaysi maydonni o‘zgartirmoqchisiz?", reply_markup=markup)
    await EditProduct.field.set()

@dp.message_handler(state=EditProduct.field)
async def new_value(message: types.Message, state: FSMContext):
    await state.update_data(field=message.text)
    await message.answer("🆕 Yangi qiymat:", reply_markup=types.ReplyKeyboardRemove())
    await EditProduct.new_value.set()

@dp.message_handler(state=EditProduct.new_value)
async def apply_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute(f"UPDATE products SET {data['field']} = ? WHERE model = ?", (message.text, data['model']))
    conn.commit()
    await message.answer("✅ Tahrirlandi.")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)




# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMIN_IDS = [807995985, 5751536492, 7435391786, 266461241]

