from django.urls import path
from . import views
from . import patient_views  # Hasta uç noktalarını import et

app_name = 'sms_service'

urlpatterns = [
    # MEVCUT URL'LER - AYNEN KALIYOR
    path('notifications/', views.doctor_notifications_page, name='doctor_notifications'),
    
    # Alarm Endpoints - MEVCUT + YENİ EKLENENLER
    path('alarms/create/', views.create_alarm, name='create_alarm'),
    path('alarms/list/', views.get_doctor_alarms, name='get_doctor_alarms'),
    path('alarms/<int:alarm_id>/toggle/', views.toggle_alarm_status, name='toggle_alarm_status'),
    path('alarms/<int:alarm_id>/delete/', views.delete_alarm, name='delete_alarm'),
    
    # SMS Endpoints - MEVCUT + YENİ EKLENENLER
    path('sms/send/', views.send_immediate_notification, name='send_immediate_notification'),
    path('sms/logs/', views.get_sms_logs, name='get_sms_logs'),
    path('sms/callback/', views.sms_callback, name='sms_callback'),
    path('sms/retry/<int:sms_log_id>/', views.retry_sms, name='retry_sms'),
    
    # İstatistikler - MEVCUT + YENİ EKLENENLER
    path('statistics/', views.get_alarm_statistics, name='get_alarm_statistics'),
    path('reports/daily/', views.get_daily_report, name='get_daily_report'),
    path('reports/monthly/', views.get_monthly_report, name='get_monthly_report'),
    
    # Şablonlar - MEVCUT + YENİ EKLENENLER
    path('templates/', views.get_sms_templates, name='get_sms_templates'),
    path('templates/create/', views.create_sms_template, name='create_sms_template'),
    path('templates/<int:template_id>/update/', views.update_sms_template, name='update_sms_template'),
    path('templates/<int:template_id>/delete/', views.delete_sms_template, name='delete_sms_template'),
    
    # YENİ EKLENEN DOKTOR MESAJ SİSTEMİ - Opsiyonel (eğer doctor_views.py dosyanız varsa)
    # path('doctors/patients/', doctor_views.get_doctor_patients, name='get_doctor_patients'),
    # path('doctors/messages/send/', doctor_views.send_patient_message, name='send_patient_message'),
    # path('doctors/messages/bulk/', doctor_views.send_bulk_patient_message, name='send_bulk_patient_message'),
    
    # YENİ SİSTEM FONKSİYONLARI
    path('settings/', views.get_system_settings, name='get_system_settings'),
    path('settings/update/', views.update_system_settings, name='update_system_settings'),
    path('health/', views.health_check, name='health_check'),

    # ===== HASTA API UÇ NOKTALARI (patient_views.py) =====
    path('patients/alarms/', patient_views.get_patient_alarms, name='get_patient_alarms'),
    path('patients/alarms/history/', patient_views.get_patient_alarm_history, name='get_patient_alarm_history'),
    path('patients/alarms/upcoming/', patient_views.get_patient_upcoming_alarms, name='get_patient_upcoming_alarms'),
    path('patients/settings/', patient_views.get_patient_notification_settings, name='get_patient_notification_settings'),
    path('patients/settings/update/', patient_views.update_patient_notification_settings, name='update_patient_notification_settings'),
    
    
]
