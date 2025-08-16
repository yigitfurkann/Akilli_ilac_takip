# settings.py dosyanızın sonuna şunları ekleyin:

# ==================== HUAWEI CLOUD SMS AYARLARI ====================
import os
from decouple import config

from django.conf import settings

INSTALLED_APPS = list(settings.INSTALLED_APPS)

# Huawei Cloud SMS konfigürasyonu
HUAWEI_ACCESS_KEY = config('HUAWEI_ACCESS_KEY', default='')
HUAWEI_SECRET_KEY = config('HUAWEI_SECRET_KEY', default='')
HUAWEI_SMS_ENDPOINT = config('HUAWEI_SMS_ENDPOINT', default='https://smsapi.tr-west-1.myhuaweicloud.com')
HUAWEI_SMS_APP_KEY = config('HUAWEI_SMS_APP_KEY', default='')
HUAWEI_SMS_APP_SECRET = config('HUAWEI_SMS_APP_SECRET', default='')
HUAWEI_SMS_CHANNEL_NUMBER = config('HUAWEI_SMS_CHANNEL_NUMBER', default='')
HUAWEI_SMS_SENDER = config('HUAWEI_SMS_SENDER', default='SMS-INFO')

# Celery konfigürasyonu (SMS'leri asenkron göndermek için)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Istanbul'

# Celery Beat Schedule (Cron Jobs)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Her dakika alarm kontrolü
    'process-alarm-notifications': {
        'task': 'sms_service.tasks.process_alarm_notifications',
        'schedule': crontab(minute='*'),  # Her dakika
    },
    
    # Başarısız SMS'leri tekrar dene (günde bir kez)
    'retry-failed-sms': {
        'task': 'sms_service.tasks.retry_failed_sms',
        'schedule': crontab(hour=2, minute=0),  # Her gün saat 02:00
    },
    
    # Eski SMS loglarını temizle (ayda bir)
    'cleanup-old-sms-logs': {
        'task': 'sms_service.tasks.cleanup_old_sms_logs',
        'schedule': crontab(day_of_month=1, hour=3, minute=0),  # Her ayın 1'i saat 03:00
    },
}

# INSTALLED_APPS'e sms_service'i ekleyin (eğer henüz eklenmemişse)
if 'sms_service' not in INSTALLED_APPS:
    INSTALLED_APPS.append('sms_service')

# Base URL (SMS callback için)
BASE_URL = config('BASE_URL', default='http://localhost:8000')

# Logging konfigürasyonu
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'sms_service.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'sms_service': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}