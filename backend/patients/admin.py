# patients/admin.py

from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """
    Hasta Admin
    """
    list_display = ('full_name', 'telefon_no', 'email', 'cinsiyet', 'age', 'kayit_tarihi')
    list_filter = ('cinsiyet', 'kayit_tarihi')
    search_fields = ('ad', 'soyad', 'telefon_no', 'email')
    ordering = ('-kayit_tarihi',)
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('user', 'ad', 'soyad', 'dogum_tarihi', 'cinsiyet')
        }),
        ('İletişim Bilgileri', {
            'fields': ('telefon_no', 'email', 'adres')
        }),
        ('Acil Durum Bilgileri', {
            'fields': ('acil_durum_kisi', 'acil_durum_telefon'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('kayit_tarihi',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('kayit_tarihi',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')