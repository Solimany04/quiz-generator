from django.db import models
from django.contrib.auth.models import AbstractUser

class TelegramUser(AbstractUser):
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.username or str(self.telegram_id)
