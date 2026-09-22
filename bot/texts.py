"""Bot matnlari. Ro'yxatdan o'tish bosqichida til hali noma'lum — shuning uchun RU + EN."""

REG = {
    "welcome": (
        "👋 <b>Добро пожаловать!</b> / <b>Welcome!</b>\n\n"
        "Для начала теста пройдите короткую регистрацию.\n"
        "Please complete a short registration to start the test.\n\n"
        "✍️ Введите ваше <b>имя</b> / Enter your <b>first name</b>:"
    ),
    "ask_last": "✍️ Введите вашу <b>фамилию</b> / Enter your <b>last name</b>:",
    "ask_phone": (
        "📱 Отправьте ваш <b>номер телефона</b> кнопкой ниже или введите вручную (+998901234567).\n"
        "Send your <b>phone number</b> using the button below or type it (+998901234567)."
    ),
    "bad_name": "⚠️ Введите корректное значение (2–50 букв) / Enter a valid value (2–50 letters).",
    "bad_phone": "⚠️ Неверный номер. Пример: +998901234567 / Invalid number. Example: +998901234567",
    "foreign_contact": "⚠️ Отправьте свой собственный контакт / Please send your own contact.",
    "ask_lang": "🌐 Выберите язык теста / Choose the test language:",
    "share_phone_btn": "📱 Отправить номер / Share phone",
}

T = {
    "ru": {
        "no_tests": "😔 Сейчас нет доступных тестов. Попробуйте позже.",
        "intro": (
            "📝 <b>Тест начинается!</b>\n\n"
            "Всего вопросов: <b>{total}</b>\n"
            "Разделы: {parts}\n\n"
            "Нажмите на букву правильного ответа. После ответа вопрос исчезнет, "
            "а изменить ответ будет нельзя. Удачи! 🍀"
        ),
        "resume": "⏯ У вас есть незавершённый тест. Продолжаем с того же места.",
        "question": "Вопрос {pi} из {pt}  •  всего {i}/{n}",
        "already_passed": "ℹ️ Вы уже прошли тест. Ваш результат:",
        "stale": "Этот вопрос уже неактуален",
        "result_title": "🏁 <b>Тест завершён!</b>",
        "part_line": "<b>Part {num} — {title}</b>\n   ✅ {c}  ❌ {w}  из {t}  —  <b>{pct}%</b>",
        "total": (
            "📊 <b>Общий результат: {c}/{t} — {pct}%</b>\n"
            "✅ Правильных: {c}\n❌ Неправильных: {w}\n⏱ Время: {dur}"
        ),
        "thanks": "Спасибо за участие!",
        "retake": "Чтобы пройти тест ещё раз, нажмите /start",
        "no_result": "У вас пока нет результатов. Нажмите /start, чтобы начать тест.",
        "help": "/start — начать тест\n/result — мой последний результат",
        "menu_result": "📊 Мой результат",
        "menu_restart": "🔄 Начать заново",
        "menu_help": "❓ Помощь",
    },
    "en": {
        "no_tests": "😔 No tests are available right now. Please try again later.",
        "intro": (
            "📝 <b>The test is starting!</b>\n\n"
            "Total questions: <b>{total}</b>\n"
            "Sections: {parts}\n\n"
            "Tap the letter of the correct answer. The question disappears after you answer "
            "and the answer can't be changed. Good luck! 🍀"
        ),
        "resume": "⏯ You have an unfinished test. Continuing where you left off.",
        "question": "Question {pi} of {pt}  •  overall {i}/{n}",
        "already_passed": "ℹ️ You have already taken the test. Your result:",
        "stale": "This question is no longer active",
        "result_title": "🏁 <b>Test completed!</b>",
        "part_line": "<b>Part {num} — {title}</b>\n   ✅ {c}  ❌ {w}  of {t}  —  <b>{pct}%</b>",
        "total": (
            "📊 <b>Overall result: {c}/{t} — {pct}%</b>\n"
            "✅ Correct: {c}\n❌ Wrong: {w}\n⏱ Time: {dur}"
        ),
        "thanks": "Thank you for participating!",
        "retake": "To take the test again, press /start",
        "no_result": "You have no results yet. Press /start to begin the test.",
        "help": "/start — start the test\n/result — my last result",
        "menu_result": "📊 My result",
        "menu_restart": "🔄 Start over",
        "menu_help": "❓ Help",
    },
}


def t(lang, key, **kw):
    text = T.get(lang or "en", T["en"])[key]
    return text.format(**kw) if kw else text
