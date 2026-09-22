import html
import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message, ReplyKeyboardRemove
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections

from quiz import services
from quiz.services import SubmitResult

from .keyboards import answers_kb, lang_kb, menu_kb, phone_kb
from .texts import REG, t

log = logging.getLogger(__name__)
router = Router()

NAME_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ '’‘`ʻʼ\-])*[^\W\d_]$")
PHONE_RE = re.compile(r"^\+?\d{9,15}$")
CAPTION_LIMIT = 1024

# Rasm + uzun matn alohida yuborilganda qo'shimcha xabarlarni o'chirish uchun
_extra_messages: dict[int, list[int]] = {}


def db(fn):
    """Sinxron ORM funksiyasini async qilib o'raydi va eskirgan ulanishlarni yopadi."""
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()
    return sync_to_async(wrapper, thread_sensitive=True)


class Reg(StatesGroup):
    first_name = State()
    last_name = State()
    phone = State()
    language = State()


def valid_name(value: str) -> bool:
    value = value.strip()
    return 2 <= len(value) <= 50 and bool(NAME_RE.match(value))


def nice_name(value: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in value.strip().split())


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[\s\-\(\)]", "", raw or "")
    if not PHONE_RE.match(digits):
        return None
    if not digits.startswith("+"):
        digits = "+" + digits
    return digits


