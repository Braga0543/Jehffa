import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # Telegram ID владельца (узнать у @userinfobot)
KASPI_PHONE = os.getenv("KASPI_PHONE", "+7 7XX XXX XX XX")  # номер для перевода на Kaspi
PRICE = 8000  # тенге за сутки
APARTMENTS = ["5", "7"]
PHOTOS = {  # фото, где лежит ключ (лежат рядом с bot.py)
    "5": Path("apt5.jpg"),
    "7": Path("apt7.jpg"),
}

# ---------- ТЕКСТЫ ----------
T = {
    "ru": {
        "greeting": "Здравствуйте! 👋 Это бот для аренды квартир.",
        "choose_apt": "Какую квартиру хотите арендовать?",
        "apt_btn": "🏠 Квартира №{n}",
        "ask_days": "Сколько суток хотите арендовать? Напишите число (например, 3).",
        "bad_days": "Введите число от 1 до 60.",
        "summary": (
            "Квартира №{apt}, суток: {days}.\n"
            "Итого: {total} ₸ ({price} ₸ за сутки).\n\n"
            "Переведите через Kaspi на номер: {phone}\n"
            "Затем отправьте сюда чек об оплате (скриншот или PDF)."
        ),
        "need_receipt": "Пожалуйста, отправьте чек как фото или файл.",
        "sent_wait": "Чек отправлен владельцу на проверку. Ожидайте подтверждения ⏳",
        "approved": "✅ Оплата подтверждена!",
        "key_info": "Ключ лежит в электрощитке у двери квартиры №{apt}.",
        "rejected": "❌ Оплата не подтверждена. Свяжитесь с владельцем или начните заново: /start",
    },
    "kk": {
        "greeting": "Сәлеметсіз бе! 👋 Бұл пәтерді жалға алуға арналған бот.",
        "choose_apt": "Қай пәтерді жалға алғыңыз келеді?",
        "apt_btn": "🏠 Пәтер №{n}",
        "ask_days": "Неше тәулікке жалға аласыз? Санын жазыңыз (мысалы, 3).",
        "bad_days": "1-ден 60-қа дейінгі санды енгізіңіз.",
        "summary": (
            "Пәтер №{apt}, тәулік саны: {days}.\n"
            "Барлығы: {total} ₸ (тәулігіне {price} ₸).\n\n"
            "Kaspi арқылы мына нөмірге аударыңыз: {phone}\n"
            "Содан кейін төлем чегін (скриншот немесе PDF) осында жіберіңіз."
        ),
        "need_receipt": "Чекті фото немесе файл ретінде жіберіңіз.",
        "sent_wait": "Чек иесіне тексеруге жіберілді. Растауды күтіңіз ⏳",
        "approved": "✅ Төлем расталды!",
        "key_info": "Кілт №{apt} пәтердің есігі жанындағы электр щитінде жатыр.",
        "rejected": "❌ Төлем расталмады. Иесімен байланысыңыз немесе қайта бастаңыз: /start",
    },
    "en": {
        "greeting": "Hello! 👋 This is an apartment rental bot.",
        "choose_apt": "Which apartment would you like to rent?",
        "apt_btn": "🏠 Apartment #{n}",
        "ask_days": "How many days do you want to rent? Send a number (e.g. 3).",
        "bad_days": "Please enter a number from 1 to 60.",
        "summary": (
            "Apartment #{apt}, days: {days}.\n"
            "Total: {total} ₸ ({price} ₸ per day).\n\n"
            "Please pay via Kaspi to: {phone}\n"
            "Then send the payment receipt here (screenshot or PDF)."
        ),
        "need_receipt": "Please send the receipt as a photo or a file.",
        "sent_wait": "Your receipt was sent to the owner for review. Please wait ⏳",
        "approved": "✅ Payment confirmed!",
        "key_info": "The key is in the electrical panel next to the door of apartment #{apt}.",
        "rejected": "❌ Payment was not confirmed. Contact the owner or start over: /start",
    },
}


class Form(StatesGroup):
    language = State()
    apartment = State()
    days = State()
    receipt = State()


dp = Dispatcher()


# ---------- ХЕНДЛЕРЫ ----------
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang:ru")
    kb.button(text="🇰🇿 Қазақша", callback_data="lang:kk")
    kb.button(text="🇬🇧 English", callback_data="lang:en")
    kb.adjust(1)
    await message.answer("Выберите язык / Тілді таңдаңыз / Choose language:", reply_markup=kb.as_markup())
    await state.set_state(Form.language)


@dp.callback_query(F.data.startswith("lang:"))
async def choose_language(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    await state.update_data(lang=lang)
    t = T[lang]
    kb = InlineKeyboardBuilder()
    for n in APARTMENTS:
        kb.button(text=t["apt_btn"].format(n=n), callback_data=f"apt:{n}")
    kb.adjust(1)
    await call.message.edit_text(f"{t['greeting']}\n\n{t['choose_apt']}", reply_markup=kb.as_markup())
    await state.set_state(Form.apartment)
    await call.answer()


@dp.callback_query(F.data.startswith("apt:"))
async def choose_apartment(call: CallbackQuery, state: FSMContext):
    apt = call.data.split(":")[1]
    data = await state.get_data()
    t = T[data["lang"]]
    await state.update_data(apt=apt)
    await call.message.edit_text(t["ask_days"])
    await state.set_state(Form.days)
    await call.answer()


@dp.message(Form.days)
async def enter_days(message: Message, state: FSMContext):
    data = await state.get_data()
    t = T[data["lang"]]
    text = (message.text or "").strip()
    if not text.isdigit() or not 1 <= int(text) <= 60:
        await message.answer(t["bad_days"])
        return
    days = int(text)
    await state.update_data(days=days, total=days * PRICE)
    await message.answer(
        t["summary"].format(apt=data["apt"], days=days, total=days * PRICE, price=PRICE, phone=KASPI_PHONE)
    )
    await state.set_state(Form.receipt)


@dp.message(Form.receipt, F.photo | F.document)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang, apt = data["lang"], data["apt"]
    user = message.from_user

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"ok:{user.id}:{apt}:{lang}")
    kb.button(text="❌ Отклонить", callback_data=f"no:{user.id}:{lang}")
    kb.adjust(2)

    caption = (
        f"Новая оплата\n"
        f"Квартира №{apt}, суток: {data['days']}, сумма: {data['total']} ₸\n"
        f"Клиент: {user.full_name}"
        + (f" (@{user.username})" if user.username else "")
    )
    await message.copy_to(OWNER_ID, caption=caption, reply_markup=kb.as_markup())
    await message.answer(T[lang]["sent_wait"])
    await state.clear()


@dp.message(Form.receipt)
async def receipt_wrong_type(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(T[data["lang"]]["need_receipt"])


@dp.callback_query(F.data.startswith(("ok:", "no:")))
async def owner_decision(call: CallbackQuery, bot: Bot):
    if call.from_user.id != OWNER_ID:
        await call.answer("Нет доступа", show_alert=True)
        return

    parts = call.data.split(":")
    if parts[0] == "ok":
        _, uid, apt, lang = parts
        uid = int(uid)
        t = T[lang]
        await bot.send_message(uid, f"{t['approved']}\n\n{t['key_info'].format(apt=apt)}")
        photo = PHOTOS.get(apt)
        if photo and photo.exists():
            await bot.send_photo(uid, FSInputFile(photo))
        status = "✅ Подтверждено"
    else:
        _, uid, lang = parts
        await bot.send_message(int(uid), T[lang]["rejected"])
        status = "❌ Отклонено"

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.reply(status)
    await call.answer()


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
