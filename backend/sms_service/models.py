# sms_service/models.py

from django.db import models
from django.utils import timezone
from accounts.models import User

class SMSLog(models.Model):
    """
    SMS gönderim logları için model
    """
    
    STATUS_CHOICES = [
        ('Pending', 'Beklemede'),
        ('Sent', 'Gönderildi'),
        ('Failed', 'Başarısız'),
        ('Delivered', 'Teslim Edildi'),
        ('Rejected', 'Reddedildi'),
    ]
    
    # Primary Key
    id = models.AutoField(primary_key=True)
    
    # SMS Bilgileri
    recipient_phone = models.CharField(
        max_length=15,
        verbose_name="Alıcı Telefon"
    )
    
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Alıcı Kullanıcı",
        related_name='sms_logs'
    )
    
    message = models.TextField(
        max_length=1000,
        verbose_name="Mesaj İçeriği"
    )
    
    message_type = models.CharField(
        max_length=50,
        default='General',
        verbose_name="Mesaj Tipi",
        help_text="IlacHatirlatma, RandevuOnay, etc."
    )
    
    # Huawei Cloud SMS Bilgileri
    template_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Template ID"
    )
    
    message_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Huawei Message ID"
    )
    
    # Durum Bilgileri
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name="Durum"
    )
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Hata Mesajı"
    )
    
    # Tarih Bilgileri
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Oluşturulma Tarihi"
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Gönderilme Tarihi"
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Teslim Edilme Tarihi"
    )
    
    # Tekrar Deneme Bilgileri
    retry_count = models.IntegerField(
        default=0,
        verbose_name="Tekrar Deneme Sayısı"
    )
    
    max_retries = models.IntegerField(
        default=3,
        verbose_name="Maksimum Tekrar Deneme"
    )
    
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sonraki Deneme Zamanı"
    )

    class Meta:
        verbose_name = "SMS Log"
        verbose_name_plural = "SMS Logları"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['recipient_phone']),
            models.Index(fields=['message_type']),
        ]
        
    def __str__(self):
        return f"SMS to {self.recipient_phone} - {self.status}"
    
    @property
    def can_retry(self):
        """Tekrar denenebilir mi"""
        return (
            self.status == 'Failed' and 
            self.retry_count < self.max_retries and
            (self.next_retry_at is None or timezone.now() >= self.next_retry_at)
        )
    
    def mark_sent(self, message_id=None):
        """SMS gönderildi olarak işaretle"""
        self.status = 'Sent'
        self.sent_at = timezone.now()
        if message_id:
            self.message_id = message_id
        self.save()
    
    def mark_failed(self, error_message=None):
        """SMS başarısız olarak işaretle"""
        self.status = 'Failed'
        if error_message:
            self.error_message = error_message
        
        # Tekrar deneme planla
        if self.retry_count < self.max_retries:
            from datetime import timedelta
            self.next_retry_at = timezone.now() + timedelta(minutes=5 * (self.retry_count + 1))
        
        self.save()
    
    def mark_delivered(self):
        """SMS teslim edildi olarak işaretle"""
        self.status = 'Delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def increment_retry(self):
        """Tekrar deneme sayısını artır"""
        self.retry_count += 1
        self.save()


class SMSTemplate(models.Model):
    """
    SMS şablonları için model
    """
    
    # Primary Key
    id = models.AutoField(primary_key=True)
    
    # Şablon Bilgileri
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Şablon Adı"
    )
    
    template_id = models.CharField(
        max_length=100,
        verbose_name="Huawei Template ID"
    )
    
    message_template = models.TextField(
        verbose_name="Mesaj Şablonu",
        help_text="Parametreler {0}, {1} şeklinde kullanılır"
    )
    
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Açıklama"
    )
    
    # Şablon Kategorisi
    category = models.CharField(
        max_length=50,
        default='General',
        verbose_name="Kategori"
    )
    
    # Durum
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif Mi"
    )
    
    # Tarih Bilgileri
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Oluşturulma Tarihi"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi"
    )

    class Meta:
        verbose_name = "SMS Şablonu"
        verbose_name_plural = "SMS Şablonları"
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def format_message(self, *args):
        """Şablonu parametrelerle formatla"""
        try:
            return self.message_template.format(*args)
        except (IndexError, KeyError) as e:
            return f"Şablon formatı hatası: {str(e)}"


