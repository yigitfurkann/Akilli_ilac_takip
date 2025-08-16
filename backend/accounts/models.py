# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    """
    Custom User modeli - MSSQL Users tablosuna karşılık gelir
    """
    USER_TYPE_CHOICES = [
        ('Hasta', 'Hasta'),
        ('Doktor', 'Doktor'),
        ('Bakici', 'Bakıcı'),
    ]
    
    # AbstractUser'dan gelen username field'ını kullanacağız
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES,
        verbose_name="Kullanıcı Tipi"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif Mi"
    )
    
    last_login_custom = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Son Giriş"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Oluşturulma Tarihi"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi"
    )

    class Meta:
        db_table = 'Users'
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"
        
    def __str__(self):
        return f"{self.username} ({self.user_type})"
    
    def save(self, *args, **kwargs):
        # Password hash'i zaten Django tarafından yapılıyor
        super().save(*args, **kwargs)   