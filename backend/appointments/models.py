# appointments/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from patients.models import Patient
from doctors.models import Doctor
from accounts.models import User

class Appointment(models.Model):
    """
    Randevu modeli - MSSQL Randevular tablosuna karşılık gelir
    """
    
    STATUS_CHOICES = [
        ('Beklemede', 'Beklemede'),
        ('Onaylandi', 'Onaylandı'),
        ('Reddedildi', 'Reddedildi'),
        ('Tamamlandi', 'Tamamlandı'),
        ('Iptal', 'İptal'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('Muayene', 'Muayene'),
        ('Kontrol', 'Kontrol'),
        ('Konsultasyon', 'Konsültasyon'),
    ]
    
    # Primary Key
    randevu_id = models.AutoField(
        primary_key=True,
        db_column='RandevuID',
        verbose_name="Randevu ID"
    )
    
    # Foreign Keys
    hasta = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        db_column='HastaID',
        verbose_name="Hasta",
        related_name='randevular'
    )
    
    doktor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        db_column='DoktorID',
        verbose_name="Doktor",
        related_name='randevular'
    )
    
    # Randevu Bilgileri
    randevu_tarihi = models.DateTimeField(
        db_column='RandevuTarihi',
        verbose_name="Randevu Tarihi"
    )
    
    randevu_suresi = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(240)],
        db_column='RandevuSuresi',
        verbose_name="Randevu Süresi (Dakika)"
    )
    
    durum = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Beklemede',
        db_column='Durum',
        verbose_name="Durum"
    )
    
    randevu_tipi = models.CharField(
        max_length=50,
        choices=APPOINTMENT_TYPE_CHOICES,
        default='Muayene',
        db_column='RandevuTipi',
        verbose_name="Randevu Tipi"
    )
    
    # Notlar
    hasta_notlari = models.TextField(
        max_length=1000,
        null=True,
        blank=True,
        db_column='HastaNotlari',
        verbose_name="Hasta Notları"
    )
    
    doktor_notlari = models.TextField(
        max_length=1000,
        null=True,
        blank=True,
        db_column='DoktorNotlari',
        verbose_name="Doktor Notları"
    )
    
    # Online randevu mu?
    online_randevu_mu = models.BooleanField(
        default=False,
        db_column='OnlineRandevuMu',
        verbose_name="Online Randevu Mu"
    )
    
    # Sistem Bilgileri
    olusturulma_tarihi = models.DateTimeField(
        default=timezone.now,
        db_column='OlusturulmaTarihi',
        verbose_name="Oluşturulma Tarihi"
    )
    
    guncelleme_tarihi = models.DateTimeField(
        auto_now=True,
        db_column='GuncellenmeTarihi',
        verbose_name="Güncellenme Tarihi"
    )
    
    onaylayan_kullanici = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='OnaylayanKullanici',
        verbose_name="Onaylayan Kullanıcı",
        related_name='onayladigi_randevular'
    )

    class Meta:
        db_table = 'Randevular'
        verbose_name = "Randevu"
        verbose_name_plural = "Randevular"
        ordering = ['-randevu_tarihi']
        
    def __str__(self):
        return f"{self.hasta.full_name} - {self.doktor.full_name} ({self.randevu_tarihi.strftime('%d.%m.%Y %H:%M')})"
    
    @property
    def randevu_bitis_zamani(self):
        """Randevu bitiş zamanını hesaplar"""
        from datetime import timedelta
        return self.randevu_tarihi + timedelta(minutes=self.randevu_suresi)
    
    @property
    def is_past(self):
        """Randevu geçmiş mi kontrol eder"""
        return self.randevu_tarihi < timezone.now()
    
    @property
    def is_today(self):
        """Randevu bugün mü kontrol eder"""
        from datetime import date
        return self.randevu_tarihi.date() == date.today()
    
    @property
    def can_be_cancelled(self):
        """Randevu iptal edilebilir mi kontrol eder"""
        if self.durum in ['Tamamlandi', 'Iptal', 'Reddedildi']:
            return False
        # Randevu saatinden en az 2 saat önce iptal edilebilir
        from datetime import timedelta
        return timezone.now() + timedelta(hours=2) < self.randevu_tarihi
    
    def clean(self):
        """Model validasyonu"""
        # Randevu tarihi gelecekte olmalı
        if self.randevu_tarihi and self.randevu_tarihi < timezone.now():
            raise ValidationError("Randevu tarihi gelecekte olmalıdır.")
        
        # Aynı doktor aynı saatte başka randevu var mı kontrol et
        if self.randevu_tarihi:
            conflicting_appointments = Appointment.objects.filter(
                doktor=self.doktor,
                randevu_tarihi__range=[
                    self.randevu_tarihi,
                    self.randevu_bitis_zamani
                ],
                durum__in=['Beklemede', 'Onaylandi']
            ).exclude(randevu_id=self.randevu_id)
            
            if conflicting_appointments.exists():
                raise ValidationError("Bu saatte doktorun başka bir randevusu bulunmaktadır.")
    
    def approve(self, approver_user):
        """Randevuyu onayla"""
        if self.durum == 'Beklemede':
            self.durum = 'Onaylandi'
            self.onaylayan_kullanici = approver_user
            self.save()
            return True
        return False
    
    def reject(self, approver_user):
        """Randevuyu reddet"""
        if self.durum == 'Beklemede':
            self.durum = 'Reddedildi'
            self.onaylayan_kullanici = approver_user
            self.save()
            return True
        return False
    
    def cancel(self):
        """Randevuyu iptal et"""
        if self.can_be_cancelled:
            self.durum = 'Iptal'
            self.save()
            return True
        return False
    
    def complete(self):
        """Randevuyu tamamla"""
        if self.durum == 'Onaylandi' and self.is_past:
            self.durum = 'Tamamlandi'
            self.save()
            return True
        return False