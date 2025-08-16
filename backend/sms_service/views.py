# sms_service/views.py - AUTHENTICATION BYPASS VERSION

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
# GEÇİCİ: Bu satırı YORUMA ALIN
# from django.contrib.auth.decorators import login_required

# GEÇİCİ: Bu fonksiyonu EKLEYIN - login_required yerine kullanacağız
def login_required(func):
    """Geçici decorator - authentication bypass"""
    return func

from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from datetime import datetime, timedelta
import json
import logging

from .models import DoctorAlarm, AlarmHistory, SMSLog, SMSTemplate, SystemLog

# GEÇİCİ: Bu satırları YORUMA ALIN - eksik modüller varsa hata vermesin
# from .services import sms_service
# from .tasks import send_immediate_sms

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET"])
def doctor_notifications_page(request):
    """
    Doktor bildirimler sayfası
    """
    # GEÇİCİ: Test için basit response
    return JsonResponse({
        'message': 'Doctor notifications page - test mode',
        'status': 'success'
    })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_alarm(request):
    """
    Yeni alarm oluştur - TEST VERSION
    """
    try:
        data = json.loads(request.body)
        
        # Gerekli alanları kontrol et
        required_fields = ['patient_name', 'patient_phone', 'title', 'message', 'alarm_time', 'alarm_type']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'{field} alanı gerekli'
                }, status=400)
        
        # GEÇİCİ: Test kullanıcısı kullan (ID=1)
        from accounts.models import User
        try:
            test_user = User.objects.first()  # İlk kullanıcıyı al
            if not test_user:
                # Eğer hiç kullanıcı yoksa test için basit yanıt ver
                return JsonResponse({
                    'success': True,
                    'alarm_id': 999,  # Test ID
                    'message': 'Alarm başarıyla oluşturuldu (TEST MODE - No Users)',
                })
        except:
            test_user = None
        
        # Alarm oluştur - TARİH FORMATINı DÜZELTELİM
        alarm_fields = {
            'doctor_id': test_user.id if test_user else 1,
            'patient_name': data['patient_name'],
            'patient_phone': data['patient_phone'],
            'title': data['title'],
            'message': data['message'],
            'alarm_time': data['alarm_time'],
            'alarm_type': data['alarm_type'],
            'repeat_type': data.get('repeat_type', 'once'),
            'custom_days': data.get('custom_days', ''),
        }
        
        # Tarih alanlarını kontrol et - boş ise None yap
        alarm_date = data.get('alarm_date')
        if alarm_date and alarm_date.strip():
            alarm_fields['alarm_date'] = alarm_date
        # else: None bırak, ekleme
        
        end_date = data.get('end_date')  
        if end_date and end_date.strip():
            alarm_fields['end_date'] = end_date
        # else: None bırak, ekleme
        
        alarm = DoctorAlarm.objects.create(**alarm_fields)
        
        # Sonraki çalışma zamanını hesapla
        if hasattr(alarm, 'calculate_next_run'):
            alarm.next_run = alarm.calculate_next_run()
            alarm.save()
        
        return JsonResponse({
            'success': True,
            'alarm_id': alarm.id,
            'message': 'Alarm başarıyla oluşturuldu (TEST MODE)',
            'next_run': alarm.next_run.isoformat() if hasattr(alarm, 'next_run') and alarm.next_run else None
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Geçersiz JSON formatı'
        }, status=400)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Alarm oluşturma hatası: {str(e)}")
        logger.error(f"Tam hata: {error_details}")
        
        return JsonResponse({
            'success': False,
            'error': f'Alarm oluşturulamadı: {str(e)}',
            'debug_info': error_details  # DEBUG için
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_immediate_notification(request):
    """
    Anında bildirim gönder - TEST VERSION
    """
    try:
        data = json.loads(request.body)
        
        phone_number = data.get('phone_number')
        message = data.get('message')
        message_type = data.get('message_type', 'General')
        
        if not phone_number or not message:
            return JsonResponse({
                'success': False,
                'error': 'Telefon numarası ve mesaj gerekli'
            }, status=400)
        
        # GEÇİCİ: SMS gönderimi simüle et
        sms_log = SMSLog.objects.create(
            recipient_phone=phone_number,
            message=message,
            message_type=message_type,
            status='Sent'  # Test için başarılı olarak işaretle
        )
        
        return JsonResponse({
            'success': True,
            'task_id': f'test_task_{sms_log.id}',
            'message': 'SMS gönderimi başlatıldı (TEST MODE)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Geçersiz JSON formatı'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Anında bildirim hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Bildirim gönderilemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_doctor_alarms(request):
    """
    Doktorun alarmlarını listele - TEST VERSION
    """
    try:
        # Sayfalama
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        # Filtreleme
        status_filter = request.GET.get('status', 'all')
        alarm_type_filter = request.GET.get('alarm_type', 'all')
        
        # QuerySet oluştur - TÜM ALARMLARI AL (test için)
        alarms = DoctorAlarm.objects.all()
        
        if status_filter != 'all':
            alarms = alarms.filter(status=status_filter)
        
        if alarm_type_filter != 'all':
            alarms = alarms.filter(alarm_type=alarm_type_filter)
        
        alarms = alarms.order_by('-created_at')
        
        # Sayfalama uygula
        paginator = Paginator(alarms, per_page)
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
                'alarm_time': alarm.alarm_time.strftime('%H:%M'),
                'alarm_date': alarm.alarm_date.isoformat() if alarm.alarm_date else None,
                'repeat_type': alarm.repeat_type,
                'status': alarm.status,
                'total_sent': getattr(alarm, 'total_sent', 0),
                'successful_sent': getattr(alarm, 'successful_sent', 0),
                'last_sent': alarm.last_sent.isoformat() if hasattr(alarm, 'last_sent') and alarm.last_sent else None,
                'next_run': alarm.next_run.isoformat() if hasattr(alarm, 'next_run') and alarm.next_run else None,
                'created_at': alarm.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'alarms': alarms_data,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        })
        
    except Exception as e:
        logger.error(f"Alarm listesi hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Alarmlar getirilemedi: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def toggle_alarm_status(request, alarm_id):
    """
    Alarm durumunu değiştir (aktif/duraklat) - TEST VERSION
    """
    try:
        alarm = DoctorAlarm.objects.get(id=alarm_id)  # doctor filtresi kaldırıldı
        
        data = json.loads(request.body)
        action = data.get('action')  # 'pause', 'resume', 'cancel'
        
        if action == 'pause':
            alarm.status = 'paused'
            alarm.save()
            message = 'Alarm duraklatıldı'
        elif action == 'resume':
            alarm.status = 'active'
            alarm.save()
            message = 'Alarm devam ettirildi'
        elif action == 'cancel':
            alarm.status = 'cancelled'
            alarm.save()
            message = 'Alarm iptal edildi'
        else:
            return JsonResponse({
                'success': False,
                'error': 'Geçersiz işlem'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'new_status': alarm.status
        })
        
    except DoctorAlarm.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Alarm bulunamadı'
        }, status=404)
    
    except Exception as e:
        logger.error(f"Alarm durum değişikliği hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'İşlem başarısız: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_sms_logs(request):
    """
    SMS loglarını getir - TEST VERSION
    """
    try:
        # Sayfalama
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Filtreleme
        status_filter = request.GET.get('status', 'all')
        phone_filter = request.GET.get('phone', '')
        
        # SMS logları - TÜM LOGLARI AL
        sms_logs = SMSLog.objects.all()
        
        if status_filter != 'all':
            sms_logs = sms_logs.filter(status=status_filter)
        
        if phone_filter:
            sms_logs = sms_logs.filter(recipient_phone__icontains=phone_filter)
        
        sms_logs = sms_logs.order_by('-created_at')
        
        # Sayfalama
        paginator = Paginator(sms_logs, per_page)
        page_obj = paginator.get_page(page)
        
        # JSON formatına çevir
        logs_data = []
        for log in page_obj:
            logs_data.append({
                'id': log.id,
                'recipient_phone': log.recipient_phone,
                'message': log.message,
                'message_type': getattr(log, 'message_type', 'General'),
                'status': log.status,
                'created_at': log.created_at.isoformat(),
                'sent_at': log.sent_at.isoformat() if hasattr(log, 'sent_at') and log.sent_at else None,
                'delivered_at': log.delivered_at.isoformat() if hasattr(log, 'delivered_at') and log.delivered_at else None,
                'error_message': getattr(log, 'error_message', '') or '',
                'retry_count': getattr(log, 'retry_count', 0)
            })
        
        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages
        })
        
    except Exception as e:
        logger.error(f"SMS log listesi hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'SMS logları getirilemedi: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def sms_callback(request):
    """
    Huawei Cloud SMS callback endpoint
    """
    try:
        data = json.loads(request.body)
        
        # GEÇİCİ: Basit callback simülasyonu
        return JsonResponse({'success': True, 'message': 'Callback received (TEST MODE)'})
        
    except Exception as e:
        logger.error(f"SMS callback hatası: {str(e)}")
        return JsonResponse({'success': False}, status=500)

@login_required
@require_http_methods(["GET"])
def get_alarm_statistics(request):
    """
    Alarm istatistiklerini getir - TEST VERSION
    """
    try:
        # TÜM ALARMLAR İÇİN istatistikler (test için)
        total_alarms = DoctorAlarm.objects.count()
        active_alarms = DoctorAlarm.objects.filter(status='active').count()
        paused_alarms = DoctorAlarm.objects.filter(status='paused').count()
        completed_alarms = DoctorAlarm.objects.filter(status='completed').count()
        cancelled_alarms = DoctorAlarm.objects.filter(status='cancelled').count()
        
        # SMS istatistikleri
        total_sms = SMSLog.objects.count()
        successful_sms = SMSLog.objects.filter(status='Sent').count()
        failed_sms = SMSLog.objects.filter(status='Failed').count()
        pending_sms = SMSLog.objects.filter(status='Pending').count()
        
        # Son 7 günün SMS verileri
        last_7_days = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = SMSLog.objects.filter(
                created_at__date=date
            ).count()
            
            last_7_days.append({
                'date': date.isoformat(),
                'count': count
            })
        
        # Alarm türlerine göre dağılım
        alarm_types = DoctorAlarm.objects.values('alarm_type').annotate(
            count=models.Count('id')
        )
        
        alarm_type_stats = {item['alarm_type']: item['count'] for item in alarm_types}
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'alarms': {
                    'total': total_alarms,
                    'active': active_alarms,
                    'paused': paused_alarms,
                    'completed': completed_alarms,
                    'cancelled': cancelled_alarms
                },
                'sms': {
                    'total': total_sms,
                    'successful': successful_sms,
                    'failed': failed_sms,
                    'pending': pending_sms,
                    'success_rate': round((successful_sms / total_sms * 100) if total_sms > 0 else 0, 2)
                },
                'alarm_types': alarm_type_stats,
                'last_7_days': list(reversed(last_7_days))
            }
        })
        
    except Exception as e:
        logger.error(f"İstatistik hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'İstatistikler getirilemedi: {str(e)}'
        }, status=500)

