import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command

API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
ADMINS = [807995985, 5751536492, 266461241, 7310580762]  # Adminlar ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

conn = sqlite3.connect('sportcity.db')
cursor = conn.cursor()

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
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    name TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    location TEXT,
    payment TEXT
)
''')
conn.commit()

class OrderState(StatesGroup):
    waiting_location = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)",
                   (message.from_user.id, message.from_user.full_name))
    conn.commit()
    await message.answer("Xush kelibsiz!\n/products orqali mahsulotlarni ko'rishingiz mumkin.")

@dp.message_handler(commands=['products'])
async def list_products(message: types.Message):
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    if not products:
        return await message.answer("Hozircha mahsulotlar mavjud emas.")
    for prod in products:
        btn = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Zakaz berish", callback_data=f"order_{prod[0]}")
        )
        await message.answer(
            f"🛍 Mahsulot: {prod[1]}\n🔢 Model: {prod[2]}\n💰 Narx: {prod[3]} so'm\n🏭 Ishlab chiqarilgan: {prod[4]}",
            reply_markup=btn
        )

@dp.callback_query_handler(lambda c: c.data.startswith('order_'))
async def order_product(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split('_')[1])
    await state.update_data(product_id=product_id)
    await bot.send_message(callback_query.from_user.id, "📍 Iltimos, manzilingizni kiriting:")
    await OrderState.waiting_location.set()

@dp.message_handler(state=OrderState.waiting_location)
async def get_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    product_id = data['product_id']
    cursor.execute("INSERT INTO orders (user_id, product_id, location, payment) VALUES (?, ?, ?, ?)",
                   (message.from_user.id, product_id, message.text, "Naqd"))
    conn.commit()

    cursor.execute("SELECT name FROM products WHERE id=?", (product_id,))
    product_name = cursor.fetchone()[0]

    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id,
            f"🛒 Yangi zakaz:\n👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"📦 Mahsulot: {product_name}\n📍 Manzil: {message.text}\n💵 To‘lov: Naqd")
    await message.answer("✅ Buyurtma qabul qilindi. Tez orada siz bilan bog'lanamiz!")
    await state.finish()

@dp.message_handler(lambda m: m.from_user.id in ADMIN_IDS and m.text.startswith("/add"))
async def add_product(message: types.Message):
    try:
        _, name, model, price, made_in = message.text.split(",")
        cursor.execute("INSERT INTO products (name, model, price, made_in) VALUES (?, ?, ?, ?)",
                       (name.strip(), model.strip(), int(price), made_in.strip()))
        conn.commit()
        await message.answer("✅ Mahsulot qo'shildi!")
    except:
        await message.answer("❗ Format: /add nom,model,narx,made_in")

@dp.message_handler(lambda m: m.from_user.id in ADMIN_IDS and m.text.startswith("/edit"))
async def edit_product(message: types.Message):
    try:
        _, prod_id, name, model, price, made_in = message.text.split(",")
        cursor.execute("UPDATE products SET name=?, model=?, price=?, made_in=? WHERE id=?",
                       (name.strip(), model.strip(), int(price), made_in.strip(), int(prod_id)))
        conn.commit()
        await message.answer("✅ Mahsulot tahrirlandi!")
    except:
        await message.answer("❗ Format: /edit id,nom,model,narx,made_in")

@dp.message_handler(lambda m: m.from_user.id in ADMIN_IDS and m.text.startswith("/delete"))
async def delete_product(message: types.Message):
    try:
        _, prod_id = message.text.split()
        cursor.execute("DELETE FROM products WHERE id=?", (int(prod_id),))
        conn.commit()
        await message.answer("🗑 Mahsulot o'chirildi.")
    except:
        await message.answer("❗ Format: /delete id")

@dp.message_handler(commands=['search_model'])
async def search_by_model(message: types.Message):
    model = message.get_args()
    cursor.execute("SELECT * FROM products WHERE model LIKE ?", ('%' + model + '%',))
    results = cursor.fetchall()
    if not results:
        return await message.answer("Model bo‘yicha mahsulot topilmadi.")
    for prod in results:
        await message.answer(f"🔍 {prod[1]} - {prod[2]} - {prod[3]} so'm")

@dp.message_handler(commands=['search_nomi'])
async def search_by_name(message: types.Message):
    name = message.get_args()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ('%' + name + '%',))
    results = cursor.fetchall()
    if not results:
        return await message.answer("Nomi bo‘yicha mahsulot topilmadi.")
    for prod in results:
        await message.answer(f"🔍 {prod[1]} - {prod[2]} - {prod[3]} so'm")

@dp.message_handler(commands=['savat'])
async def savat(message: types.Message):
    cursor.execute("SELECT * FROM orders WHERE user_id=?", (message.from_user.id,))
    orders = cursor.fetchall()
    if not orders:
        return await message.answer("🛒 Savatingiz bo‘sh.")
    for order in orders:
        cursor.execute("SELECT name FROM products WHERE id=?", (order[2],))
        name = cursor.fetchone()[0]
        await message.answer(f"📦 {name}\n📍 {order[3]}\n💵 {order[4]}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)



# API_TOKEN = '7310580762:AAGaxIWXKFUjUU4qoVARdWkHMRR0c9QSKLU'
# ADMINS = [807995985, 5751536492, 266461241]  # Admin Telegram IDs
# SELLER_CARD = "5614 8600 0311 6783"

# bot = Bot(API_TOKEN)
# dp = Dispatcher(bot, storage=MemoryStorage())

# # --- DB initialization ---
# def init_db():
#     conn = sqlite3.connect('sport_city.db')
#     c = conn.cursor()
#     c.execute("""CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE, full_name TEXT, username TEXT, first_join TEXT)""")
#     c.execute("""CREATE TABLE IF NOT EXISTS products (
#         id INTEGER PRIMARY KEY, name TEXT, price INTEGER, model TEXT UNIQUE, made_in TEXT, image TEXT)""")
#     c.execute("""CREATE TABLE IF NOT EXISTS orders (
#         id INTEGER PRIMARY KEY, telegram_id INTEGER, product_id INTEGER,
#         name TEXT, surname TEXT, age INTEGER, phone TEXT, username TEXT,
#         created TEXT)""")
#     conn.commit(); conn.close()
# init_db()

# def is_admin(uid): return uid in ADMINS

# # --- LOCALIZATION ---
# LANG = {}  # {user_id: lang_code}

# @dp.message_handler(commands=['languages'])
# async def cmd_lang(message: types.Message):
#     if not is_admin(message.from_user.id): return await message.reply("🚫 Faqat admin!")
#     kb = InlineKeyboardMarkup(row_width=3)
#     for code,name in (('uz','🇺🇿 O‘zbek'),('ru','🇷🇺 Русча'),('en','🇬🇧 English')):
#         kb.insert(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
#     await message.reply("Tilni tanlang:", reply_markup=kb)

# @dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
# async def lang_select(c: types.CallbackQuery):
#     code = c.data.split('_')[1]
#     LANG[c.from_user.id] = code
#     await c.answer(f"Til {code} tanlandi")

# # --- ADMIN: USERS LIST ---
# @dp.message_handler(commands=['users'])
# async def cmd_users(message: types.Message):
#     if not is_admin(message.from_user.id): return await message.reply("🚫 Faqat admin!")
#     rows = sqlite3.connect('sport_city.db').cursor().execute(
#         "SELECT telegram_id, full_name, username FROM users").fetchall()
#     lines = [f"{fn} (@{un}) — {tid}" for tid,fn,un in rows]
#     await message.reply("👥 Foydalanuvchilar:\n" + "\n".join(lines))

# # --- ADMIN: BUYERTMA FORM ---
# class OrderFilling(StatesGroup):
#     product_id = State()
#     name = State()
#     surname = State()
#     age = State()
#     phone = State()
#     username = State()

# # --- ADMIN commands for products omitted for brevity (use earlier code) ---

# # --- USER: /products & view ---
# @dp.message_handler(commands=['products'])
# async def cmd_products(m):
#     rows = sqlite3.connect('sport_city.db').cursor().execute(
#         "SELECT id,name FROM products").fetchall()
#     kb = InlineKeyboardMarkup()
#     for pid,name in rows:
#         kb.insert(InlineKeyboardButton(name, callback_data=f"view_{pid}"))
#     await m.reply("Mahsulotlar:", reply_markup=kb)

# @dp.callback_query_handler(lambda c: c.data.startswith("view_"))
# async def view_prod(c):
#     pid = int(c.data.split('_')[1])
#     row = sqlite3.connect('sport_city.db').cursor().execute(
#         "SELECT name,price,image FROM products WHERE id=?", (pid,)
#     ).fetchone()
#     if not row: return await c.answer("Topilmadi")
#     name,price,img = row
#     kb = InlineKeyboardMarkup().insert(InlineKeyboardButton("📋 Buyurtma berish", callback_data=f"order_{pid}"))
#     await bot.send_photo(c.from_user.id, img,
#                          caption=f"{name} — {price} so‘m", reply_markup=kb)

# # --- ORDER PROCESS ---
# @dp.callback_query_handler(lambda c: c.data.startswith("order_"))
# async def start_order(c, state: FSMContext):
#     pid = int(c.data.split('_')[1])
#     await state.update_data(product_id=pid)
#     await c.message.reply("Ismingizni yozing:"); await OrderFilling.name.set()

# @dp.message_handler(state=OrderFilling.name)
# async def st_name(m, state):
#     await state.update_data(name=m.text); await m.reply("Familiyangiz?"); await OrderFilling.surname.set()

# @dp.message_handler(state=OrderFilling.surname)
# async def st_surname(m, state):
#     await state.update_data(surname=m.text); await m.reply("Yoshingiz?"); await OrderFilling.age.set()

# @dp.message_handler(state=OrderFilling.age)
# async def st_age(m, state):
#     await state.update_data(age=m.text); await m.reply("Raqamingiz?"); await OrderFilling.phone.set()

# @dp.message_handler(state=OrderFilling.phone)
# async def st_phone(m, state):
#     await state.update_data(phone=m.text); await m.reply("Telegram username (@...)").; await OrderFilling.username.set()

# @dp.message_handler(state=OrderFilling.username)
# async def st_username(m, state):
#     await state.update_data(username=m.text)
#     data=await state.get_data(); row=sqlite3.connect('sport_city.db').cursor().execute(
#         "SELECT name,price FROM products WHERE id=?", (data['product_id'],)
#     ).fetchone()
#     text=(f"📌 Ariza:\n👤 {data['name']} {data['surname']}, {data['age']} yosh\n"
#           f"📞 {data['phone']}\n🆔 {data['username']}\n"
#           f"🛒 {row[0]} — {row[1]} so‘m")
#     for ad in ADMINS: await bot.send_message(ad, text)
#     sqlite3.connect('sport_city.db').cursor().execute(
#         "INSERT INTO orders VALUES (NULL,?,?,?,?,?,?,?,?)",
#         (m.from_user.id,data['product_id'],data['name'],data['surname'],
#          data['age'], data['phone'], data['username'], datetime.now().isoformat()))
#     await m.reply("✅ Arizangiz yuborildi!"); await state.finish()

# # --- SAVAT ---
# @dp.message_handler(commands=['savat'])
# async def cmd_savat(m):
#     rows = sqlite3.connect('sport_city.db').cursor().execute(
#         "SELECT id,product_id FROM orders WHERE telegram_id=?", (m.from_user.id,)
#     ).fetchall()
#     if not rows: return await m.reply("🛒 Savat bo‘sh")
#     kb=InlineKeyboardMarkup()
#     for oid,pid in rows:
#         name=sqlite3.connect('sport_city.db').cursor().execute(
#             "SELECT name FROM products WHERE id=?", (pid,)).fetchone()[0]
#         kb.insert(InlineKeyboardButton(name, callback_data=f"sav_{oid}"))
#     await m.reply("📦 Savatdagi buyurtmalar:", reply_markup=kb)

# @dp.callback_query_handler(lambda c: c.data.startswith("sav_"))
# async def show_sav(c):
#     oid=int(c.data.split('_')[1])
#     row=sqlite3.connect('sport_city.db').cursor().execute(
#         "SELECT name,surname,age,phone,username,created FROM orders WHERE id=?", (oid,)
#     ).fetchone()
#     await c.message.reply(f"📋 Buyurtma:\nIsm: {row[0]} {row[1]}, {row[2]} yosh\n📞 {row[3]}\n🆔 {row[4]}\n⏰ {row[5]}")

# # --- RUN ---
# if __name__ == "__main__":
#     executor.start_polling(dp, skip_updates=True)

