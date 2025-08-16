# patients/serializers.py
from rest_framework import serializers
from .models import Patient

class PatientSerializer(serializers.ModelSerializer):
    # Mevcut read-only fields
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    
    # Frontend ile uyumlu field mappings
    first_name = serializers.CharField(source='ad', max_length=50)
    last_name = serializers.CharField(source='soyad', max_length=50)
    phone = serializers.CharField(source='telefon_no', max_length=15, required=False, allow_blank=True)
    birth_date = serializers.DateField(source='dogum_tarihi', required=False, allow_null=True)
    address = serializers.CharField(source='adres', required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(source='acil_durum_kisi', max_length=100, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(source='acil_durum_telefon', max_length=15, required=False, allow_blank=True)
    date_joined = serializers.DateTimeField(source='kayit_tarihi', read_only=True)
    
    # Cinsiyet için özel mapping (mevcut model yapısı korunarak)
    gender = serializers.SerializerMethodField()
    
    # Yeni sağlık bilgileri fields
    medical_conditions = serializers.CharField(required=False, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_blank=True)
    blood_type = serializers.CharField(max_length=3, required=False, allow_blank=True)
    
    class Meta:
        model = Patient
        fields = [
            # ID ve temel bilgiler
            'id', 'full_name', 'age', 'email', 'date_joined',
            
            # Frontend mapping fields
            'first_name', 'last_name', 'phone', 'birth_date', 
            'gender', 'address', 'blood_type',
            
            # Acil durum bilgileri
            'emergency_contact_name', 'emergency_contact_phone',
            
            # Sağlık bilgileri
            'medical_conditions', 'allergies',
            
            # Mevcut field isimleri (backward compatibility için)
            'ad', 'soyad', 'telefon_no', 'dogum_tarihi', 
            'cinsiyet', 'adres', 'acil_durum_kisi', 'acil_durum_telefon', 
            'kayit_tarihi'
        ]
        read_only_fields = ['id', 'kayit_tarihi', 'full_name', 'age', 'date_joined']
    
    def get_gender(self, obj):
        """Cinsiyet mapping - frontend için E/K/O formatına çevir"""
        gender_map = {
            'Erkek': 'E',
            'Kadin': 'K',
            'Diger': 'O'
        }
        return gender_map.get(obj.cinsiyet, '')
    
    def validate_gender(self, value):
        """Frontend'den gelen E/K/O değerlerini model formatına çevir"""
        if hasattr(self, 'initial_data') and 'gender' in self.initial_data:
            frontend_gender = self.initial_data['gender']
            gender_reverse_map = {
                'E': 'Erkek',
                'K': 'Kadin',
                'O': 'Diger'
            }
            return gender_reverse_map.get(frontend_gender, '')
        return value
    
    def validate_blood_type(self, value):
        """Kan grubu validasyonu"""
        valid_blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        if value and value not in valid_blood_types:
            raise serializers.ValidationError(f"Geçerli kan grupları: {', '.join(valid_blood_types)}")
        return value
    
    def validate_phone(self, value):
        """Telefon numarası validasyonu"""
        if value:
            # Mevcut model validasyonu zaten var, burada ek kontrol
            cleaned_phone = ''.join(filter(str.isdigit, value))
            if len(cleaned_phone) < 10:
                raise serializers.ValidationError("Telefon numarası en az 10 haneli olmalıdır.")
        return value
    
    def validate_emergency_contact_phone(self, value):
        """Acil durum telefon validasyonu"""
        if value:
            cleaned_phone = ''.join(filter(str.isdigit, value))
            if len(cleaned_phone) < 10:
                raise serializers.ValidationError("Acil durum telefonu en az 10 haneli olmalıdır.")
        return value
    
    def to_internal_value(self, data):
        """Frontend'den gelen veriyi model formatına çevir"""
        # Cinsiyet mapping'i
        if 'gender' in data:
            gender_reverse_map = {
                'E': 'Erkek',
                'K': 'Kadin', 
                'O': 'Diger'
            }
            # cinsiyet field'ını da güncelle (model için)
            data['cinsiyet'] = gender_reverse_map.get(data['gender'], '')
        
        return super().to_internal_value(data)
    
    def update(self, instance, validated_data):
        """Güncelleme işlemi"""
        # Cinsiyet mapping'i update sırasında
        if 'gender' in self.initial_data:
            gender_reverse_map = {
                'E': 'Erkek',
                'K': 'Kadin',
                'O': 'Diger'
            }
            validated_data['cinsiyet'] = gender_reverse_map.get(self.initial_data['gender'], instance.cinsiyet)
        
        # User tablosundaki bilgileri güncelle (eğer User modeli varsa)
        if hasattr(instance.user, 'first_name'):
            if 'ad' in validated_data:
                instance.user.first_name = validated_data['ad']
            if 'soyad' in validated_data:
                instance.user.last_name = validated_data['soyad']
            if 'email' in validated_data:
                instance.user.email = validated_data['email']
            instance.user.save()
        
        return super().update(instance, validated_data)