from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .texts import REG, t


def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=REG["share_phone_btn"], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def menu_kb(lang, can_restart=True):
    """Natija / qayta boshlash / yordam — doimiy pastki menyu.

    can_restart=False bo'lsa (ALLOW_RETAKE=False va foydalanuvchi testni
    allaqachon tugatgan), "Qayta boshlash" tugmasi ko'rsatilmaydi — chunki
    bosilganda baribir "allaqachon topshirgansiz" degan tupikka olib keladi.
    """
    row1 = [KeyboardButton(text=t(lang, "menu_result"))]
    if can_restart:
        row1.append(KeyboardButton(text=t(lang, "menu_restart")))
    return ReplyKeyboardMarkup(
        keyboard=[row1, [KeyboardButton(text=t(lang, "menu_help"))]],
        resize_keyboard=True,
    )


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    ]])


def answers_kb(session_id, question_id, options):
    """options: [(option_id, letter, text)] — tugmalarda faqat harflar."""
    buttons = [
        InlineKeyboardButton(text=letter, callback_data=f"a:{session_id}:{question_id}:{oid}")
        for oid, letter, _ in options
    ]
    per_row = 5 if len(buttons) in (5, 10) else 4
    rows = [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]
    return InlineKeyboardMarkup(inline_keyboard=rows)