# ------------------------------------------------------------- helpers
async def safe_delete(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass  # 48 soatdan eski yoki allaqachon o'chirilgan


async def send_question(bot, chat_id, session_id, lang):
    q = await db(services.current_question)(session_id)
    if q is None:
        return False
    header = f"📘 <b>Part {q.part_number} — {html.escape(q.part_title)}</b>"
    lines = [header]
    if q.is_first_in_part and q.part_instruction:
        lines.append(f"<i>{html.escape(q.part_instruction)}</i>")
    lines.append(t(lang, "question", pi=q.part_index, pt=q.part_total, i=q.index, n=q.total))
    lines.append("")
    lines.append(f"<b>{html.escape(q.text)}</b>")
    lines.append("")
    lines.extend(f"<b>{letter})</b> {html.escape(text)}" for _, letter, text in q.options)
    body = "\n".join(lines)
    kb = answers_kb(q.session_id, q.question_id, q.options)

    extra = []
    if q.image_path:
        photo = FSInputFile(q.image_path)
        if len(body) <= CAPTION_LIMIT:
            await bot.send_photo(chat_id, photo, caption=body, reply_markup=kb)
        else:
            m = await bot.send_photo(chat_id, photo)
            extra.append(m.message_id)
            await bot.send_message(chat_id, body, reply_markup=kb)
    else:
        await bot.send_message(chat_id, body, reply_markup=kb)
    if extra:
        _extra_messages[chat_id] = extra
    return True


async def send_result(bot, chat_id, session_id, prefix_key="result_title"):
    r = await db(services.session_result)(session_id)
    lang = r["language"]
    lines = [t(lang, prefix_key), ""]
    for n, p in enumerate(r["parts"], start=1):
        lines.append(t(lang, "part_line", num=n, title=html.escape(p["title"]),
                       c=p["correct"], w=p["wrong"], t=p["total"], pct=p["pct"]))
    lines.append("")
    lines.append(t(lang, "total", c=r["correct"], w=r["wrong"], t=r["total"],
                   pct=round(r["pct"], 1), dur=r["duration"]))
    lines.append("")
    lines.append(t(lang, "thanks"))
    if settings.ALLOW_RETAKE:
        lines.append(t(lang, "retake"))
    await bot.send_message(
        chat_id, "\n".join(lines), reply_markup=menu_kb(lang, can_restart=settings.ALLOW_RETAKE)
    )


# ------------------------------------------------------------- /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    tg_user = await db(services.upsert_user)(user.id, user.username or "")

    active = await db(services.get_active_session)(user.id)
    if active:
        await message.answer(t(active.language, "resume"), reply_markup=menu_kb(active.language))
        await send_question(message.bot, message.chat.id, active.id, active.language)
        return

    if not settings.ALLOW_RETAKE:
        last = await db(services.get_last_finished_session)(user.id)
        if last:
            await send_result(message.bot, message.chat.id, last.id, prefix_key="already_passed")
            return

    if tg_user.phone:
        # Ro'yxatdan avval o'tgan (ism/familiya/telefon saqlangan) — qayta so'ramaymiz,
        # to'g'ridan-to'g'ri tilni so'raymiz. Har safar yangi (tasodifiy) paket tanlanadi.
        await state.set_state(Reg.language)
        await message.answer(REG["ask_lang"], reply_markup=lang_kb())
        return

    await state.set_state(Reg.first_name)
    await message.answer(REG["welcome"], reply_markup=ReplyKeyboardRemove())


@router.message(Command("result"))
async def cmd_result(message: Message):
    last = await db(services.get_last_finished_session)(message.from_user.id)
    if not last:
        await message.answer(t("ru", "no_result") + "\n\n" + t("en", "no_result"))
        return
    await send_result(message.bot, message.chat.id, last.id)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(t("ru", "help") + "\n\n" + t("en", "help"))


# ------------------------------------------------------ registration
@router.message(Reg.first_name, F.text)
async def reg_first(message: Message, state: FSMContext):
    if not valid_name(message.text):
        await message.answer(REG["bad_name"])
        return
    await state.update_data(first_name=nice_name(message.text))
    await state.set_state(Reg.last_name)
    await message.answer(REG["ask_last"])


@router.message(Reg.last_name, F.text)
async def reg_last(message: Message, state: FSMContext):
    if not valid_name(message.text):
        await message.answer(REG["bad_name"])
        return
    await state.update_data(last_name=nice_name(message.text))
    await state.set_state(Reg.phone)
    await message.answer(REG["ask_phone"], reply_markup=phone_kb())


@router.message(Reg.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext):
    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(REG["foreign_contact"], reply_markup=phone_kb())
        return
    phone = normalize_phone(contact.phone_number)
    await _finish_registration(message, state, phone or contact.phone_number)


@router.message(Reg.phone, F.text)
async def reg_phone_text(message: Message, state: FSMContext):
    phone = normalize_phone(message.text)
    if not phone:
        await message.answer(REG["bad_phone"], reply_markup=phone_kb())
        return
    await _finish_registration(message, state, phone)


async def _finish_registration(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    user = message.from_user
    await db(services.upsert_user)(
        user.id, user.username or "",
        first_name=data["first_name"], last_name=data["last_name"], phone=phone,
    )
    await state.set_state(Reg.language)
    await message.answer("✅", reply_markup=ReplyKeyboardRemove())
    await message.answer(REG["ask_lang"], reply_markup=lang_kb())


@router.message(Reg.first_name)
@router.message(Reg.last_name)
async def reg_wrong_type(message: Message):
    await message.answer(REG["bad_name"])


@router.message(Reg.phone)
async def reg_phone_wrong_type(message: Message):
    await message.answer(REG["bad_phone"], reply_markup=phone_kb())


# ---------------------------------------------------------- language
@router.callback_query(Reg.language, F.data.startswith("lang:"))
async def choose_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split(":", 1)[1]
    if lang not in ("ru", "en"):
        await cb.answer()
        return
    await cb.answer()
    await state.clear()
    await safe_delete(cb.bot, cb.message.chat.id, cb.message.message_id)

    uid = cb.from_user.id
    await db(services.upsert_user)(uid, cb.from_user.username or "", language=lang)
    session = await db(services.start_session)(uid, lang)
    if session is None:
        await cb.message.answer(t(lang, "no_tests"))
        return

    titles = await db(services.session_part_titles)(session.id)
    parts = "\n" + "\n".join(f"  • {html.escape(x)}" for x in titles)
    await cb.message.answer(
        t(session.language, "intro", total=session.total_questions, parts=parts),
        reply_markup=menu_kb(session.language),
    )
    await send_question(cb.bot, cb.message.chat.id, session.id, session.language)


@router.callback_query(F.data.startswith("lang:"))
async def lang_outside_flow(cb: CallbackQuery):
    await cb.answer("/start", show_alert=False)
    await safe_delete(cb.bot, cb.message.chat.id, cb.message.message_id)


# ------------------------------------------------------------ answers
@router.callback_query(F.data.startswith("a:"))
async def on_answer(cb: CallbackQuery):
    try:
        _, sid, qid, oid = cb.data.split(":")
        sid, qid, oid = int(sid), int(qid), int(oid)
    except ValueError:
        await cb.answer()
        return

    chat_id = cb.message.chat.id
    result = await db(services.submit_answer)(cb.from_user.id, sid, qid, oid)

    if result in (SubmitResult.STALE, SubmitResult.INVALID):
        active = await db(services.get_active_session)(cb.from_user.id)
        await cb.answer(t(active.language if active else "en", "stale"))
        await safe_delete(cb.bot, chat_id, cb.message.message_id)
        return

    await cb.answer()
    await safe_delete(cb.bot, chat_id, cb.message.message_id)
    for mid in _extra_messages.pop(chat_id, []):
        await safe_delete(cb.bot, chat_id, mid)

    if result == SubmitResult.FINISHED:
        await send_result(cb.bot, chat_id, sid)
        return

    active = await db(services.get_active_session)(cb.from_user.id)
    if active:
        sent = await send_question(cb.bot, chat_id, active.id, active.language)
        if not sent:
            await send_result(cb.bot, chat_id, active.id)


# --------------------------------------------------------- doimiy menyu
MENU_RESULT_TEXTS = {t("ru", "menu_result"), t("en", "menu_result")}
MENU_RESTART_TEXTS = {t("ru", "menu_restart"), t("en", "menu_restart")}
MENU_HELP_TEXTS = {t("ru", "menu_help"), t("en", "menu_help")}


@router.message(F.text.in_(MENU_RESTART_TEXTS))
async def menu_restart(message: Message, state: FSMContext):
    await cmd_start(message, state)


@router.message(F.text.in_(MENU_RESULT_TEXTS))
async def menu_result(message: Message):
    await cmd_result(message)


@router.message(F.text.in_(MENU_HELP_TEXTS))
async def menu_help(message: Message):
    await cmd_help(message)


@router.message()
async def fallback(message: Message):
    active = await db(services.get_active_session)(message.from_user.id)
    if active:
        # Test davomida matn yozilsa — joriy savolni qayta ko'rsatamiz
        await send_question(message.bot, message.chat.id, active.id, active.language)
        return
    await message.answer(t("ru", "help") + "\n\n" + t("en", "help"))
