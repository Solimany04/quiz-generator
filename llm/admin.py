from django.contrib import admin
import httpx
from .models import ModelRegistry
from django.contrib import messages

@admin.register(ModelRegistry)
class ModelRegistryAdmin(admin.ModelAdmin):
    list_display = ('model_identifier', 'is_downloaded', 'is_active_default', 'last_checked')
    list_editable = ('is_active_default',)
    actions = ['sync_with_lm_studio']

    @admin.action(description='Sync available models from local LM Studio')
    def sync_with_lm_studio(self, request, queryset):
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get('http://localhost:1234/v1/models')
                response.raise_for_status()
                data = response.json()
                
                added = 0
                for model_data in data.get('data', []):
                    model_id = model_data.get('id')
                    if model_id:
                        obj, created = ModelRegistry.objects.get_or_create(
                            model_identifier=model_id,
                            defaults={'is_downloaded': True}
                        )
                        if created:
                            added += 1
                        else:
                            obj.is_downloaded = True
                            obj.save()
                
                self.message_user(request, f'Successfully synced models. Added {added} new models.', messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f'Failed to sync with LM Studio: {e}', level=messages.ERROR)