# BASIT PLACEHOLDER FONKSİYONLAR - Hata vermemesi için
@login_required
@require_http_methods(["GET"])
def get_sms_templates(request):
    return JsonResponse({'success': True, 'templates': []})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_sms_template(request):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_bulk_notification(request):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_medication_alarm(request, medication_id):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_appointment_alarm(request, appointment_id):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@require_http_methods(["GET"])
def get_patient_alarms(request, patient_id=None):
    """
    Hastaya ait alarmları getir - KULLANICI BAZLI FİLTRELEME
    """
    try:
        # Test için - gerçek kullanımda request.user.phone kullanılacak
        if patient_id:
            # Specific patient ID ile çağrılmışsa o hastayı bul
            from accounts.models import User
            try:
                patient_user = User.objects.get(id=patient_id)
                patient_phone = getattr(patient_user, 'phone', '05551234567')
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Hasta bulunamadı'
                }, status=404)
        else:
            # URL parametresi veya test telefonu kullan
            patient_phone = request.GET.get('phone', '05551234567')

        # Query parametreleri
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 50)
        status_filter = request.GET.get('status', 'all')
        alarm_type_filter = request.GET.get('alarm_type', 'all')

        # *** ÖNEMLİ: SADECE HASTAYA AİT ALARMLARI FİLTRELE ***
        queryset = DoctorAlarm.objects.filter(
            patient_phone=patient_phone
        ).order_by('-created_at')

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
                'doctor_name': 'Dr. Test',
                'doctor_specialty': 'Genel Pratisyen',
                'notification_sent': getattr(alarm, 'total_sent', 0) > 0,
                'total_sent': getattr(alarm, 'total_sent', 0),
                'successful_sent': getattr(alarm, 'successful_sent', 0)
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
        
