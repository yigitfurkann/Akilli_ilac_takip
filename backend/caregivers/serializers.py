# caregivers/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model  # User import'unu değiştir
from .models import Caregiver, CaregiverPatientAssignment, CaregiverNote
from django.conf import settings

# User model'ini al
User = get_user_model()

class CaregiverSerializer(serializers.ModelSerializer):
    # Read-only fields
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    ortalama_puan = serializers.ReadOnlyField()
    assigned_patients_count = serializers.ReadOnlyField()
    
    # Frontend ile uyumlu field mappings
    first_name = serializers.CharField(source='ad', max_length=50)
    last_name = serializers.CharField(source='soyad', max_length=50)
    phone = serializers.CharField(source='telefon_no', max_length=15, required=False, allow_blank=True)
    birth_date = serializers.DateField(source='dogum_tarihi', required=False, allow_null=True)
    address = serializers.CharField(source='adres', required=False, allow_blank=True)
    education = serializers.CharField(source='egitim_durumu', required=False, allow_blank=True)
    experience = serializers.CharField(source='deneyim', required=False, allow_blank=True)
    certificates = serializers.CharField(source='sertifikalar', required=False, allow_blank=True)
    specialties = serializers.CharField(source='uzmanlik_alanlari', required=False, allow_blank=True)
    working_hours = serializers.CharField(source='calisma_saatleri', required=False, allow_blank=True)
    available_days = serializers.CharField(source='musait_gunler', required=False, allow_blank=True)
    salary = serializers.DecimalField(source='maas', max_digits=10, decimal_places=2, required=False, allow_null=True)
    date_joined = serializers.DateTimeField(source='kayit_tarihi', read_only=True)
    last_login = serializers.DateTimeField(source='son_giris', read_only=True)
    
    # User tablosundan email
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Caregiver
        fields = [
            # ID ve temel bilgiler
            'id', 'full_name', 'age', 'email', 'date_joined', 'last_login',
            
            # Frontend mapping fields
            'first_name', 'last_name', 'phone', 'birth_date', 'address',
            
            # Mesleki bilgiler
            'education', 'experience', 'certificates', 'specialties',
            'working_hours', 'available_days', 'salary',
            
            # Rating bilgileri
            'ortalama_puan', 'assigned_patients_count',
            
            # Sistem bilgileri
            'aktif',
            
            # Eski field isimleri (backward compatibility için)
            'ad', 'soyad', 'telefon_no', 'dogum_tarihi', 'adres',
            'egitim_durumu', 'deneyim', 'sertifikalar', 'uzmanlik_alanlari',
            'calisma_saatleri', 'musait_gunler', 'maas', 'kayit_tarihi', 'son_giris'
        ]
        read_only_fields = [
            'id', 'kayit_tarihi', 'son_giris', 'full_name', 'age', 
            'email', 'date_joined', 'last_login', 'ortalama_puan', 'assigned_patients_count'
        ]
    
    def validate_phone(self, value):
        """Telefon numarası validasyonu"""
        if value:
            cleaned_phone = ''.join(filter(str.isdigit, value))
            if len(cleaned_phone) < 10:
                raise serializers.ValidationError("Telefon numarası en az 10 haneli olmalıdır.")
        return value
    
    def update(self, instance, validated_data):
        """Güncelleme işlemi"""
        # User tablosundaki bilgileri güncelle
        user_data = {}
        if 'ad' in validated_data:
            user_data['first_name'] = validated_data['ad']
        if 'soyad' in validated_data:
            user_data['last_name'] = validated_data['soyad']
        
        if user_data:
            User.objects.filter(id=instance.user.id).update(**user_data)
            instance.user.refresh_from_db()
        
        return super().update(instance, validated_data)

class CaregiverPatientAssignmentSerializer(serializers.ModelSerializer):
    caregiver_name = serializers.CharField(source='caregiver.full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    assignment_duration = serializers.ReadOnlyField()
    
    class Meta:
        model = CaregiverPatientAssignment
        fields = [
            'id', 'caregiver', 'patient', 'caregiver_name', 'patient_name',
            'assigned_date', 'end_date', 'is_active', 'notes',
            'last_contact_date', 'contact_frequency', 'assignment_duration'
        ]
        read_only_fields = ['id', 'assignment_duration']

class CaregiverNoteSerializer(serializers.ModelSerializer):
    caregiver_name = serializers.CharField(source='caregiver.full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = CaregiverNote
        fields = [
            'id', 'caregiver', 'patient', 'caregiver_name', 'patient_name',
            'note', 'note_type', 'is_urgent', 'created_date'
        ]
        read_only_fields = ['id', 'created_date']