class SystemSettings(models.Model):
    """
    Sistem ayarları modeli - MSSQL SistemAyarlari tablosuna karşılık gelir
    """
    
    DATA_TYPE_CHOICES = [
        ('String', 'String'),
        ('Integer', 'Integer'),
        ('Boolean', 'Boolean'),
        ('JSON', 'JSON'),
        ('Date', 'Date'),
    ]
    
    # Primary Key
    id = models.AutoField(primary_key=True, db_column='ID')
    
    # Ayar Bilgileri
    kategori = models.CharField(
        max_length=50,
        default='Genel',
        db_column='Kategori',
        verbose_name="Kategori"
    )
    
    ayar_adi = models.CharField(
        max_length=100,
        unique=True,
        db_column='AyarAdi',
        verbose_name="Ayar Adı"
    )
    
    ayar_degeri = models.TextField(
        null=True,
        blank=True,
        db_column='AyarDegeri',
        verbose_name="Ayar Değeri"
    )
    
    veri_tipi = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='String',
        db_column='VeriTipi',
        verbose_name="Veri Tipi"
    )
    
    aciklama = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        db_column='Aciklama',
        verbose_name="Açıklama"
    )
    
    is_public = models.BooleanField(
        default=False,
        db_column='IsPublic',
        verbose_name="Herkese Açık Mı"
    )
    
    # Tarih Bilgileri
    updated_at = models.DateTimeField(
        auto_now=True,
        db_column='UpdatedAt',
        verbose_name="Güncellenme Tarihi"
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='UpdatedBy',
        verbose_name="Güncelleyen"
    )

    class Meta:
        db_table = 'SistemAyarlari'
        verbose_name = "Sistem Ayarı"
        verbose_name_plural = "Sistem Ayarları"
        ordering = ['kategori', 'ayar_adi']
        
    def __str__(self):
        return f"{self.kategori} - {self.ayar_adi}"
    
    def get_value(self):
        """Ayar değerini doğru veri tipinde döndür"""
        if not self.ayar_degeri:
            return None
            
        if self.veri_tipi == 'Integer':
            try:
                return int(self.ayar_degeri)
            except ValueError:
                return 0
        elif self.veri_tipi == 'Boolean':
            return self.ayar_degeri.lower() in ['true', '1', 'yes', 'on']
        elif self.veri_tipi == 'JSON':
            import json
            try:
                return json.loads(self.ayar_degeri)
            except json.JSONDecodeError:
                return {}
        elif self.veri_tipi == 'Date':
            from datetime import datetime
            try:
                return datetime.fromisoformat(self.ayar_degeri)
            except ValueError:
                return None
        else:  # String
            return self.ayar_degeri
    
    @classmethod
    def get_setting(cls, ayar_adi, default=None):
        """Ayar değerini getir"""
        try:
            setting = cls.objects.get(ayar_adi=ayar_adi)
            return setting.get_value()
        except cls.DoesNotExist:
            return default


class SystemLog(models.Model):
    """
    Sistem logları modeli - MSSQL SistemLoglari tablosuna karşılık gelir
    """
    
    LOG_LEVEL_CHOICES = [
        ('DEBUG', 'DEBUG'),
        ('INFO', 'INFO'),
        ('WARNING', 'WARNING'),
        ('ERROR', 'ERROR'),
        ('CRITICAL', 'CRITICAL'),
    ]
    
    # Primary Key
    log_id = models.AutoField(
        primary_key=True,
        db_column='LogID',
        verbose_name="Log ID"
    )
    
    # Kullanıcı Bilgisi
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='UserID',
        verbose_name="Kullanıcı"
    )
    
    # Log Bilgileri
    log_level = models.CharField(
        max_length=20,
        choices=LOG_LEVEL_CHOICES,
        default='INFO',
        db_column='LogLevel',
        verbose_name="Log Seviyesi"
    )
    
    kategori = models.CharField(
        max_length=50,
        db_column='Kategori',
        verbose_name="Kategori"
    )
    
    mesaj = models.TextField(
        db_column='Mesaj',
        verbose_name="Mesaj"
    )
    
    ip_adresi = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column='IPAdresi',
        verbose_name="IP Adresi"
    )
    
    user_agent = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_column='UserAgent',
        verbose_name="User Agent"
    )
    
    ek_bilgiler = models.TextField(
        null=True,
        blank=True,
        db_column='EkBilgiler',
        verbose_name="Ek Bilgiler (JSON)"
    )
    
    # Tarih Bilgisi
    created_at = models.DateTimeField(
        default=timezone.now,
        db_column='CreatedAt',
        verbose_name="Oluşturulma Tarihi"
    )

    class Meta:
        db_table = 'SistemLoglari'
        verbose_name = "Sistem Logu"
        verbose_name_plural = "Sistem Logları"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['log_level']),
            models.Index(fields=['kategori']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.log_level} - {self.kategori} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"
    
    @classmethod
    def log(cls, level, category, message, user=None, ip_address=None, user_agent=None, extra_data=None):
        """Log kaydı oluştur"""
        import json
        
        return cls.objects.create(
            user=user,
            log_level=level,
            kategori=category,
            mesaj=message,
            ip_adresi=ip_address,
            user_agent=user_agent,
            ek_bilgiler=json.dumps(extra_data, ensure_ascii=False) if extra_data else None
        )
        
        
    # sms_service/models.py 