@csrf_exempt
@require_http_methods(["POST"])
def send_patient_sms(request, patient_id):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_alarm(request, alarm_id):
    try:
        alarm = DoctorAlarm.objects.get(id=alarm_id)
        alarm_title = alarm.title
        alarm.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Alarm "{alarm_title}" başarıyla silindi (TEST MODE)'
        })
    except DoctorAlarm.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Alarm bulunamadı'
        }, status=404)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def retry_sms(request, sms_log_id):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@require_http_methods(["GET"])
def get_daily_report(request):
    return JsonResponse({'success': True, 'report': {'message': 'TEST MODE'}})

@login_required
@require_http_methods(["GET"])
def get_monthly_report(request):
    return JsonResponse({'success': True, 'report': {'message': 'TEST MODE'}})

@login_required
@csrf_exempt
@require_http_methods(["PUT"])
def update_sms_template(request, template_id):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_sms_template(request, template_id):
    return JsonResponse({'success': False, 'error': 'Not implemented yet (TEST MODE)'})

@login_required
@require_http_methods(["GET"])
def get_system_settings(request):
    return JsonResponse({
        'success': True,
        'settings': {
            'sms_enabled': True,
            'mode': 'TEST MODE'
        }
    })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_system_settings(request):
    return JsonResponse({'success': True, 'message': 'Settings updated (TEST MODE)'})

@require_http_methods(["GET"])
def health_check(request):
    """Sistem sağlık kontrol - TEST VERSION"""
    try:
        # Veritabanı bağlantısını test et
        alarm_count = DoctorAlarm.objects.count()
        sms_count = SMSLog.objects.count()
        
        health_status = {
            'status': 'healthy',
            'mode': 'TEST MODE - Authentication Bypassed',
            'timestamp': timezone.now().isoformat(),
            'database': {
                'connected': True,
                'alarm_count': alarm_count,
                'sms_count': sms_count
            },
            'services': {
                'sms_service': 'running (test mode)',
            }
        }
        
        return JsonResponse(health_status)
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)  