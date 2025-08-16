# sms_service/tasks.py

from accounts import models
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import DoctorAlarm, AlarmHistory, SMSLog, SystemLog
from .services import sms_service

logger = logging.getLogger(__name__)

@shared_task
def process_alarm_notifications():
    """
    Zamanı gelen alarmları işle - Celery Beat ile her dakika çalışır
    """
    try:
        now = timezone.now()
        
        # Çalışması gereken aktif alarmları bul
        active_alarms = DoctorAlarm.objects.filter(
            status='active',
            next_run__lte=now
        ).exclude(
            end_date__lt=now.date()
        )
        
        processed_count = 0
        success_count = 0
        
        for alarm in active_alarms:
            try:
                # SMS gönder
                result = sms_service.send_sms(
                    phone_number=alarm.patient_phone,
                    message=alarm.message,
                    user=alarm.doctor,
                    message_type=alarm.alarm_type
                )
                
                # SMS Log referansını al
                sms_log = None
                if result.get('sms_log_id'):
                    try:
                        sms_log = SMSLog.objects.get(id=result['sms_log_id'])
                    except SMSLog.DoesNotExist:
                        pass
                
                # Alarm history kaydı oluştur
                AlarmHistory.objects.create(
                    alarm=alarm,
                    sms_log=sms_log,
                    success=result['success'],
                    error_message=result.get('error', '')
                )
                
                # Alarm durumunu güncelle
                alarm.mark_sent(success=result['success'])
                
                if result['success']:
                    success_count += 1
                    logger.info(f"Alarm SMS gönderildi: {alarm.id} - {alarm.patient_name}")
                else:
                    logger.error(f"Alarm SMS hatası: {alarm.id} - {result.get('error')}")
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Alarm işleme hatası: {alarm.id} - {str(e)}")
                
                # Hata kaydı oluştur
                AlarmHistory.objects.create(
                    alarm=alarm,
                    success=False,
                    error_message=str(e)
                )
                
                processed_count += 1
        
        # Sistem logu
        SystemLog.log(
            level='INFO',
            category='ALARM',
            message=f'Alarm işleme: İşlenen: {processed_count}, Başarılı: {success_count}',
            extra_data={
                'processed_count': processed_count,
                'success_count': success_count
            }
        )
        
        logger.info(f"Alarm işleme tamamlandı. İşlenen: {processed_count}, Başarılı: {success_count}")
        
        return {
            'processed_count': processed_count,
            'success_count': success_count
        }
        
    except Exception as e:
        error_msg = f"Alarm işleme genel hatası: {str(e)}"
        logger.error(error_msg)
        
        SystemLog.log(
            level='ERROR',
            category='ALARM',
            message=error_msg
        )
        
        return {'error': error_msg}

@shared_task
def send_immediate_sms(phone_number, message, user_id=None, message_type='General'):
    """
    Anında SMS gönder
    """
    try:
        from accounts.models import User
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        result = sms_service.send_sms(
            phone_number=phone_number,
            message=message,
            user=user,
            message_type=message_type
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Anında SMS hatası: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

@shared_task
def retry_failed_sms():
    """
    Başarısız SMS'leri tekrar dene - günde bir kez çalışır
    """
    try:
        failed_sms_list = SMSLog.objects.filter(
            status='Failed'
        ).filter(
            retry_count__lt=models.F('max_retries')
        )
        
        retry_count = 0
        success_count = 0
        
        for sms_log in failed_sms_list:
            if sms_log.can_retry:
                sms_log.increment_retry()
                
                result = sms_service.send_sms(
                    phone_number=sms_log.recipient_phone,
                    message=sms_log.message,
                    user=sms_log.recipient_user,
                    message_type=sms_log.message_type
                )
                
                if result['success']:
                    success_count += 1
                
                retry_count += 1
        
        SystemLog.log(
            level='INFO',
            category='SMS',
            message=f'SMS tekrar deneme: {retry_count} denendi, {success_count} başarılı',
            extra_data={
                'retry_count': retry_count,
                'success_count': success_count
            }
        )
        
        return {
            'retry_count': retry_count,
            'success_count': success_count
        }
        
    except Exception as e:
        error_msg = f"SMS tekrar deneme hatası: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}

@shared_task
def cleanup_old_sms_logs():
    """
    Eski SMS loglarını temizle - ayda bir çalışır
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=90)  # 90 gün önce
        
        deleted_count = SMSLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        SystemLog.log(
            level='INFO',
            category='SMS',
            message=f'Eski SMS logları temizlendi: {deleted_count}',
            extra_data={'deleted_count': deleted_count}
        )
        
        return {'deleted_count': deleted_count}
        
    except Exception as e:
        error_msg = f"SMS log temizleme hatası: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}