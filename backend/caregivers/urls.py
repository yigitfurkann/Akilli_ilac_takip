# caregivers/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard istatistikleri
    path('dashboard/', views.CaregiverDashboardView.as_view(), name='caregiver-dashboard'),
    
    # Hasta listesi (GELİŞTİRİLMİŞ - doktor notları ile)
    path('patients/', views.CaregiverPatientsView.as_view(), name='caregiver-patients'),
    
    # Hasta detayları (GELİŞTİRİLMİŞ - doktor notları ile)
    path('patients/<int:patient_id>/', views.PatientDetailView.as_view(), name='patient-detail'),
    
    # YENİ: Sadece doktor notları endpoint'i
    path('patients/<int:patient_id>/doctor-notes/', views.PatientDoctorNotesView.as_view(), name='patient-doctor-notes'),
    
    # Hasta ilaçları
    path('patients/<int:patient_id>/medications/', views.PatientMedicationsView.as_view(), name='patient-medications'),
    
    # Hasta randevuları
    path('patients/<int:patient_id>/appointments/', views.PatientAppointmentsView.as_view(), name='patient-appointments'),
    
    # Bakıcı notları
    path('patients/<int:patient_id>/notes/', views.PatientNotesView.as_view(), name='patient-notes'),
    
    # Acil durum bildirimi
    path('patients/<int:patient_id>/emergency-alert/', views.EmergencyAlertView.as_view(), name='emergency-alert'),
    
    # Profil yönetimi
    path('profile/', views.CaregiverProfileView.as_view(), name='caregiver-profile'),
    
    # Bildirimler
    path('notifications/', views.CaregiverNotificationsView.as_view(), name='caregiver-notifications'),
]