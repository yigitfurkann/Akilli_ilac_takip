from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

class Ilac(models.Model):
    """
    İlaç modeli - SQLite için optimize edilmiş
    """
    
    YEMEK_ILISKISI_CHOICES = [
        ('yemekten_once', 'Yemekten Önce'),
        ('yemekten_sonra', 'Yemekten Sonra'),
        ('yemekle_birlikte', 'Yemekle Birlikte'),
        ('ac_karnina', 'Aç Karnına'),
        ('farketmez', 'Farketmez'),
    ]
    
    # Foreign Keys - Django standart User ve related modellerle
    hasta = models.ForeignKey(
    'patients.Patient',  # 'patients.Hasta' DEĞİL
    on_delete=models.CASCADE,
    verbose_name="Hasta",
    related_name='ilac_alim_gecmisi'
    )
    
    doktor = models.ForeignKey(
    'doctors.Doctor',  
    on_delete=models.CASCADE, 
    verbose_name="Doktor",
    related_name='recete_ettigi_ilaclar'
    )
    
    # İlaç Bilgileri
    ilac_adi = models.CharField(
        max_length=200,
        verbose_name="İlaç Adı"
    )
    
    etken_madde = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Etken Madde"
    )
    
    dozaj = models.CharField(
        max_length=50,
        verbose_name="Dozaj",
        help_text="Örn: 500mg, 1 tablet, 5ml"
    )
    
    kullanim_sikligi = models.CharField(
        max_length=100,
        verbose_name="Kullanım Sıklığı",
        help_text="Örn: Günde 3 kez, 12 saatte bir, 8 saatte bir"
    )
    
    yemek_iliskisi = models.CharField(
        max_length=20,
        choices=YEMEK_ILISKISI_CHOICES,
        blank=True,
        null=True,
        verbose_name="Yemek İlişkisi"
    )
    
    # Tarih Bilgileri
    baslangic_tarihi = models.DateField(
        verbose_name="Başlangıç Tarihi"
    )
    
    bitis_tarihi = models.DateField(
        blank=True,
        null=True,
        verbose_name="Bitiş Tarihi"
    )
    
    # Talimatlar ve Uyarılar
    kullanim_talimatlari = models.TextField(
        blank=True,
        null=True,
        verbose_name="Kullanım Talimatları"
    )
    
    yan_etkiler = models.TextField(
        blank=True,
        null=True,
        verbose_name="Yan Etkiler"
    )
    
    uyarilar = models.TextField(
        blank=True,
        null=True,
        verbose_name="Uyarılar"
    )
    
    # Sistem Bilgileri
    aktif = models.BooleanField(
        default=True,
        verbose_name="Aktif Mi"
    )
    
    olusturulma_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma Tarihi"
    )
    
    guncelleme_tarihi = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi"
    )

    class Meta:
        verbose_name = "İlaç"
        verbose_name_plural = "İlaçlar"
        ordering = ['-olusturulma_tarihi']
        
    def __str__(self):
        return f"{self.ilac_adi} - {self.hasta.full_name}"
    
    @property
    def is_current(self):
        """İlaç şu anda kullanılıyor mu"""
        from datetime import date
        today = date.today()
        if not self.aktif:
            return False
        if self.bitis_tarihi and self.bitis_tarihi < today:
            return False
        return self.baslangic_tarihi <= today
    
    @property
    def is_expired(self):
        """İlaç süresi dolmuş mu"""
        from datetime import date
        if self.bitis_tarihi:
            return self.bitis_tarihi < date.today()
        return False
    
    @property
    def days_remaining(self):
        """Kalan gün sayısı"""
        if self.bitis_tarihi:
            from datetime import date
            remaining = (self.bitis_tarihi - date.today()).days
            return max(0, remaining)
        return None
    
    def clean(self):
        """Model validasyonu"""
        if self.bitis_tarihi and self.bitis_tarihi < self.baslangic_tarihi:
            raise ValidationError("Bitiş tarihi başlangıç tarihinden önce olamaz.")
    
    def get_next_dose_times(self, count=3):
        """Sonraki ilaç alma zamanlarını hesaplar"""
        from datetime import datetime, timedelta
        import re
        
        # Kullanım sıklığından saat aralığını çıkar
        frequency_text = self.kullanim_sikligi.lower()
        
        if 'günde' in frequency_text:
            # "Günde 3 kez" gibi
            match = re.search(r'günde\s*(\d+)', frequency_text)
            if match:
                daily_count = int(match.group(1))
                interval_hours = 24 / daily_count
            else:
                interval_hours = 8  # Default
        elif 'saatte' in frequency_text:
            # "8 saatte bir" gibi
            match = re.search(r'(\d+)\s*saatte', frequency_text)
            if match:
                interval_hours = int(match.group(1))
            else:
                interval_hours = 8  # Default
        else:
            interval_hours = 8  # Default
        
        # Sonraki zamanları hesapla
        next_times = []
        current_time = datetime.now()
        
        for i in range(count):
            next_time = current_time + timedelta(hours=interval_hours * (i + 1))
            next_times.append(next_time)
        
        return next_times


