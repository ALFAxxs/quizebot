import asyncio

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Telegram botni long-polling rejimida ishga tushiradi"

    def handle(self, *args, **options):
        from bot.main import run
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            self.stdout.write("Bot to'xtatildi.")
