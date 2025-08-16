# doctors/serializers.py

from rest_framework import serializers
from .models import Doctor

class DoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    working_hours = serializers.ReadOnlyField(source='get_calisma_saatleri')
    
    class Meta:
        model = Doctor
        fields = [
            'doktor_id', 'ad', 'soyad', 'full_name', 'uzmanlik', 
            'diploma_no', 'telefon_no', 'email', 'working_hours',
            'muayenehane_adresi', 'is_active', 'created_at'
        ]
        read_only_fields = ['doktor_id', 'created_at', 'full_name', 'working_hours']