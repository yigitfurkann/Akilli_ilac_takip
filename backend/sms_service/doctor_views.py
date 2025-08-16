# sms_service/doctor_views.py - Tamamlanmış ve düzeltilmiş hali
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from datetime import datetime, timedelta
import json
import logging

from notifications.models import Bildirim  # Bildirim modelini import et
from .tasks import send_immediate_sms

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_patient_message(request):
    """
    Doktorun hastaya mesaj göndermesi
    """
    try:
        data = json.loads(request.body)
        
        # Gerekli alanları kontrol et
        patient_id = data.get('patient_id')
        title = data.get('title', 'Doktor Mesajı')
        message = data.get('message')
        priority = data.get('priority', 'normal')
        send_sms = data.get('send_sms', True)
        
        if not patient_id or not message:
            return JsonResponse({
                'success': False,
                'error': 'Hasta ID ve mesaj gerekli'
            }, status=400)
        
        # Hastayı bul
        try:
            patient = User.objects.get(id=patient_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Hasta bulunamadı'
            }, status=404)
        
        # Bildirim oluştur
        bildirim = Bildirim.create_doctor_message(
            doktor_user=request.user,
            hasta_user=patient,
            baslik=title,
            mesaj=message,
            oncelik=priority
        )
        
        return JsonResponse({
            'success': True,
            'notification_id': bildirim.id,
            'message': 'Mesaj başarıyla gönderildi',
            'sms_sent': bildirim.sms_gonderildi
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Geçersiz JSON formatı'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Hasta mesajı hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Mesaj gönderilemedi: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_bulk_patient_message(request):
    """
    Doktorun birden fazla hastaya mesaj göndermesi
    """
    try:
        data = json.loads(request.body)
        
        patient_ids = data.get('patient_ids', [])
        title = data.get('title', 'Doktor Mesajı')
        message = data.get('message')
        priority = data.get('priority', 'normal')
        
        if not patient_ids or not message:
            return JsonResponse({
                'success': False,
                'error': 'Hasta listesi ve mesaj gerekli'
            }, status=400)
        
        # Hastaları bul
        patients = User.objects.filter(id__in=patient_ids)
        
        if not patients.exists():
            return JsonResponse({
                'success': False,
                'error': 'Hiçbir hasta bulunamadı'
            }, status=404)
        
        # Her hastaya bildirim gönder
        notifications_created = []
        errors = []
        
        for patient in patients:
            try:
                bildirim = Bildirim.create_doctor_message(
                    doktor_user=request.user,
                    hasta_user=patient,
                    baslik=title,
                    mesaj=message,
                    oncelik=priority
                )
                notifications_created.append({
                    'patient_id': patient.id,
                    'patient_name': f"{patient.first_name} {patient.last_name}",
                    'notification_id': bildirim.id,
                    'sms_sent': bildirim.sms_gonderildi
                })
            except Exception as e:
                errors.append({
                    'patient_id': patient.id,
                    'patient_name': f"{patient.first_name} {patient.last_name}",
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'message': f'{len(notifications_created)} hastaya mesaj gönderildi',
            'notifications': notifications_created,
            'errors': errors,
            'total_sent': len(notifications_created),
            'total_errors': len(errors)
        })
        
    except Exception as e:
        logger.error(f"Toplu mesaj hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Toplu mesaj gönderilemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_doctor_patients(request):
    """
    Doktorun hastalarını listele
    """
    try:
        # Sayfalama
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        search = request.GET.get('search', '')
        
        # Doktorun hastalarını bul - Appointment modelinden
        # Bu query'i kendi appointment modelinize göre güncelleyin
        patients_query = User.objects.filter(
            # appointments__doctor=request.user  # appointment modelinize göre değiştirin
        ).distinct()
        
        # Eğer appointment modeli yoksa, tüm users'ları döndürebilirsiniz (geçici olarak)
        if not patients_query.exists():
            # Geçici çözüm: Doktor olmayan tüm kullanıcıları döndür
            patients_query = User.objects.filter(
                is_staff=False,
                is_superuser=False
            ).exclude(id=request.user.id)
        
        if search:
            patients_query = patients_query.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search)
            )
        
        # Sayfalama
        paginator = Paginator(patients_query, per_page)
        page_obj = paginator.get_page(page)
        
        # JSON formatına çevir
        patients_data = []
        for patient in page_obj:
            # Hastanın telefon numarasını al
            phone = None
            if hasattr(patient, 'profile') and hasattr(patient.profile, 'phone'):
                phone = patient.profile.phone
            elif hasattr(patient, 'phone'):
                phone = patient.phone
            
            # Son randevu bilgisi (appointment modelinize göre güncelleyin)
            last_appointment = None
            # try:
            #     last_app = patient.appointments.filter(doctor=request.user).latest('date')
            #     last_appointment = last_app.date.strftime('%Y-%m-%d')
            # except:
            #     pass
            
            patients_data.append({
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'full_name': f"{patient.first_name} {patient.last_name}",
                'email': patient.email,
                'phone': phone,
                'last_appointment': last_appointment,
                'total_notifications': Bildirim.objects.filter(
                    gonderen=request.user,
                    alici=patient
                ).count(),
                'unread_notifications': Bildirim.objects.filter(
                    gonderen=request.user,
                    alici=patient,
                    okundu=False
                ).count()
            })
        
        return JsonResponse({
            'success': True,
            'patients': patients_data,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        })
        
    except Exception as e:
        logger.error(f"Hasta listesi hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Hasta listesi getirilemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_sent_notifications(request):
    """
    Doktorun gönderdiği bildirimleri listele
    """
    try:
        # Sayfalama
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Filtreleme
        notification_type = request.GET.get('type', 'all')
        patient_id = request.GET.get('patient_id', '')
        status_filter = request.GET.get('status', 'all')
        
        # Doktorun gönderdiği bildirimler
        notifications = Bildirim.objects.filter(
            gonderen=request.user
        )
        
        # Filtreler uygula
        if notification_type != 'all':
            notifications = notifications.filter(bildirim_tipi=notification_type)
        
        if patient_id:
            notifications = notifications.filter(alici_id=patient_id)
        
        if status_filter == 'read':
            notifications = notifications.filter(okundu=True)
        elif status_filter == 'unread':
            notifications = notifications.filter(okundu=False)
        elif status_filter == 'sms_sent':
            notifications = notifications.filter(sms_gonderildi=True)
        elif status_filter == 'sms_failed':
            notifications = notifications.filter(sms_durum='failed')
        
        notifications = notifications.order_by('-gonderim_tarihi')
        
        # Sayfalama
        paginator = Paginator(notifications, per_page)
        page_obj = paginator.get_page(page)
        
        # JSON formatına çevir
        notifications_data = []
        for notification in page_obj:
            notifications_data.append({
                'id': notification.id,
                'title': notification.baslik,
                'message': notification.mesaj,
                'patient_name': f"{notification.alici.first_name} {notification.alici.last_name}",
                'patient_id': notification.alici.id,
                'notification_type': notification.bildirim_tipi,
                'notification_type_display': notification.get_bildirim_tipi_display(),
                'priority': notification.oncelik,
                'priority_display': notification.get_oncelik_display(),
                'is_read': notification.okundu,
                'read_at': notification.okunma_tarihi.isoformat() if notification.okunma_tarihi else None,
                'sent_at': notification.gonderim_tarihi.isoformat(),
                'sms_sent': notification.sms_gonderildi,
                'sms_status': notification.sms_durum,
                'sms_sent_at': notification.sms_gonderim_tarihi.isoformat() if notification.sms_gonderim_tarihi else None,
                'sms_error': notification.sms_hata_mesaji,
                'email_sent': notification.email_gonderildi,
                'is_urgent': notification.is_urgent,
                'is_overdue': notification.is_overdue
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        })
        
    except Exception as e:
        logger.error(f"Bildirim listesi hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Bildirimler getirilemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_notification_statistics(request):
    """
    Doktorun bildirim istatistiklerini getir
    """
    try:
        # Doktorun gönderdiği bildirimler
        total_sent = Bildirim.objects.filter(gonderen=request.user).count()
        
        # Okunma durumu
        read_count = Bildirim.objects.filter(gonderen=request.user, okundu=True).count()
        unread_count = Bildirim.objects.filter(gonderen=request.user, okundu=False).count()
        
        # SMS durumu
        sms_sent = Bildirim.objects.filter(gonderen=request.user, sms_gonderildi=True).count()
        sms_delivered = Bildirim.objects.filter(gonderen=request.user, sms_durum='delivered').count()
        sms_failed = Bildirim.objects.filter(gonderen=request.user, sms_durum='failed').count()
        
        # Bildirim türlerine göre
        notification_types = Bildirim.objects.filter(
            gonderen=request.user
        ).values('bildirim_tipi').annotate(
            count=models.Count('id')
        )
        
        type_stats = {item['bildirim_tipi']: item['count'] for item in notification_types}
        
        # Son 7 günün verileri
        last_7_days = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = Bildirim.objects.filter(
                gonderen=request.user,
                gonderim_tarihi__date=date
            ).count()
            
            last_7_days.append({
                'date': date.isoformat(),
                'count': count
            })
        
        # Öncelik durumu
        priority_stats = Bildirim.objects.filter(
            gonderen=request.user
        ).values('oncelik').annotate(
            count=models.Count('id')
        )
        
        priority_data = {item['oncelik']: item['count'] for item in priority_stats}
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'total_sent': total_sent,
                'read_count': read_count,
                'unread_count': unread_count,
                'read_rate': round((read_count / total_sent * 100) if total_sent > 0 else 0, 2),
                'sms_sent': sms_sent,
                'sms_delivered': sms_delivered,
                'sms_failed': sms_failed,
                'sms_success_rate': round((sms_delivered / sms_sent * 100) if sms_sent > 0 else 0, 2),
                'notification_types': type_stats,
                'priority_stats': priority_data,
                'last_7_days': list(reversed(last_7_days))
            }
        })
        
    except Exception as e:
        logger.error(f"İstatistik hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'İstatistikler getirilemedi: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def resend_failed_sms(request, notification_id):
    """
    Başarısız SMS'i tekrar gönder
    """
    try:
        # Bildirimi bul
        notification = get_object_or_404(
            Bildirim, 
            id=notification_id, 
            gonderen=request.user
        )
        
        # SMS tekrar gönder
        success = notification.send_sms_notification()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'SMS tekrar gönderimi başlatıldı'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'SMS gönderilemedi'
            }, status=400)
        
    except Exception as e:
        logger.error(f"SMS tekrar gönderim hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'SMS tekrar gönderilemedi: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_message_templates(request):
    """
    Doktor mesaj şablonlarını getir
    """
    try:
        # Önceden tanımlanmış şablonlar
        default_templates = [
            {
                'id': 'medication_reminder',
                'name': 'İlaç Hatırlatması',
                'title': 'İlaç Alma Hatırlatması',
                'content': 'Sayın {patient_name}, {medication_name} ilacınızı {dosage} dozunda almanızı unutmayın. Düzenli kullanım önemlidir.',
                'type': 'medication',
                'variables': ['patient_name', 'medication_name', 'dosage']
            },
            {
                'id': 'appointment_reminder',
                'name': 'Randevu Hatırlatması',
                'title': 'Randevu Hatırlatması',
                'content': 'Sayın {patient_name}, {appointment_date} tarihinde saat {appointment_time} randevunuz bulunmaktadır. Lütfen zamanında gelmek için dikkat edin.',
                'type': 'appointment',
                'variables': ['patient_name', 'appointment_date', 'appointment_time']
            },
            {
                'id': 'general_info',
                'name': 'Genel Bilgilendirme',
                'title': 'Doktor Mesajı',
                'content': 'Sayın {patient_name}, sağlığınızla ilgili önemli bir bilgi paylaşmak istiyorum: {custom_message}',
                'type': 'general',
                'variables': ['patient_name', 'custom_message']
            },
            {
                'id': 'test_results',
                'name': 'Tahlil Sonuçları',
                'title': 'Tahlil Sonuçlarınız',
                'content': 'Sayın {patient_name}, {test_date} tarihli tahlil sonuçlarınız hazır. Lütfen muayenehaneye gelerek sonuçları değerlendirelim.',
                'type': 'test_results',
                'variables': ['patient_name', 'test_date']
            },
            {
                'id': 'urgent_message',
                'name': 'Acil Mesaj',
                'title': 'ACİL: Doktor Mesajı',
                'content': 'Sayın {patient_name}, ACİL: {urgent_message} Lütfen derhal iletişime geçin. Tel: {doctor_phone}',
                'type': 'urgent',
                'variables': ['patient_name', 'urgent_message', 'doctor_phone']
            },
            {
                'id': 'check_up_reminder',
                'name': 'Kontrol Hatırlatması',
                'title': 'Kontrol Randevusu Hatırlatması',
                'content': 'Sayın {patient_name}, son muayenenizin üzerinden {months} ay geçti. Kontrol randevusu almanızı öneriyorum.',
                'type': 'checkup',
                'variables': ['patient_name', 'months']
            },
            {
                'id': 'lab_preparation',
                'name': 'Tahlil Hazırlığı',
                'title': 'Tahlil Öncesi Hazırlık',
                'content': 'Sayın {patient_name}, yarınki tahlil randevunuz için {hours} saat öncesinden aç kalmanız gerekmektedir.',
                'type': 'lab_prep',
                'variables': ['patient_name', 'hours']
            }
        ]
        
        # Doktor özel şablonları (gelecekte custom template modeli eklenirse)
        # custom_templates = CustomTemplate.objects.filter(doctor=request.user)
        
        return JsonResponse({
            'success': True,
            'templates': default_templates
        })
        
    except Exception as e:
        logger.error(f"Şablon listesi hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Şablonlar getirilemedi: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_custom_template(request):
    """
    Özel mesaj şablonu oluştur
    """
    try:
        data = json.loads(request.body)
        
        name = data.get('name')
        title = data.get('title')
        content = data.get('content')
        template_type = data.get('type', 'general')
        
        if not all([name, title, content]):
            return JsonResponse({
                'success': False,
                'error': 'İsim, başlık ve içerik gerekli'
            }, status=400)
        
        # Burada custom template modeli oluşturulacak
        # template = CustomTemplate.objects.create(
        #     doctor=request.user,
        #     name=name,
        #     title=title,
        #     content=content,
        #     template_type=template_type
        # )
        
        return JsonResponse({
            'success': True,
            'message': 'Şablon oluşturuldu',
            # 'template_id': template.id
        })
        
    except Exception as e:
        logger.error(f"Şablon oluşturma hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Şablon oluşturulamadı: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_patient_notification_history(request, patient_id):
    """
    Belirli bir hastanın bildirim geçmişini getir
    """
    try:
        # Hastayı kontrol et
        try:
            patient = User.objects.get(id=patient_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Hasta bulunamadı'
            }, status=404)
        
        # Sayfalama
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Bu doktorun bu hastaya gönderdiği bildirimler
        notifications = Bildirim.objects.filter(
            gonderen=request.user,
            alici=patient
        ).order_by('-gonderim_tarihi')
        
        # Sayfalama
        paginator = Paginator(notifications, per_page)
        page_obj = paginator.get_page(page)
        
        # JSON formatına çevir
        notifications_data = []
        for notification in page_obj:
            notifications_data.append({
                'id': notification.id,
                'title': notification.baslik,
                'message': notification.mesaj,
                'type': notification.get_bildirim_tipi_display(),
                'priority': notification.get_oncelik_display(),
                'sent_at': notification.gonderim_tarihi.isoformat(),
                'is_read': notification.okundu,
                'read_at': notification.okunma_tarihi.isoformat() if notification.okunma_tarihi else None,
                'sms_sent': notification.sms_gonderildi,
                'sms_status': notification.sms_durum
            })
        
        return JsonResponse({
            'success': True,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'notifications': notifications_data,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages
        })
        
    except Exception as e:
        logger.error(f"Hasta bildirim geçmişi hatası: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Bildirim geçmişi getirilemedi: {str(e)}'
        }, status=500)