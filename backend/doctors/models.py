from django.db import models
from django.utils import timezone
import json
from accounts.models import User

class Doctor(models.Model):
    """
    Doktor modeli - SQLite için optimize edilmiş
    """
    
    # Primary Key - DoktorID (DOCxxx formatında)
    doktor_id = models.CharField(
        max_length=20,
        primary_key=True,
        verbose_name="Doktor ID"
    )
    
    # Foreign Key to User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name="Kullanıcı",
        related_name='doktor_profile'
    )
    
    # Kişisel Bilgiler
    ad = models.CharField(
        max_length=50,
        verbose_name="Ad"
    )
    
    soyad = models.CharField(
        max_length=50,
        verbose_name="Soyad"
    )
    
    uzmanlik = models.CharField(
        max_length=100,
        verbose_name="Uzmanlık"
    )
    
    diploma_no = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Diploma Numarası"
    )
    
    telefon_no = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="Telefon Numarası"
    )
    
    email = models.EmailField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="E-posta"
    )
    
    # Çalışma saatleri JSON formatında
    calisma_saatleri = models.TextField(
        null=True,
        blank=True,
        verbose_name="Çalışma Saatleri",
        help_text="JSON formatında: {\"pazartesi\": \"09:00-17:00\", ...}"
    )
    
    muayenehane_adresi = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Muayenehane Adresi"
    )
    
    # Sistem Bilgileri
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif Mi"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Oluşturulma Tarihi"
    )

    class Meta:
        verbose_name = "Doktor"
        verbose_name_plural = "Doktorlar"
        
    def __str__(self):
        return f"Dr. {self.ad} {self.soyad} ({self.uzmanlik})"
    
    @property
    def full_name(self):
        return f"Dr. {self.ad} {self.soyad}"
    
    def get_calisma_saatleri(self):
        """Çalışma saatlerini dictionary olarak döndürür"""
        if self.calisma_saatleri:
            try:
                return json.loads(self.calisma_saatleri)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_calisma_saatleri(self, saatler_dict):
        """Çalışma saatlerini JSON string olarak kaydeder"""
        self.calisma_saatleri = json.dumps(saatler_dict, ensure_ascii=False)
    
    def is_available_on_day(self, day_name):
        """Belirli bir günde çalışıyor mu kontrol eder"""
        saatler = self.get_calisma_saatleri()
        return day_name.lower() in saatler and saatler[day_name.lower()]
    
    def save(self, *args, **kwargs):
        # DoktorID otomatik oluşturma
        if not self.doktor_id:
            last_doctor = Doctor.objects.order_by('doktor_id').last()
            if last_doctor:
                last_id = int(last_doctor.doktor_id[3:])  # DOC kısmını çıkar
                new_id = last_id + 1
            else:
                new_id = 1
            self.doktor_id = f"DOC{new_id:03d}"  # DOC001 formatı
        super().save(*args, **kwargs)