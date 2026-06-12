import time
import requests
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from quizzes.views import TelegramWebhookView
from rest_framework.test import APIRequestFactory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs a fallback polling loop to ingest Telegram messages'

    def handle(self, *args, **options):
        # We assume TELEGRAM_BOT_TOKEN is set in settings or env
        import os
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN is not set in env.'))
            return

        self.stdout.write(self.style.SUCCESS("Bot is listening for messages via polling..."))
        last_update_id = 0
        factory = APIRequestFactory()
        view = TelegramWebhookView.as_view()
        
        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"offset": last_update_id + 1, "timeout": 30}
                response = requests.get(url, params=params, timeout=35)
                
                if response.status_code == 200:
                    updates = response.json().get("result", [])
                    for update in updates:
                        last_update_id = update["update_id"]
                        
                        # Simulate a webhook request to our view
                        request = factory.post('/api/v1/telegram/webhook/', data=update, format='json')
                        view(request)
                        logger.info(f"Ingested update {last_update_id} via polling.")
                else:
                    self.stdout.write(self.style.ERROR(f"Error getting updates: {response.text}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Polling error: {e}"))
                
            time.sleep(1)
