# patients/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Profil işlemleri
    path('profile/', views.PatientProfileView.as_view(), name='patient_profile'),
    
    # Doktor listesi
    path('doctors/', views.PatientDoctorsView.as_view(), name='patient_doctors'),
    
    # Randevu işlemleri
    path('appointments/', views.PatientAppointmentsView.as_view(), name='patient_appointments'),
    path('appointments/<int:appointment_id>/', views.PatientAppointmentsView.as_view(), name='patient_appointment_cancel'),
    
    # İlaç işlemleri
    path('medications/', views.PatientMedicationsView.as_view(), name='patient_medications'),
    
    # Bildirim işlemleri
    path('notifications/', views.PatientNotificationsView.as_view(), name='patient_notifications'),
    path('notifications/<int:notification_id>/', views.PatientNotificationsView.as_view(), name='patient_notification_read'),
    
    path('notifications/statistics/', views.patient_notifications_statistics, name='patient_notifications_statistics'),
    path('notifications/mark_all_read/', views.patient_notifications_mark_all_read, name='patient_notifications_mark_all_read'),

    
]