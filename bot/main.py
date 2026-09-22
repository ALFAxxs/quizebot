import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from django.conf import settings

from .handlers import router

log = logging.getLogger(__name__)


async def run():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.set_my_commands([
        BotCommand(command="start", description="Start test / Начать тест"),
        BotCommand(command="result", description="My result / Мой результат"),
        BotCommand(command="help", description="Help / Помощь"),
    ])
    await bot.delete_webhook(drop_pending_updates=False)
    me = await bot.get_me()
    log.info("Bot @%s ishga tushdi", me.username)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
