from django.db import models

class ModelRegistry(models.Model):
    model_identifier = models.CharField(max_length=255, unique=True)
    is_downloaded = models.BooleanField(default=False)
    file_size = models.CharField(max_length=50, null=True, blank=True)
    is_active_default = models.BooleanField(default=False)
    last_checked = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.model_identifier

    def save(self, *args, **kwargs):
        if self.is_active_default:
            ModelRegistry.objects.filter(is_active_default=True).update(is_active_default=False)
        super().save(*args, **kwargs)
