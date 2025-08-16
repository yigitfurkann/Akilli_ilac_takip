# doctors/urls.py - Düzeltilmiş hali
from django.urls import path
from . import views

# SMS service views'larını import edin
from sms_service import views as sms_views

urlpatterns = [
    # Hasta listesi 
    path('patients/', views.DoctorPatientsView.as_view(), name='doctor_patients'),
    
    # Randevu
    path('appointments/', views.DoctorAppointmentsView.as_view(), name='doctor_appointments'),
    path('appointments/<int:appointment_id>/', views.DoctorAppointmentsView.as_view(), name='doctor_appointment_detail'),
    
    # İlaç yönetimi
    path('medications/', views.DoctorMedicationsView.as_view(), name='doctor_medications'),
    
    # Bildirim sistemi - MEVCUT
    path('notifications/', views.DoctorNotificationsView.as_view(), name='doctor_notifications'),
    
    # ==================== YENİ: BAKICI YÖNETİMİ ====================
    
    # Bakıcı listesi
    path('caregivers/', views.DoctorCaregiversView.as_view(), name='doctor-caregivers'),
    
    # Bakıcı atamaları
    path('caregiver-assignments/', views.DoctorCaregiverAssignmentsView.as_view(), name='doctor-caregiver-assignments'),
    path('caregiver-assignments/<int:assignment_id>/', views.DoctorCaregiverAssignmentsView.as_view(), name='doctor-caregiver-assignment-detail'),
    
    # Bakıcı istatistikleri
    path('caregiver-stats/', views.DoctorCaregiverStatsView.as_view(), name='doctor-caregiver-stats'),
    
    # ==================== YENİ: SMS VE ALARM SİSTEMİ ====================
    
    # SMS Alarm yönetimi
    path('sms/alarms/create/', sms_views.create_alarm, name='doctor-sms-create-alarm'),
    path('sms/alarms/list/', sms_views.get_doctor_alarms, name='doctor-sms-alarms-list'),
    path('sms/alarms/<int:alarm_id>/toggle/', sms_views.toggle_alarm_status, name='doctor-sms-toggle-alarm'),
    
    # SMS Gönderimi
    path('sms/send/', sms_views.send_immediate_notification, name='doctor-sms-send'),
    path('sms/send/bulk/', sms_views.send_bulk_notification, name='doctor-sms-send-bulk'),
    
    # SMS Logları ve İstatistikler
    path('sms/logs/', sms_views.get_sms_logs, name='doctor-sms-logs'),
    path('sms/statistics/', sms_views.get_alarm_statistics, name='doctor-sms-statistics'),
    
    # SMS Şablonları
    path('sms/templates/', sms_views.get_sms_templates, name='doctor-sms-templates'),
    path('sms/templates/create/', sms_views.create_sms_template, name='doctor-sms-create-template'),
    
    # SMS Callback (Huawei Cloud için)
    path('sms/callback/', sms_views.sms_callback, name='doctor-sms-callback'),
    
    # ==================== İLAÇ ALARM ENTEGRASYONU ====================
    
    # İlaç için otomatik alarm kurma
    path('medications/<int:medication_id>/create-alarm/', sms_views.create_medication_alarm, name='doctor-medication-alarm'),
    
    # Randevu için otomatik alarm kurma  
    path('appointments/<int:appointment_id>/create-alarm/', sms_views.create_appointment_alarm, name='doctor-appointment-alarm'),
    
    # Hasta bazlı alarm yönetimi
    path('patients/<int:patient_id>/alarms/', sms_views.get_patient_alarms, name='doctor-patient-alarms'),
    path('patients/<int:patient_id>/send-sms/', sms_views.send_patient_sms, name='doctor-patient-sms'),
    
]