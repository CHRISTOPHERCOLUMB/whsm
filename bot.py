import asyncio
import json
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ========== КОНФИГ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан!")

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip().isdigit()]
if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS не заданы!")

SUPPORT = os.getenv("SUPPORT", "@whitesmoke_support")
STORE_NAME = os.getenv("STORE_NAME", "WHITE SMOKE")
DATA_FILE = os.getenv("DATA_FILE", "white_smoke_data.json")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== ЗАГРУЗКА / СОХРАНЕНИЕ ==========
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "products": [],
            "cities": [],
            "orders": [],
            "next_product_id": 1,
            "next_order_id": 1
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load_data()

# ========== ПОЛЬЗОВАТЕЛИ ==========
def get_user(user_id):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "balance": 0,
            "orders": [],
            "joined": datetime.now().isoformat()
        }
        save_data(data)
    return data["users"][uid]

def save_user(user_id, user_data):
    data["users"][str(user_id)] = user_data
    save_data(data)

# ========== FSM ==========
class PaymentState(StatesGroup):
    waiting = State()

class AdminStates(StatesGroup):
    add_name = State()
    add_price = State()
    add_weight = State()
    add_city = State()
    edit_select = State()
    edit_field = State()
    edit_value = State()
    delete_select = State()
    add_city_name = State()
    del_city_select = State()
    bal_user = State()
    bal_amount = State()
    broadcast_text = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = [
        [KeyboardButton(text="📦 Прайс")],
        [KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="💼 Работа")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    kb = [
        [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="✏️ Редактировать товар")],
        [KeyboardButton(text="🗑 Удалить товар"), KeyboardButton(text="🏙 Добавить город")],
        [KeyboardButton(text="🗑 Удалить город"), KeyboardButton(text="💰 Выдать баланс")],
        [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🔙 Выйти из админки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def back_to_admin_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад в админку")]], resize_keyboard=True)

def cities_keyboard():
    kb = []
    for city in data["cities"]:
        if any(p["city"] == city for p in data["products"]):
            kb.append([KeyboardButton(text=city)])
    kb.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def products_keyboard(city):
    kb = []
    for p in data["products"]:
        if p["city"] == city:
            kb.append([KeyboardButton(text=f"{p['name']} ({p['weight']}) - {p['price']} KZT")])
    kb.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def payment_keyboard():
    kb = [
        [KeyboardButton(text="USDT")],
        [KeyboardButton(text="LITECOIN")],
        [KeyboardButton(text="Перевод на карту РК")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    get_user(message.from_user.id)
    await message.answer(
        f"✨ Добро пожаловать в <b>{STORE_NAME}</b>!\n\n"
        "Доступные товары можно посмотреть в разделе 📦 Прайс.\n"
        "По всем вопросам обращайтесь в поддержку.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.message(F.text == "📦 Прайс")
async def price_handler(message: types.Message):
    cities_with_products = list(set(p["city"] for p in data["products"]))
    if not cities_with_products:
        await message.answer("📦 В данный момент товаров нет.", reply_markup=main_menu())
        return
    await message.answer(
        "🏙 <b>Выберите город для просмотра товаров:</b>",
        parse_mode="HTML",
        reply_markup=cities_keyboard()
    )

@dp.message(F.text == "❓ Помощь")
async def help_handler(message: types.Message):
    await message.answer(
        f"❓ <b>Помощь</b>\n\nВозникли вопросы? Обращайтесь к {SUPPORT}",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.message(F.text == "💼 Работа")
async def work_handler(message: types.Message):
    await message.answer(
        f"💼 <b>Работа</b>\n\nКостанай, Рудный, Лисаковск, Федоровка\nЗа работой в ЛС {SUPPORT}",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.message(F.text == "🔙 Назад")
async def back_to_main(message: types.Message):
    await message.answer("🔙 Возврат в главное меню.", reply_markup=main_menu())

@dp.message(lambda msg: msg.text in [city for city in data["cities"] if any(p["city"] == city for p in data["products"])])
async def city_selected(message: types.Message):
    city = message.text
    await message.answer(
        f"📦 <b>Товары в городе {city}:</b>",
        parse_mode="HTML",
        reply_markup=products_keyboard(city)
    )

@dp.message(lambda msg: msg.text and " - " in msg.text and any(p["name"] in msg.text for p in data["products"]))
async def product_selected(message: types.Message, state: FSMContext):
    product_text = message.text.split(" - ")[0].strip()
    product_name = re.sub(r'\s*\([^)]*\)', '', product_text).strip()
    product = next((p for p in data["products"] if p["name"] == product_name), None)
    if not product:
        await message.answer("❌ Товар не найден.")
        return
    await state.update_data(product=product)
    await message.answer(
        f"✅ <b>Вы выбрали:</b>\n"
        f"📦 {product['name']}\n"
        f"⚖️ Вес: {product['weight']}\n"
        f"💰 Цена: {product['price']} KZT\n\n"
        f"Выберите способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_keyboard()
    )
    await state.set_state(PaymentState.waiting)

@dp.message(StateFilter(PaymentState.waiting), F.text == "🔙 Назад")
async def back_from_payment(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔙 Возврат к выбору города.", reply_markup=cities_keyboard())

@dp.message(StateFilter(PaymentState.waiting), F.text.in_(["USDT", "LITECOIN", "Перевод на карту РК"]))
async def payment_chosen(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"⚠️ <b>Внимание!</b>\n\n"
        f"На данный момент автоматическая оплата отключена.\n"
        f"Обратитесь в поддержку: {SUPPORT}",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# ========== АДМИН-ПАНЕЛЬ ==========
def is_admin(user_id):
    return user_id in ADMIN_IDS

@dp.message(Command("admin"))
async def admin_entry(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

@dp.message(F.text == "🔙 Выйти из админки")
async def exit_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔙 Вы вышли из админки.", reply_markup=main_menu())

@dp.message(F.text == "🔙 Назад в админку")
async def back_to_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("⚙️ Панель администратора", reply_markup=admin_menu())

# ---------- Добавление товара ----------
@dp.message(F.text == "➕ Добавить товар")
async def add_product_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите <b>название</b> товара:", parse_mode="HTML", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.add_name)

@dp.message(AdminStates.add_name)
async def add_product_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    await state.update_data(name=message.text)
    await message.answer("Введите <b>цену</b> (в KZT):", parse_mode="HTML")
    await state.set_state(AdminStates.add_price)

@dp.message(AdminStates.add_price)
async def add_product_price(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        await state.update_data(price=int(price))
        await message.answer("Введите <b>вес</b> (например: 1 г):", parse_mode="HTML")
        await state.set_state(AdminStates.add_weight)
    except:
        await message.answer("❌ Введите число больше 0.")

@dp.message(AdminStates.add_weight)
async def add_product_weight(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    await state.update_data(weight=message.text)
    if not data["cities"]:
        await message.answer("❌ Сначала добавьте хотя бы один город через '🏙 Добавить город'.")
        await state.clear()
        return
    cities_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(data["cities"])])
    await message.answer(f"Выберите <b>город</b> (введите номер):\n{cities_list}", parse_mode="HTML")
    await state.set_state(AdminStates.add_city)

@dp.message(AdminStates.add_city)
async def add_product_city(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    try:
        idx = int(message.text) - 1
        if idx < 0 or idx >= len(data["cities"]):
            raise ValueError
        city = data["cities"][idx]
        data_state = await state.get_data()
        product = {
            "id": data["next_product_id"],
            "name": data_state["name"],
            "price": data_state["price"],
            "weight": data_state["weight"],
            "city": city
        }
        data["products"].append(product)
        data["next_product_id"] += 1
        save_data(data)
        await state.clear()
        await message.answer(f"✅ Товар <b>{product['name']}</b> добавлен в {city}!", parse_mode="HTML", reply_markup=admin_menu())
    except:
        await message.answer(f"❌ Введите число от 1 до {len(data['cities'])}")

# ---------- Редактирование товара ----------
@dp.message(F.text == "✏️ Редактировать товар")
async def edit_product_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not data["products"]:
        await message.answer("Нет товаров для редактирования.", reply_markup=admin_menu())
        return
    text = "📝 <b>Список товаров:</b>\n\n"
    for p in data["products"]:
        text += f"ID: {p['id']} | {p['name']} | {p['price']} KZT | {p['city']}\n"
    text += "\nВведите ID товара для редактирования:"
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.edit_select)

@dp.message(AdminStates.edit_select)
async def edit_product_select(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    if not message.text.isdigit():
        await message.answer("❌ Введите ID.")
        return
    pid = int(message.text)
    product = next((p for p in data["products"] if p["id"] == pid), None)
    if not product:
        await message.answer("❌ Товар не найден.")
        await state.clear()
        return
    await state.update_data(pid=pid)
    await message.answer(
        "Что изменить?\n"
        "Доступно: <code>name</code>, <code>price</code>, <code>weight</code>, <code>city</code>\n"
        "Введите поле:",
        parse_mode="HTML",
        reply_markup=back_to_admin_kb()
    )
    await state.set_state(AdminStates.edit_field)

@dp.message(AdminStates.edit_field)
async def edit_product_field(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    field = message.text.lower()
    if field not in ["name", "price", "weight", "city"]:
        await message.answer("❌ Доступно: name, price, weight, city")
        return
    await state.update_data(field=field)
    await message.answer(f"Введите новое значение для <code>{field}</code>:", parse_mode="HTML")
    await state.set_state(AdminStates.edit_value)

@dp.message(AdminStates.edit_value)
async def edit_product_value(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    data_state = await state.get_data()
    pid = data_state["pid"]
    field = data_state["field"]
    value = message.text
    product = next((p for p in data["products"] if p["id"] == pid), None)
    if not product:
        await message.answer("❌ Товар не найден.")
        await state.clear()
        return
    if field == "price":
        try:
            value = int(float(value.replace(",", ".")))
        except:
            await message.answer("❌ Введите число.")
            return
    elif field == "city":
        if value not in data["cities"]:
            await message.answer(f"❌ Город должен быть из списка: {', '.join(data['cities'])}")
            return
    product[field] = value
    save_data(data)
    await state.clear()
    await message.answer(f"✅ Товар обновлён: {field} → {value}", reply_markup=admin_menu())

# ---------- Удаление товара ----------
@dp.message(F.text == "🗑 Удалить товар")
async def delete_product_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not data["products"]:
        await message.answer("Нет товаров для удаления.", reply_markup=admin_menu())
        return
    text = "🗑 <b>Список товаров:</b>\n\n"
    for p in data["products"]:
        text += f"ID: {p['id']} | {p['name']}\n"
    text += "\nВведите ID товара для удаления:"
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.delete_select)

@dp.message(AdminStates.delete_select)
async def delete_product_confirm(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    if not message.text.isdigit():
        await message.answer("❌ Введите ID.")
        return
    pid = int(message.text)
    product = next((p for p in data["products"] if p["id"] == pid), None)
    if not product:
        await message.answer("❌ Товар не найден.")
        await state.clear()
        return
    data["products"].remove(product)
    save_data(data)
    await state.clear()
    await message.answer(f"✅ Товар <b>{product['name']}</b> удалён.", parse_mode="HTML", reply_markup=admin_menu())

# ---------- Добавление города ----------
@dp.message(F.text == "🏙 Добавить город")
async def add_city_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите название нового города:", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.add_city_name)

@dp.message(AdminStates.add_city_name)
async def add_city_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    city = message.text.strip()
    if not city:
        await message.answer("❌ Введите название города.")
        return
    if city in data["cities"]:
        await message.answer("❌ Такой город уже есть.")
        return
    data["cities"].append(city)
    save_data(data)
    await state.clear()
    await message.answer(f"✅ Город <b>{city}</b> добавлен.", parse_mode="HTML", reply_markup=admin_menu())

# ---------- Удаление города ----------
@dp.message(F.text == "🗑 Удалить город")
async def remove_city_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not data["cities"]:
        await message.answer("Нет городов для удаления.", reply_markup=admin_menu())
        return
    text = "🗑 <b>Список городов:</b>\n\n"
    for i, city in enumerate(data["cities"], 1):
        text += f"{i}. {city}\n"
    text += "\nВведите номер города для удаления:"
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.del_city_select)

@dp.message(AdminStates.del_city_select)
async def remove_city_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    try:
        idx = int(message.text) - 1
        if idx < 0 or idx >= len(data["cities"]):
            raise ValueError
        city = data["cities"][idx]
        data["cities"].remove(city)
        data["products"] = [p for p in data["products"] if p["city"] != city]
        save_data(data)
        await state.clear()
        await message.answer(f"✅ Город <b>{city}</b> и все его товары удалены.", parse_mode="HTML", reply_markup=admin_menu())
    except:
        await message.answer(f"❌ Введите число от 1 до {len(data['cities'])}")

# -# ---------- Выдача баланса ----------
@dp.message(F.text == "💰 Выдать баланс")
async def add_balance_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите ID пользователя и сумму через пробел:\nПример: <code>613790427 5000</code>", parse_mode="HTML", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.bal_user)

@dp.message(AdminStates.bal_user)
async def add_balance_user(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("❌ Формат: <code>ID СУММА</code>", parse_mode="HTML")
        return
    user_id = parts[0]
    amount = int(parts[1])
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "balance": 0,
            "orders": [],
            "joined": datetime.now().isoformat()
        }
    data["users"][user_id]["balance"] += amount
    save_data(data)
    await state.clear()
    await message.answer(f"✅ Пользователю <code>{user_id}</code> начислено {amount} KZT.", parse_mode="HTML", reply_markup=admin_menu())
    try:
        await bot.send_message(int(user_id), f"💰 Ваш баланс пополнен на <b>{amount} KZT</b>!", parse_mode="HTML")
    except:
        pass

# ---------- Рассылка ----------
@dp.message(F.text == "📢 Рассылка")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите текст рассылки:", reply_markup=back_to_admin_kb())
    await state.set_state(AdminStates.broadcast_text)

@dp.message(AdminStates.broadcast_text)
async def broadcast_send(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в админку":
        await state.clear()
        await back_to_admin(message, state)
        return
    text = message.text
    count = 0
    for user_id in data["users"].keys():
        try:
            await bot.send_message(int(user_id), text, parse_mode="HTML")
            count += 1
        except:
            pass
    await state.clear()
    await message.answer(f"✅ Рассылка отправлена {count} пользователям.", reply_markup=admin_menu())

# ---------- Статистика ----------
@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    total_users = len(data["users"])
    total_orders = len(data["orders"])
    total_revenue = sum(o.get("price", 0) for o in data["orders"])
    total_balance = sum(u["balance"] for u in data["users"].values())
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🛍️ Заказов: {total_orders}\n"
        f"💰 Выручка: {total_revenue} KZT\n"
        f"💎 Общий баланс: {total_balance} KZT\n"
        f"📦 Товаров: {len(data['products'])}\n"
        f"🏙 Городов: {len(data['cities'])}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Бот WHITE SMOKE запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
