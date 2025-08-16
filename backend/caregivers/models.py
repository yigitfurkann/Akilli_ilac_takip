# caregivers/models.py

from django.db import models
from django.conf import settings  # User yerine settings kullan
from django.utils import timezone
from patients.models import Patient

class Caregiver(models.Model):
    """
    Bakıcı modeli
    """
    
    EDUCATION_CHOICES = [
        ('Lise', 'Lise'),
        ('OnLisans', 'Ön Lisans'),
        ('Lisans', 'Lisans'),
        ('YuksekLisans', 'Yüksek Lisans'),
    ]
    
    EXPERIENCE_CHOICES = [
        ('0-1', '0-1 Yıl'),
        ('1-3', '1-3 Yıl'),
        ('3-5', '3-5 Yıl'),  
        ('5-10', '5-10 Yıl'),
        ('10+', '10+ Yıl'),
    ]
    
    # Foreign Key to User - settings.AUTH_USER_MODEL kullan
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # User yerine settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        verbose_name="Kullanıcı",
        related_name='bakici_profile'
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
    
    telefon_no = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Telefon Numarası"
    )
    
    email = models.EmailField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="E-posta"
    )
    
    dogum_tarihi = models.DateField(
        null=True,
        blank=True,
        verbose_name="Doğum Tarihi"
    )
    
    adres = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Adres"
    )
    
    # Mesleki Bilgiler
    egitim_durumu = models.CharField(
        max_length=20,
        choices=EDUCATION_CHOICES,
        null=True,
        blank=True,
        verbose_name="Eğitim Durumu"
    )
    
    deneyim = models.CharField(
        max_length=10,
        choices=EXPERIENCE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Deneyim"
    )
    
    sertifikalar = models.TextField(
        null=True,
        blank=True,
        verbose_name="Sertifikalar",
        help_text="Sahip olduğu sertifikaları belirtiniz"
    )
    
    uzmanlik_alanlari = models.TextField(
        null=True,
        blank=True,
        verbose_name="Uzmanlık Alanları",
        help_text="Yaşlı bakımı, engelli bakımı vb."
    )
    
    # Çalışma Bilgileri
    calisma_saatleri = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Çalışma Saatleri"
    )
    
    musait_gunler = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Müsait Günler"
    )
    
    maas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Maaş"
    )
    
    # Sistem Bilgileri
    aktif = models.BooleanField(
        default=True,
        verbose_name="Aktif"
    )
    
    kayit_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Kayıt Tarihi"
    )
    
    son_giris = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Son Giriş"
    )
    
    # Rating sistemi
    toplam_puan = models.FloatField(
        default=0.0,
        verbose_name="Toplam Puan"
    )
    
    degerlendirme_sayisi = models.IntegerField(
        default=0,
        verbose_name="Değerlendirme Sayısı"
    )

    class Meta:
        verbose_name = "Bakıcı"
        verbose_name_plural = "Bakıcılar"
        db_table = 'caregivers'
    
    def __str__(self):
        return f"{self.ad} {self.soyad}"
    
    @property
    def full_name(self):
        return f"{self.ad} {self.soyad}"
    
    @property
    def age(self):
        if self.dogum_tarihi:
            from datetime import date
            today = date.today()
            return today.year - self.dogum_tarihi.year - (
                (today.month, today.day) < (self.dogum_tarihi.month, self.dogum_tarihi.day)
            )
        return None
    
    @property
    def ortalama_puan(self):
        """Ortalama değerlendirme puanı"""
        if self.degerlendirme_sayisi > 0:
            return round(self.toplam_puan / self.degerlendirme_sayisi, 1)
        return 0.0
    
    @property
    def assigned_patients_count(self):
        """Atanmış hasta sayısı"""
        return self.caregiver_assignments.filter(is_active=True).count()


class CaregiverPatientAssignment(models.Model):
    """
    Bakıcı-Hasta eşleştirme modeli
    """
    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.CASCADE,
        related_name='caregiver_assignments',
        verbose_name="Bakıcı"
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='patient_assignments',
        verbose_name="Hasta"
    )
    
    assigned_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Atanma Tarihi"
    )
    
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bitiş Tarihi"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif"
    )
    
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Notlar"
    )
    
    # İletişim takibi
    last_contact_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Son İletişim Tarihi"
    )
    
    contact_frequency = models.CharField(
        max_length=20,
        default='daily',
        choices=[
            ('daily', 'Günlük'),
            ('weekly', 'Haftalık'),
            ('monthly', 'Aylık'),
        ],
        verbose_name="İletişim Sıklığı"
    )

    class Meta:
        verbose_name = "Bakıcı-Hasta Ataması"
        verbose_name_plural = "Bakıcı-Hasta Atamaları"
        db_table = 'caregiver_patient_assignments'
        unique_together = ['caregiver', 'patient']
    
    def __str__(self):
        return f"{self.caregiver.full_name} -> {self.patient.full_name}"
    
    @property
    def assignment_duration(self):
        """Atama süresi (gün)"""
        end_date = self.end_date or timezone.now()
        return (end_date.date() - self.assigned_date.date()).days


class CaregiverNote(models.Model):
    """
    Bakıcının hasta hakkında tuttuğu notlar
    """
    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.CASCADE,
        verbose_name="Bakıcı"
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        verbose_name="Hasta"
    )
    
    note = models.TextField(
        verbose_name="Not"
    )
    
    note_type = models.CharField(
        max_length=20,
        choices=[
            ('general', 'Genel'),
            ('medication', 'İlaç'),
            ('emergency', 'Acil Durum'),
            ('improvement', 'İyileşme'),
            ('concern', 'Endişe'),
        ],
        default='general',
        verbose_name="Not Tipi"
    )
    
    is_urgent = models.BooleanField(
        default=False,
        verbose_name="Acil"
    )
    
    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma Tarihi"
    )

    class Meta:
        verbose_name = "Bakıcı Notu"
        verbose_name_plural = "Bakıcı Notları"
        db_table = 'caregiver_notes'
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.caregiver.full_name} - {self.patient.full_name} ({self.created_date.strftime('%d.%m.%Y')})"