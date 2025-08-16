# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from patients.models import Patient

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active']
        read_only_fields = ['id', 'role']


class PatientRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    # Hasta bilgileri
    ad = serializers.CharField(max_length=50)
    soyad = serializers.CharField(max_length=50)
    telefon_no = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False)
    dogum_tarihi = serializers.DateField(required=False)
    cinsiyet = serializers.ChoiceField(choices=Patient.GENDER_CHOICES, required=False)
    adres = serializers.CharField(max_length=500, required=False)
    acil_durum_kisi = serializers.CharField(max_length=100, required=False)
    acil_durum_telefon = serializers.CharField(max_length=15, required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'password', 'password_confirm', 'email', 'first_name', 'last_name',
            'ad', 'soyad', 'telefon_no', 'dogum_tarihi', 'cinsiyet', 'adres',
            'acil_durum_kisi', 'acil_durum_telefon'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Şifreler eşleşmiyor.")
        return attrs
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu kullanıcı adı zaten kullanılıyor.")
        return value
    
    def validate_telefon_no(self, value):
        if Patient.objects.filter(telefon_no=value).exists():
            raise serializers.ValidationError("Bu telefon numarası zaten kayıtlı.")
        return value
    
    def create(self, validated_data):
        # Şifre onay alanını kaldır
        validated_data.pop('password_confirm')
        
        # Hasta bilgilerini ayır
        patient_data = {
            'ad': validated_data.pop('ad'),
            'soyad': validated_data.pop('soyad'),
            'telefon_no': validated_data.pop('telefon_no'),
            'email': validated_data.get('email', ''),
            'dogum_tarihi': validated_data.pop('dogum_tarihi', None),
            'cinsiyet': validated_data.pop('cinsiyet', None),
            'adres': validated_data.pop('adres', ''),
            'acil_durum_kisi': validated_data.pop('acil_durum_kisi', ''),
            'acil_durum_telefon': validated_data.pop('acil_durum_telefon', ''),
        }
        
        # User oluştur
        password = validated_data.pop('password')
        validated_data['user_type'] = 'Hasta'
        validated_data['first_name'] = patient_data['ad']
        validated_data['last_name'] = patient_data['soyad']
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Patient profili oluştur
        patient_data['user'] = user
        Patient.objects.create(**patient_data)
        
        return user