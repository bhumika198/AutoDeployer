import os
import logging
from celery import Celery

# ----------------------------
# Logger Setup
# ----------------------------
logger = logging.getLogger("celery")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("/root/Documents/AutoDeployer/celery.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)

logger.info("Celery file initialized")

# ----------------------------
# Django settings
# ----------------------------


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deployflow.settings')

app = Celery('deployflow')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()