class DoctorAlarm(models.Model):
    """
    Doktor tarafından kurulan alarmlar - mevcut yapıya uygun
    """
    
    ALARM_TYPE_CHOICES = [
        ('medication', 'İlaç Hatırlatması'),
        ('appointment', 'Randevu Hatırlatması'),
        ('checkup', 'Kontrol Hatırlatması'),
        ('general', 'Genel Hatırlatma'),
    ]
    
    REPEAT_TYPE_CHOICES = [
        ('once', 'Bir Kez'),
        ('daily', 'Günlük'),
        ('weekly', 'Haftalık'),
        ('monthly', 'Aylık'),
        ('custom', 'Özel'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('paused', 'Duraklatıldı'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    # Primary Key
    id = models.AutoField(primary_key=True)
    
    # Doktor ve Hasta Bilgileri
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_alarms',
        verbose_name="Doktor"
    )
    
    patient_name = models.CharField(
        max_length=100,
        verbose_name="Hasta Adı"
    )
    
    patient_phone = models.CharField(
        max_length=15,
        verbose_name="Hasta Telefon"
    )
    
    patient_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_alarms',
        verbose_name="Hasta Kullanıcı"
    )
    
    # Alarm Bilgileri
    alarm_type = models.CharField(
        max_length=20,
        choices=ALARM_TYPE_CHOICES,
        verbose_name="Alarm Tipi"
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name="Alarm Başlığı"
    )
    
    message = models.TextField(
        verbose_name="Mesaj İçeriği"
    )
    
    # Zaman Bilgileri
    alarm_time = models.TimeField(
        verbose_name="Alarm Saati"
    )
    
    alarm_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Alarm Tarihi"
    )
    
    repeat_type = models.CharField(
        max_length=20,
        choices=REPEAT_TYPE_CHOICES,
        default='once',
        verbose_name="Tekrar Tipi"
    )
    
    custom_days = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Özel Günler",
        help_text="1,2,3,4,5 (Pazartesi-Cuma)"
    )
    
    # Durum
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Durum"
    )
    
    # İstatistikler
    total_sent = models.IntegerField(
        default=0,
        verbose_name="Toplam Gönderim"
    )
    
    successful_sent = models.IntegerField(
        default=0,
        verbose_name="Başarılı Gönderim"
    )
    
    last_sent = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Son Gönderim"
    )
    
    next_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sonraki Çalışma"
    )
    
    # Tarih Bilgileri
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Oluşturulma Tarihi"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Bitiş Tarihi"
    )

    class Meta:
        verbose_name = "Doktor Alarmı"
        verbose_name_plural = "Doktor Alarmları"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['alarm_time']),
            models.Index(fields=['next_run']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.patient_name} ({self.alarm_time})"
    
    def calculate_next_run(self):
        """Sonraki çalışma zamanını hesapla"""
        from datetime import datetime, timedelta
        
        now = timezone.now()
        today = now.date()
        
        if self.repeat_type == 'once':
            if self.alarm_date:
                next_run = timezone.make_aware(
                    datetime.combine(self.alarm_date, self.alarm_time)
                )
                return next_run if next_run > now else None
            else:
                next_run = timezone.make_aware(
                    datetime.combine(today, self.alarm_time)
                )
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
        
        elif self.repeat_type == 'daily':
            next_run = timezone.make_aware(
                datetime.combine(today, self.alarm_time)
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        elif self.repeat_type == 'weekly':
            next_run = timezone.make_aware(
                datetime.combine(today, self.alarm_time)
            )
            if next_run <= now:
                next_run += timedelta(weeks=1)
            return next_run
        
        return None
    
    def should_run_now(self):
        """Şu anda çalışması gerekiyor mu?"""
        if self.status != 'active':
            return False
        
        if self.end_date and timezone.now().date() > self.end_date:
            return False
        
        now = timezone.now()
        return self.next_run and now >= self.next_run
    
    def mark_sent(self, success=True):
        """Gönderim olarak işaretle"""
        self.last_sent = timezone.now()
        self.total_sent += 1
        
        if success:
            self.successful_sent += 1
        
        # Sonraki çalışma zamanını hesapla
        self.next_run = self.calculate_next_run()
        
        # Tek seferlik ise tamamlandı olarak işaretle
        if self.repeat_type == 'once':
            self.status = 'completed'
        
        self.save()

class AlarmHistory(models.Model):
    """
    Alarm gönderim geçmişi
    """
    
    id = models.AutoField(primary_key=True)
    
    alarm = models.ForeignKey(
        DoctorAlarm,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="Alarm"
    )
    
    sms_log = models.ForeignKey(
        SMSLog,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="SMS Log"
    )
    
    sent_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Gönderim Zamanı"
    )
    
    success = models.BooleanField(
        default=False,
        verbose_name="Başarılı"
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name="Hata Mesajı"
    )

    class Meta:
        verbose_name = "Alarm Geçmişi"
        verbose_name_plural = "Alarm Geçmişleri"
        ordering = ['-sent_at']
        
    def __str__(self):
        status = "Başarılı" if self.success else "Başarısız"
        return f"{self.alarm.title} - {status}"