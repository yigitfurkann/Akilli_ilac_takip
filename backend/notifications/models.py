#notifications/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Bildirim(models.Model):
    """
    Bildirim modeli - SQLite için optimize edilmiş
    """
    
    GONDEREN_TIP_CHOICES = [
        ('doktor', 'Doktor'),
        ('bakici', 'Bakıcı'),
        ('sistem', 'Sistem'),
        ('admin', 'Admin'),
    ]
    
    ALICI_TIP_CHOICES = [
        ('hasta', 'Hasta'),
        ('doktor', 'Doktor'),
        ('bakici', 'Bakıcı'),
    ]
    
    BILDIRIM_TIP_CHOICES = [
        ('ilac_hatirlatma', 'İlaç Hatırlatması'),
        ('randevu_onay', 'Randevu Onayı'),
        ('randevu_red', 'Randevu Reddi'),
        ('randevu_hatirlatma', 'Randevu Hatırlatması'),
        ('randevu_talebi', 'Randevu Talebi'),
        ('bakici_atama', 'Bakıcı Ataması'),
        ('ilac_eklendi', 'İlaç Eklendi'),
        ('genel', 'Genel Bildirim'),
        ('acil', 'Acil Durum'),
        ('bilgi_guncelleme', 'Bilgi Güncelleme'),
    ]
    
    ONCELIK_CHOICES = [
        ('dusuk', 'Düşük'),
        ('normal', 'Normal'),
        ('yuksek', 'Yüksek'),
        ('acil', 'Acil'),
    ]
    
    # Gönderen Bilgileri
    gonderen = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Gönderen",
        related_name='gonderdigi_bildirimler'
    )
    
    gonderen_tip = models.CharField(
        max_length=20,
        choices=GONDEREN_TIP_CHOICES,
        verbose_name="Gönderen Tipi"
    )
    
    # Alıcı Bilgileri
    alici = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Alıcı",
        related_name='aldigi_bildirimler'
    )
    
    alici_tip = models.CharField(
        max_length=20,
        choices=ALICI_TIP_CHOICES,
        default='hasta',
        verbose_name="Alıcı Tipi"
    )
    
    # Bildirim İçeriği
    bildirim_tipi = models.CharField(
        max_length=50,
        choices=BILDIRIM_TIP_CHOICES,
        verbose_name="Bildirim Tipi"
    )
    
    oncelik = models.CharField(
        max_length=20,
        choices=ONCELIK_CHOICES,
        default='normal',
        verbose_name="Öncelik"
    )
    
    baslik = models.CharField(
        max_length=200,
        verbose_name="Başlık"
    )
    
    mesaj = models.TextField(
        verbose_name="Mesaj"
    )
    
    # Tarih Bilgileri
    gonderim_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Gönderim Tarihi"
    )
    
    okundu = models.BooleanField(
        default=False,
        verbose_name="Okundu Mu"
    )
    
    okunma_tarihi = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Okunma Tarihi"
    )
    
    # SMS Bilgileri
    sms_gonderildi = models.BooleanField(
        default=False,
        verbose_name="SMS Gönderildi Mi"
    )
    
    sms_gonderim_tarihi = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="SMS Gönderim Tarihi"
    )
    
    # Email Bilgileri
    email_gonderildi = models.BooleanField(
        default=False,
        verbose_name="Email Gönderildi Mi"
    )
    
    email_gonderim_tarihi = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Email Gönderim Tarihi"
    )
    
    # Sistem Bilgileri
    aktif = models.BooleanField(
        default=True,
        verbose_name="Aktif Mi"
    )
    
    # İlişkili Kayıtlar (Opsiyonel Foreign Key'ler)
    randevu = models.ForeignKey(
    'appointments.Appointment',  # 'appointments.Randevu' DEĞİL
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name="İlgili Randevu",
    related_name='bildirimleri'
    ) 
    
    ilac = models.ForeignKey(
    'medications.Ilac',  # Bu doğru
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name="İlgili İlaç",
    related_name='bildirimleri'
    )
    
    # SMS durum alanları - SADECE YOKSA EKLEYIN
    sms_durum = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Beklemede'),
            ('sent', 'Gönderildi'),
            ('delivered', 'Teslim Edildi'),
            ('failed', 'Başarısız'),
        ],
        default='pending',
        verbose_name="SMS Durumu",
        null=True,
        blank=True
    )
    
    sms_hata_mesaji = models.TextField(
        null=True,
        blank=True,
        verbose_name="SMS Hata Mesajı"
    )

