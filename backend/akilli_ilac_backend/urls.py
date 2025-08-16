# akilli_ilac_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/', include('accounts.urls')),
    path('api/patients/', include('patients.urls')),
    path('api/doctors/', include('doctors.urls')),
    path('api/caregivers/', include('caregivers.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/medications/', include('medications.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/sms_service/', include('sms_service.urls')),  # SMS servisi URL'leri
]

# Media ve static files için development ayarları
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)