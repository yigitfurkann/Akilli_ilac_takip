#sms_service/patient_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, timedelta
import json
import logging

# Mevcut modellerinizi import edin
from .models import DoctorAlarm, SMSLog

logger = logging.getLogger(__name__)

# GEÇİCİ: Authentication bypass için
def login_required(func):
    """Geçici decorator - authentication bypass"""
    return func

@login_required
@require_http_methods(["GET"])
def get_patient_alarms(request):
    """
    Hastaya ait alarmları getir - Backend'deki mevcut alarmları kullan
    """
    try:
        # Test için - gerçek kullanımda request.user.phone kullanılacak
        patient_phone = request.GET.get('phone', '05551234567')  # Test telefonu

        # Query parametreleri
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 50)
        status_filter = request.GET.get('status', 'all')
        alarm_type_filter = request.GET.get('alarm_type', 'all')

        # Hastanın telefon numarasına göre alarmları bul
        queryset = DoctorAlarm.objects.all().order_by('-created_at')

        # Filtreleme
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        if alarm_type_filter != 'all':
            queryset = queryset.filter(alarm_type=alarm_type_filter)

        # Pagination
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        # JSON formatına çevir
        alarms_data = []
        for alarm in page_obj:
            alarms_data.append({
                'id': alarm.id,
                'title': alarm.title,
                'patient_name': alarm.patient_name,
                'patient_phone': alarm.patient_phone,
                'message': alarm.message,
                'alarm_type': alarm.alarm_type,
                'alarm_time': alarm.alarm_time.strftime('%H:%M') if alarm.alarm_time else None,
                'alarm_date': alarm.alarm_date.isoformat() if alarm.alarm_date else None,
                'repeat_type': alarm.repeat_type,
                'status': alarm.status,
                'created_at': alarm.created_at.isoformat(),
                'is_patient_alarm': True,
                'doctor_name': 'Dr. Test',  # Test için
                'doctor_specialty': 'Genel Pratisyen',
                'notification_sent': getattr(alarm, 'total_sent', 0) > 0,
                'next_trigger': calculate_next_trigger_time(alarm),
                'days_active': (timezone.now().date() - alarm.created_at.date()).days
            })

        return JsonResponse({
            'success': True,
            'alarms': alarms_data,
            'total': paginator.count,
            'page': page,
            'per_page': per_page,
            'has_next': page_obj.has_next(),
            'statistics': {
                'active': queryset.filter(status='active').count(),
                'paused': queryset.filter(status='paused').count(),
                'completed': queryset.filter(status='completed').count(),
                'total': queryset.count()
            }
        })

    except Exception as e:
        logger.error(f"Patient alarms error: {str(e)}")
        return JsonResponse({
            'success': False,
            'alarms': [],
            'error': f'Hasta alarmları yüklenemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_patient_alarm_history(request):
    """
    Hastanın alarm geçmişini getir
    """
    try:
        patient_phone = request.GET.get('phone', '05551234567')  # Test

        # Query parametreleri
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 50)), 100)

        # SMS loglarından geçmişi al
        queryset = SMSLog.objects.all().order_by('-created_at')

        # Pagination
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        # JSON formatına çevir
        history_data = []
        for log in page_obj:
            history_data.append({
                'id': log.id,
                'recipient_phone': log.recipient_phone,
                'message': log.message,
                'message_type': getattr(log, 'message_type', 'General'),
                'status': log.status,
                'created_at': log.created_at.isoformat(),
                'is_successful': log.status.lower() in ['sent', 'delivered'],
                'formatted_date': log.created_at.strftime('%d.%m.%Y %H:%M'),
                'doctor_name': 'Dr. Test',
                'alarm_type': 'medication'
            })

        return JsonResponse({
            'success': True,
            'history': history_data,
            'total': paginator.count,
            'page': page,
            'per_page': per_page,
            'has_next': page_obj.has_next(),
            'statistics': {
                'total_messages': paginator.count,
                'successful': queryset.filter(status__icontains='sent').count(),
                'failed': queryset.filter(status__icontains='failed').count()
            }
        })

    except Exception as e:
        logger.error(f"Patient alarm history error: {str(e)}")
        return JsonResponse({
            'success': False,
            'history': [],
            'error': f'Alarm geçmişi yüklenemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_patient_upcoming_alarms(request):
    """
    Hastanın yaklaşan alarmlarını getir
    """
    try:
        patient_phone = request.GET.get('phone', '05551234567')  # Test

        # Aktif alarmları getir
        active_alarms = DoctorAlarm.objects.filter(
            status='active'
        ).order_by('alarm_time')[:10]

        upcoming = []
        today = timezone.now().date()

        for alarm in active_alarms:
            next_trigger = calculate_next_trigger_time(alarm)
            if next_trigger:
                upcoming.append({
                    'id': alarm.id,
                    'title': alarm.title,
                    'message': alarm.message,
                    'alarm_time': alarm.alarm_time.strftime('%H:%M') if alarm.alarm_time else None,
                    'next_trigger': next_trigger,
                    'alarm_type': alarm.alarm_type,
                    'doctor_name': 'Dr. Test',
                    'is_today': next_trigger and datetime.fromisoformat(next_trigger).date() == today,
                    'hours_until': calculate_hours_until(next_trigger) if next_trigger else 0
                })

        return JsonResponse({
            'success': True,
            'upcoming_alarms': upcoming,
            'count': len(upcoming)
        })

    except Exception as e:
        logger.error(f"Patient upcoming alarms error: {str(e)}")
        return JsonResponse({
            'success': False,
            'upcoming_alarms': [],
            'count': 0,
            'error': f'Yaklaşan alarmlar yüklenemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_patient_notification_settings(request):
    """
    Hastanın bildirim tercihlerini getir
    """
    try:
        # Test ayarları
        settings = {
            'sms_enabled': True,
            'email_enabled': False,
            'medication_reminders': True,
            'appointment_reminders': True,
            'general_notifications': True,
            'quiet_hours_enabled': False,
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '08:00',
            'preferred_language': 'tr',
            'phone_number': '05551234567',
            'email': ''
        }

        return JsonResponse({
            'success': True,
            'settings': settings
        })

    except Exception as e:
        logger.error(f"Patient notification settings error: {str(e)}")
        return JsonResponse({
            'success': False,
            'settings': {},
            'error': f'Bildirim ayarları yüklenemedi: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["PUT"])
def update_patient_notification_settings(request):
    """
    Hastanın bildirim tercihlerini güncelle
    """
    try:
        data = json.loads(request.body)

        # Test için - başarılı response döndür
        return JsonResponse({
            'success': True,
            'message': 'Bildirim ayarları güncellendi (TEST MODE)',
            'settings': data
        })

    except Exception as e:
        logger.error(f"Patient notification settings update error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Ayarlar güncellenirken hata oluştu: {str(e)}'
        }, status=500)

# Helper functions
def calculate_next_trigger_time(alarm):
    """Alarmın bir sonraki tetiklenme zamanını hesapla"""
    try:
        now = timezone.now()
        today = now.date()

        # Alarm saatini parse et
        if hasattr(alarm, 'alarm_time') and alarm.alarm_time:
            alarm_time = alarm.alarm_time

            if alarm.repeat_type == 'once':
                # Tek seferlik alarm
                if alarm.alarm_date:
                    alarm_datetime = timezone.make_aware(
                        datetime.combine(alarm.alarm_date, alarm_time)
                    )
                    return alarm_datetime.isoformat() if alarm_datetime > now else None
                else:
                    # Bugün için
                    today_datetime = timezone.make_aware(
                        datetime.combine(today, alarm_time)
                    )
                    return today_datetime.isoformat() if today_datetime > now else None

            elif alarm.repeat_type == 'daily':
                # Günlük alarm
                today_datetime = timezone.make_aware(
                    datetime.combine(today, alarm_time)
                )

                if today_datetime > now:
                    return today_datetime.isoformat()
                else:
                    # Yarın
                    tomorrow = today + timedelta(days=1)
                    tomorrow_datetime = timezone.make_aware(
                        datetime.combine(tomorrow, alarm_time)
                    )
                    return tomorrow_datetime.isoformat()

        return None

    except Exception as e:
        logger.error(f"Next trigger calculation error: {str(e)}")
        return None

def calculate_hours_until(next_trigger_str):
    """Bir sonraki tetiklenmeye kadar kaç saat olduğunu hesapla"""
    try:
        if next_trigger_str:
            next_trigger = datetime.fromisoformat(next_trigger_str.replace('Z', '+00:00'))
            now = timezone.now()
            if next_trigger > now:
                return int((next_trigger - now).total_seconds() / 3600)
        return 0
    except:
        return 0
