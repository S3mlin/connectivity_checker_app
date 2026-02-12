import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "connectivity_checker_app.settings")

app = Celery("connectivity_checker_app")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()