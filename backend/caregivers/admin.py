# caregivers/admin.py

from django.contrib import admin
from .models import Caregiver, CaregiverPatientAssignment, CaregiverNote

@admin.register(Caregiver)
class CaregiverAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'telefon_no', 'email', 'egitim_durumu', 
        'deneyim', 'assigned_patients_count', 'ortalama_puan', 
        'aktif', 'kayit_tarihi'
    ]
    list_filter = [
        'aktif', 'egitim_durumu', 'deneyim', 'kayit_tarihi'
    ]
    search_fields = [
        'ad', 'soyad', 'telefon_no', 'email', 'uzmanlik_alanlari'
    ]
    readonly_fields = [
        'kayit_tarihi', 'son_giris', 'toplam_puan', 
        'degerlendirme_sayisi', 'assigned_patients_count', 'ortalama_puan'
    ]
    
    fieldsets = (
        ('Kişisel Bilgiler', {
            'fields': ('user', 'ad', 'soyad', 'telefon_no', 'email', 'dogum_tarihi', 'adres')
        }),
        ('Mesleki Bilgiler', {
            'fields': ('egitim_durumu', 'deneyim', 'sertifikalar', 'uzmanlik_alanlari')
        }),
        ('Çalışma Bilgileri', {
            'fields': ('calisma_saatleri', 'musait_gunler', 'maas')
        }),
        ('Değerlendirme', {
            'fields': ('toplam_puan', 'degerlendirme_sayisi', 'ortalama_puan'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('aktif', 'kayit_tarihi', 'son_giris'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CaregiverPatientAssignment)
class CaregiverPatientAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'caregiver', 'patient', 'assigned_date', 'end_date', 
        'is_active', 'contact_frequency', 'last_contact_date'
    ]
    list_filter = [
        'is_active', 'contact_frequency', 'assigned_date'
    ]
    search_fields = [
        'caregiver__ad', 'caregiver__soyad', 
        'patient__ad', 'patient__soyad'
    ]
    date_hierarchy = 'assigned_date'
    
    fieldsets = (
        ('Atama Bilgileri', {
            'fields': ('caregiver', 'patient', 'assigned_date', 'end_date', 'is_active')
        }),
        ('İletişim Takibi', {
            'fields': ('contact_frequency', 'last_contact_date')
        }),
        ('Notlar', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

@admin.register(CaregiverNote)
class CaregiverNoteAdmin(admin.ModelAdmin):
    list_display = [
        'caregiver', 'patient', 'note_type', 'is_urgent', 'created_date'
    ]
    list_filter = [
        'note_type', 'is_urgent', 'created_date'
    ]
    search_fields = [
        'caregiver__ad', 'caregiver__soyad',
        'patient__ad', 'patient__soyad', 'note'
    ]
    date_hierarchy = 'created_date'
    readonly_fields = ['created_date']
    
    fieldsets = (
        ('Not Bilgileri', {
            'fields': ('caregiver', 'patient', 'note_type', 'is_urgent')
        }),
        ('Not İçeriği', {
            'fields': ('note',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_date',),
            'classes': ('collapse',)
        }),
    )   