class IlacAlimGecmisi(models.Model):
    """
    İlaç Alım Geçmişi modeli - SQLite için optimize edilmiş
    """
    
    ALIM_DURUM_CHOICES = [
        ('beklemede', 'Beklemede'),
        ('alindi', 'Alındı'),
        ('atlanmis', 'Atlanmış'),
        ('gecikme', 'Gecikme'),
    ]
    
    # Foreign Keys
    ilac = models.ForeignKey(
        Ilac,
        on_delete=models.CASCADE,
        verbose_name="İlaç",
        related_name='alim_gecmisi'
    )
    
    hasta = models.ForeignKey(
    'patients.Patient',  # 'patients.Hasta' DEĞİL
    on_delete=models.CASCADE,
    verbose_name="Hasta",
    related_name='ilaclar'
)
    
    # Alım Bilgileri
    planlanan_alim_tarihi = models.DateTimeField(
        verbose_name="Planlanan Alım Tarihi"
    )
    
    gercek_alim_tarihi = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Gerçek Alım Tarihi"
    )
    
    alim_durumu = models.CharField(
        max_length=20,
        choices=ALIM_DURUM_CHOICES,
        default='beklemede',
        verbose_name="Alım Durumu"
    )
    
    gecikme_suresi = models.PositiveIntegerField(
        default=0,
        verbose_name="Gecikme Süresi (Dakika)"
    )
    
    notlar = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notlar"
    )
    
    hatirlatma_gonderildi = models.BooleanField(
        default=False,
        verbose_name="Hatırlatma Gönderildi Mi"
    )
    
    # Sistem Bilgileri
    olusturulma_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma Tarihi"
    )

    class Meta:
        verbose_name = "İlaç Alım Geçmişi"
        verbose_name_plural = "İlaç Alım Geçmişleri"
        ordering = ['-planlanan_alim_tarihi']
        
    def __str__(self):
        return f"{self.ilac.ilac_adi} - {self.planlanan_alim_tarihi.strftime('%d.%m.%Y %H:%M')}"
    
    @property
    def is_overdue(self):
        """İlaç vakti geçmiş mi"""
        if self.alim_durumu != 'beklemede':
            return False
        return timezone.now() > self.planlanan_alim_tarihi
    
    @property
    def minutes_overdue(self):
        """Kaç dakika gecikmiş"""
        if not self.is_overdue:
            return 0
        delta = timezone.now() - self.planlanan_alim_tarihi
        return int(delta.total_seconds() / 60)
    
    def mark_taken(self, actual_time=None):
        """İlacı alındı olarak işaretle"""
        if actual_time is None:
            actual_time = timezone.now()
        
        self.gercek_alim_tarihi = actual_time
        
        # Gecikme süresini hesapla
        if actual_time > self.planlanan_alim_tarihi:
            delta = actual_time - self.planlanan_alim_tarihi
            self.gecikme_suresi = int(delta.total_seconds() / 60)
            self.alim_durumu = 'gecikme' if self.gecikme_suresi > 30 else 'alindi'
        else:
            self.gecikme_suresi = 0
            self.alim_durumu = 'alindi'
        
        self.save()
    
    def mark_skipped(self, note=None):
        """İlacı atlanmış olarak işaretle"""
        self.alim_durumu = 'atlanmis'
        if note:
            self.notlar = note
        self.save()
    
    def send_reminder(self):
        """Hatırlatma gönder"""
        # Bu metod notifications app'inde implement edilecek
        self.hatirlatma_gonderildi = True
        self.save()