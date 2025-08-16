# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Doktor modelini doğru yerden import et
# from .models import Doctor  # ❌ YANLIŞ - Doctor accounts.models'da değil
# from doctors.models import Doctor  # ✅ DOĞRU - ama daha iyi çözüm aşağıda

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom User Admin
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    # Kullanıcı düzenleme formunu genişlet
    fieldsets = UserAdmin.fieldsets + (
        ('Ek Bilgiler', {
            'fields': ('user_type', 'last_login_custom', 'created_at', 'updated_at'),
        }),
    )
    
    # Yeni kullanıcı oluşturma formunu genişlet
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Ek Bilgiler', {
            'fields': ('user_type', 'email'),
        }),
    )
    
    # Salt okunur alanlar
    readonly_fields = ('created_at', 'updated_at', 'last_login_custom')

    def get_queryset(self, request):
        """Performans için related objelerini de getir"""
        return super().get_queryset(request).select_related()