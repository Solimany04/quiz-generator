import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Sets the Telegram webhook URL'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The full HTTPS URL for the webhook (e.g., https://<ngrok-url>/api/v1/telegram/webhook/)')

    def handle(self, *args, **options):
        url = options['url']
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if getattr(settings, 'TELEGRAM_BOT_TOKEN', None):
            token = token or settings.TELEGRAM_BOT_TOKEN

        if not token:
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN is not set in env or settings.'))
            return

        if not url.startswith('https://'):
            self.stdout.write(self.style.ERROR('Webhook URL must start with https://'))
            return

        api_url = f"https://api.telegram.org/bot{token}/setWebhook"
        try:
            response = requests.post(api_url, data={'url': url})
            result = response.json()
            if result.get('ok'):
                self.stdout.write(self.style.SUCCESS(f"Successfully set webhook to {url}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to set webhook: {result.get('description')}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error setting webhook: {e}"))