# Mevcut @classmethod metodlarınızın SONUNA şu metodları ekleyin:

    @classmethod
    def create_doctor_message(cls, doktor_user, hasta_user, baslik, mesaj, oncelik='normal'):
        """
        Doktor mesajı bildirimi oluştur ve SMS gönder
        """
        # Bildirim oluştur
        bildirim = cls.objects.create(
            gonderen=doktor_user,
            gonderen_tip='doktor',
            alici=hasta_user,
            alici_tip='hasta',
            bildirim_tipi='genel',
            oncelik=oncelik,
            baslik=baslik,
            mesaj=mesaj
        )
        
        # SMS gönder
        try:
            bildirim.send_sms_notification()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"SMS gönderim hatası: {e}")
        
        return bildirim
    
    def send_sms_notification(self):
        """
        Bu bildirim için SMS gönder
        """
        try:
            # SMS service import et
            from sms_service.services import sms_service
            
            # Hasta telefon numarasını al
            patient_phone = None
            if hasattr(self.alici, 'patient_profile'):
                patient_phone = self.alici.patient_profile.telefon_no
            elif hasattr(self.alici, 'phone'):
                patient_phone = self.alici.phone
            
            if not patient_phone:
                return False
            
            # SMS mesajını oluştur
            if self.gonderen:
                sms_message = f"Dr. {self.gonderen.get_full_name()}: {self.mesaj}"
            else:
                sms_message = self.mesaj
            
            # SMS gönder
            result = sms_service.send_sms(
                phone_number=patient_phone,
                message=sms_message,
                user=self.alici,
                message_type='DoktorMesaj'
            )
            
            if result['success']:
                self.mark_sms_sent()
                return True
            else:
                # SMS hatası için alanlar güncelle
                self.sms_durum = 'failed'
                self.sms_hata_mesaji = result.get('error', '')
                self.save()
                return False
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"SMS bildirim hatası: {e}")
            return False
    
    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ['-gonderim_tarihi']
        indexes = [
            models.Index(fields=['alici', 'okundu']),
            models.Index(fields=['bildirim_tipi']),
            models.Index(fields=['oncelik']),
            models.Index(fields=['gonderim_tarihi']),
        ]
        
    def __str__(self):
        return f"{self.baslik} - {self.alici.username}"
    
    @property
    def is_urgent(self):
        """Acil bildirim mi"""
        return self.oncelik == 'acil'
    
    @property
    def is_overdue(self):
        """Gecikmiş bildirim mi (24 saatten eski ve okunmamış)"""
        if self.okundu:
            return False
        from datetime import timedelta
        return timezone.now() - self.gonderim_tarihi > timedelta(days=1)
    
    def mark_as_read(self):
        """Bildirimi okundu olarak işaretle"""
        if not self.okundu:
            self.okundu = True
            self.okunma_tarihi = timezone.now()
            self.save(update_fields=['okundu', 'okunma_tarihi'])
    
    def mark_sms_sent(self):
        """SMS gönderildi olarak işaretle"""
        self.sms_gonderildi = True
        self.sms_gonderim_tarihi = timezone.now()
        self.save(update_fields=['sms_gonderildi', 'sms_gonderim_tarihi'])
    
    def mark_email_sent(self):
        """Email gönderildi olarak işaretle"""
        self.email_gonderildi = True
        self.email_gonderim_tarihi = timezone.now()
        self.save(update_fields=['email_gonderildi', 'email_gonderim_tarihi'])
    
    @classmethod
    def create_medication_reminder(cls, hasta_user, ilac, message):
        """İlaç hatırlatması bildirimi oluştur"""
        return cls.objects.create(
            gonderen=None,
            gonderen_tip='sistem',
            alici=hasta_user,
            alici_tip='hasta',
            bildirim_tipi='ilac_hatirlatma',
            oncelik='yuksek',
            baslik='İlaç Hatırlatması',
            mesaj=message,
            ilac=ilac
        )
    
    @classmethod
    def create_appointment_request(cls, hasta_user, doktor_user, randevu, message):
        """Randevu talebi bildirimi oluştur"""
        return cls.objects.create(
            gonderen=hasta_user,
            gonderen_tip='hasta',
            alici=doktor_user,
            alici_tip='doktor',
            bildirim_tipi='randevu_talebi',
            oncelik='normal',
            baslik='Yeni Randevu Talebi',
            mesaj=message,
            randevu=randevu
        )
    
    @classmethod
    def create_appointment_approval(cls, doktor_user, hasta_user, randevu, message):
        """Randevu onay bildirimi oluştur"""
        return cls.objects.create(
            gonderen=doktor_user,
            gonderen_tip='doktor',
            alici=hasta_user,
            alici_tip='hasta',
            bildirim_tipi='randevu_onay',
            oncelik='normal',
            baslik='Randevunuz Onaylandı',
            mesaj=message,
            randevu=randevu
        )


