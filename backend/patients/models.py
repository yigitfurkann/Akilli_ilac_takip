from django.db import models
from django.core.validators import RegexValidator
from accounts.models import User

class Patient(models.Model):
    """
    Hasta modeli
    """
    GENDER_CHOICES = [
        ('Erkek', 'Erkek'),
        ('Kadin', 'Kadın'),
        ('Diger', 'Diğer'),
    ]
    
    # Yeni: Kan grubu seçenekleri
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A Rh+'),
        ('A-', 'A Rh-'),
        ('B+', 'B Rh+'),
        ('B-', 'B Rh-'),
        ('AB+', 'AB Rh+'),
        ('AB-', 'AB Rh-'),
        ('O+', 'O Rh+'),
        ('O-', 'O Rh-'),
    ]
        
    # Foreign Key to User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name="Kullanıcı",
        related_name='hasta_profile'
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
        
    # Telefon numarası validasyonu
    phone_regex = RegexValidator(
        regex=r'^(\+90|05)\d{10,}$',
        message="Telefon numarası +90 veya 05 ile başlamalıdır."
    )
        
    telefon_no = models.CharField(
        validators=[phone_regex],
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
        
    cinsiyet = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
        verbose_name="Cinsiyet"
    )
        
    adres = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Adres"
    )
        
    # Acil Durum Bilgileri
    acil_durum_kisi = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Acil Durum Kişisi"
    )
        
    acil_durum_telefon = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="Acil Durum Telefonu"
    )
    
    # YENİ: Sağlık Bilgileri
    medical_conditions = models.TextField(
        null=True,
        blank=True,
        verbose_name="Kronik Hastalıklar",
        help_text="Diyabet, hipertansiyon, astım vb. kronik hastalıkları belirtiniz"
    )
    
    allergies = models.TextField(
        null=True,
        blank=True,
        verbose_name="Alerjiler",
        help_text="İlaç, besin, polen vb. alerjilerinizi belirtiniz"
    )
    
    blood_type = models.CharField(
        max_length=3,
        choices=BLOOD_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Kan Grubu"
    )
        
    # Sistem Bilgileri
    kayit_tarihi = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Kayıt Tarihi"
    )
    
    # YENİ: Ek sistem bilgileri
    aktif = models.BooleanField(
        default=True,
        verbose_name="Aktif"
    )
    
    son_giris = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Son Giriş"
    )

    class Meta:
        verbose_name = "Hasta"
        verbose_name_plural = "Hastalar"
            
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
    
    # YENİ: Ek property'ler
    @property
    def gender_display(self):
        """Cinsiyet görüntüleme - frontend uyumluluğu için"""
        gender_map = {
            'Erkek': 'E',
            'Kadin': 'K', 
            'Diger': 'O'
        }
        return gender_map.get(self.cinsiyet, '')
    
    @property
    def gender_for_frontend(self):
        """Frontend için cinsiyet mapping"""
        return self.gender_display
    
    @property
    def blood_type_display(self):
        """Kan grubu display"""
        return self.get_blood_type_display() if self.blood_type else 'Belirtilmemiş'
    
    @property
    def has_emergency_contact(self):
        """Acil durum iletişim bilgisi var mı?"""
        return bool(self.acil_durum_kisi and self.acil_durum_telefon)
    
    @property
    def has_health_info(self):
        """Sağlık bilgileri eklenmiş mi?"""
        return bool(self.medical_conditions or self.allergies or self.blood_type)
    
    @property
    def profile_completion_percentage(self):
        """Profil tamamlanma yüzdesi"""
        total_fields = 11
        completed_fields = 0
        
        # Temel bilgiler (zorunlu olanlar hariç - zaten var)
        if self.ad: completed_fields += 1
        if self.soyad: completed_fields += 1
        if self.telefon_no: completed_fields += 1
        if self.dogum_tarihi: completed_fields += 1
        if self.cinsiyet: completed_fields += 1
        if self.adres: completed_fields += 1
        
        # Acil durum bilgileri
        if self.acil_durum_kisi: completed_fields += 1
        if self.acil_durum_telefon: completed_fields += 1
        
        # Sağlık bilgileri
        if self.blood_type: completed_fields += 1
        if self.medical_conditions: completed_fields += 1
        if self.allergies: completed_fields += 1
        
        return round((completed_fields / total_fields) * 100)