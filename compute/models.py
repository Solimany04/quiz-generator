from django.db import models
from django.conf import settings
import uuid

class UserComputeNode(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='compute_node')
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    total_processed_tasks = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Node for {self.user.username}"
