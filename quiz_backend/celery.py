import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quiz_backend.settings')

app = Celery('quiz_backend')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
