from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TelegramUser

@admin.register(TelegramUser)
class TelegramUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Telegram Info', {'fields': ('telegram_id', 'is_premium')}),
    )
    list_display = ('username', 'telegram_id', 'is_premium', 'is_staff')
