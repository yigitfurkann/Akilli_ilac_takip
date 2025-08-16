# doctors/admin.py

from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """
    Doktor Admin
    """
    list_display = ('doktor_id', 'full_name', 'uzmanlik', 'telefon_no', 'is_active', 'created_at')
    list_filter = ('uzmanlik', 'is_active', 'created_at')
    search_fields = ('doktor_id', 'ad', 'soyad', 'uzmanlik', 'telefon_no', 'email')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('doktor_id', 'user', 'ad', 'soyad', 'uzmanlik')
        }),
        ('İletişim Bilgileri', {
            'fields': ('telefon_no', 'email', 'muayenehane_adresi')
        }),
        ('Profesyonel Bilgiler', {
            'fields': ('diploma_no', 'calisma_saatleri')
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')