class SistemAyarlari(models.Model):
    """
    Sistem ayarları modeli - SQLite için optimize edilmiş
    """
    
    VERI_TIPI_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('date', 'Date'),
    ]
    
    # Ayar Bilgileri
    kategori = models.CharField(
        max_length=50,
        default='genel',
        verbose_name="Kategori"
    )
    
    ayar_adi = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Ayar Adı"
    )
    
    ayar_degeri = models.TextField(
        blank=True,
        null=True,
        verbose_name="Ayar Değeri"
    )
    
    veri_tipi = models.CharField(
        max_length=20,
        choices=VERI_TIPI_CHOICES,
        default='string',
        verbose_name="Veri Tipi"
    )
    
    aciklama = models.TextField(
        blank=True,
        null=True,
        verbose_name="Açıklama"
    )
    
    herkese_acik = models.BooleanField(
        default=False,
        verbose_name="Herkese Açık Mı"
    )
    
    # Tarih Bilgileri
    guncelleme_tarihi = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi"
    )
    
    guncelleyen = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Güncelleyen"
    )

    class Meta:
        verbose_name = "Sistem Ayarı"
        verbose_name_plural = "Sistem Ayarları"
        ordering = ['kategori', 'ayar_adi']
        
    def __str__(self):
        return f"{self.kategori} - {self.ayar_adi}"
    
    def get_value(self):
        """Ayar değerini doğru veri tipinde döndür"""
        if not self.ayar_degeri:
            return None
            
        if self.veri_tipi == 'integer':
            try:
                return int(self.ayar_degeri)
            except ValueError:
                return 0
        elif self.veri_tipi == 'boolean':
            return self.ayar_degeri.lower() in ['true', '1', 'yes', 'on']
        elif self.veri_tipi == 'json':
            import json
            try:
                return json.loads(self.ayar_degeri)
            except json.JSONDecodeError:
                return {}
        elif self.veri_tipi == 'date':
            from datetime import datetime
            try:
                return datetime.fromisoformat(self.ayar_degeri)
            except ValueError:
                return None
        else:  # string
            return self.ayar_degeri
    
    @classmethod
    def get_setting(cls, ayar_adi, default=None):
        """Ayar değerini getir"""
        try:
            setting = cls.objects.get(ayar_adi=ayar_adi)
            return setting.get_value()
        except cls.DoesNotExist:
            return default