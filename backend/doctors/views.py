# doctors/views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from .models import Doctor
from patients.models import Patient
from appointments.models import Appointment
from medications.models import Ilac
from notifications.models import Bildirim
from sms_service.models import SMSLog
from .serializers import DoctorSerializer
import json

class DoctorPatientsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Doktorun hastalarını listele"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            
            # Doktorun randevuları olan hastaları getir
            appointments = Appointment.objects.filter(doktor=doctor).values('hasta').distinct()
            patient_ids = [app['hasta'] for app in appointments]
            patients = Patient.objects.filter(id__in=patient_ids)
            
            patient_list = []
            for patient in patients:
                # Her hasta için son randevu bilgisi
                last_appointment = Appointment.objects.filter(
                    hasta=patient, 
                    doktor=doctor
                ).order_by('-randevu_tarihi').first()
                
                # Hasta için aktif ilaç sayısı
                active_medications = Ilac.objects.filter(
                    hasta=patient, 
                    doktor=doctor, 
                    aktif=True
                ).count()
                
                # Hastanın aktif bakıcısı var mı kontrol et
                from caregivers.models import CaregiverPatientAssignment
                active_caregiver = CaregiverPatientAssignment.objects.filter(
                    patient=patient,
                    is_active=True
                ).first()
                
                patient_data = {
                    'id': patient.id,
                    'name': patient.full_name,
                    'phone': patient.telefon_no,
                    'email': patient.email,
                    'age': patient.age,
                    'gender': patient.cinsiyet,
                    'address': patient.adres,
                    'last_appointment': {
                        'date': last_appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M') if last_appointment else None,
                        'type': last_appointment.randevu_tipi if last_appointment else None,
                        'status': last_appointment.durum if last_appointment else None
                    },
                    'active_medications_count': active_medications,
                    'emergency_contact': {
                        'name': patient.acil_durum_kisi,
                        'phone': patient.acil_durum_telefon
                    },
                    'caregiver_info': {
                        'has_caregiver': active_caregiver is not None,
                        'caregiver_name': active_caregiver.caregiver.full_name if active_caregiver else None,
                        'caregiver_phone': active_caregiver.caregiver.telefon_no if active_caregiver else None,
                        'assignment_date': active_caregiver.assigned_date.strftime('%Y-%m-%d') if active_caregiver else None
                    }
                }
                patient_list.append(patient_data)
            
            return Response(patient_list)
            
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)


class DoctorAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Doktorun randevularını listele"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            appointments = Appointment.objects.filter(doktor=doctor).order_by('-randevu_tarihi')
            
            appointment_list = []
            for appointment in appointments:
                appointment_data = {
                    'id': appointment.randevu_id,
                    'patient_name': appointment.hasta.full_name,
                    'patient_phone': appointment.hasta.telefon_no,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                    'time': appointment.randevu_tarihi.strftime('%H:%M'),
                    'duration': appointment.randevu_suresi,
                    'status': appointment.durum,
                    'type': appointment.randevu_tipi,
                    'patient_notes': appointment.hasta_notlari,
                    'doctor_notes': appointment.doktor_notlari,
                    'is_online': appointment.online_randevu_mu,
                    'created_date': appointment.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M'),
                    'can_approve': appointment.durum == 'Beklemede',
                    'is_past': appointment.is_past,
                    'is_today': appointment.is_today
                }
                appointment_list.append(appointment_data)
            
            return Response(appointment_list)
            
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, appointment_id):
        """Randevu durumu güncelle (onayla/reddet)"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            appointment = get_object_or_404(
                Appointment, 
                randevu_id=appointment_id, 
                doktor=doctor
            )
            
            action = request.data.get('action')  # 'approve' veya 'reject'
            doctor_notes = request.data.get('doctor_notes', '')
            
            if action == 'approve':
                if appointment.approve(request.user):
                    # Hastaya onay bildirimi gönder
                    notification = Bildirim.objects.create(
                        gonderen=request.user,
                        gonderen_tip='doktor',
                        alici=appointment.hasta.user,
                        alici_tip='hasta',
                        bildirim_tipi='randevu_onay',
                        baslik='Randevunuz Onaylandı',
                        mesaj=f'{appointment.randevu_tarihi.strftime("%d.%m.%Y %H:%M")} tarihli randevunuz onaylanmıştır.',
                        randevu=appointment
                    )
                    
                    # SMS gönder
                    self._send_sms_notification(
                        appointment.hasta.telefon_no,
                        f"Sayın {appointment.hasta.full_name}, {appointment.randevu_tarihi.strftime('%d.%m.%Y %H:%M')} tarihli randevunuz Dr. {doctor.full_name} tarafından onaylanmıştır.",
                        appointment.hasta.user,
                        'RandevuOnay'
                    )
                    
                    message = 'Randevu onaylandı ve hastaya bildirim gönderildi'
                else:
                    message = 'Randevu onaylanamadı'
                    
            elif action == 'reject':
                if appointment.reject(request.user):
                    # Hastaya red bildirimi gönder
                    notification = Bildirim.objects.create(
                        gonderen=request.user,
                        gonderen_tip='doktor',
                        alici=appointment.hasta.user,
                        alici_tip='hasta',
                        bildirim_tipi='randevu_red',
                        baslik='Randevu Talebi Reddedildi',
                        mesaj=f'{appointment.randevu_tarihi.strftime("%d.%m.%Y %H:%M")} tarihli randevu talebiniz reddedilmiştir. Lütfen farklı bir tarih seçiniz.',
                        randevu=appointment
                    )
                    
                    # SMS gönder
                    self._send_sms_notification(
                        appointment.hasta.telefon_no,
                        f"Sayın {appointment.hasta.full_name}, {appointment.randevu_tarihi.strftime('%d.%m.%Y %H:%M')} tarihli randevu talebiniz reddedilmiştir.",
                        appointment.hasta.user,
                        'RandevuRed'
                    )
                    
                    message = 'Randevu reddedildi ve hastaya bildirim gönderildi'
                else:
                    message = 'Randevu reddedilemedi'
            
            # Doktor notunu ekle
            if doctor_notes:
                appointment.doktor_notlari = doctor_notes
                appointment.save()
            
            return Response({'message': message})
            
        except Exception as e:
            return Response({
                'error': f'İşlem gerçekleştirilemedi: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_sms_notification(self, phone, message, user, message_type):
        """SMS bildirimi gönder"""
        try:
            # SMS log oluştur
            SMSLog.objects.create(
                recipient_phone=phone,
                recipient_user=user,
                message=message,
                message_type=message_type,
                status='Pending'
            )
            # Gerçek SMS gönderimi Huawei Cloud ile yapılacak
        except Exception as e:
            print(f"SMS gönderim hatası: {e}")


class DoctorMedicationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Doktorun yazdığı ilaçları listele"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            medications = Ilac.objects.filter(doktor=doctor).order_by('-olusturulma_tarihi')
            
            medication_list = []
            for medication in medications:
                medication_data = {
                    'id': medication.id,
                    'patient_name': medication.hasta.full_name,
                    'medication_name': medication.ilac_adi,
                    'active_ingredient': medication.etken_madde,
                    'dosage': medication.dozaj,
                    'frequency': medication.kullanim_sikligi,
                    'meal_relation': medication.yemek_iliskisi,
                    'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                    'end_date': medication.bitis_tarihi.strftime('%Y-%m-%d') if medication.bitis_tarihi else None,
                    'instructions': medication.kullanim_talimatlari,
                    'is_active': medication.aktif,
                    'is_current': medication.is_current,
                    'created_date': medication.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M')
                }
                medication_list.append(medication_data)
            
            return Response(medication_list)
            
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        """Hastaya yeni ilaç ekle"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            patient_id = request.data.get('patient_id')
            
            print(f"Gelen veri: {request.data}")  # Debug için
            
            if not patient_id:
                return Response({
                    'error': 'Hasta seçimi gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            patient = get_object_or_404(Patient, id=patient_id)
            
            # İlaç adı kontrolü - hem medication_name hem de name'i kontrol et
            ilac_adi = request.data.get('medication_name') or request.data.get('name', '').strip()
            if not ilac_adi:
                return Response({
                    'error': 'İlaç adı gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Dozaj kontrolü
            dozaj = request.data.get('dosage', '').strip()
            if not dozaj:
                return Response({
                    'error': 'Dozaj bilgisi gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Kullanım sıklığı kontrolü
            kullanim_sikligi = request.data.get('frequency', '').strip()
            if not kullanim_sikligi:
                return Response({
                    'error': 'Kullanım sıklığı gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Tarih kontrolü - start_date gelirse onu kullan, yoksa bugünü kullan
            baslangic_tarihi = request.data.get('start_date')
            if not baslangic_tarihi:
                from datetime import date
                baslangic_tarihi = date.today()
            
            # Bitiş tarihi hesaplama
            bitis_tarihi = request.data.get('end_date')
            if not bitis_tarihi and request.data.get('duration_days'):
                try:
                    from datetime import date, timedelta
                    duration = int(request.data.get('duration_days'))
                    if isinstance(baslangic_tarihi, str):
                        from datetime import datetime
                        baslangic_tarihi = datetime.strptime(baslangic_tarihi, '%Y-%m-%d').date()
                    bitis_tarihi = baslangic_tarihi + timedelta(days=duration)
                except (ValueError, TypeError):
                    pass  # Hata durumunda bitiş tarihi None kalır
            
            # İlaç oluştur
            medication = Ilac.objects.create(
                hasta=patient,
                doktor=doctor,
                ilac_adi=ilac_adi,
                etken_madde=request.data.get('active_ingredient', ''),
                dozaj=dozaj,
                kullanim_sikligi=kullanim_sikligi,
                yemek_iliskisi=request.data.get('meal_relation', 'farketmez'),
                baslangic_tarihi=baslangic_tarihi,
                bitis_tarihi=bitis_tarihi,
                kullanim_talimatlari=request.data.get('instructions', ''),
                yan_etkiler=request.data.get('side_effects', ''),
                uyarilar=request.data.get('warnings', ''),
                aktif=True  # Varsayılan olarak aktif
            )
            
            print(f"İlaç oluşturuldu: {medication.id} - {medication.ilac_adi}")  # Debug için
            
            # Hastaya bildirim gönder
            try:
                Bildirim.objects.create(
                    gonderen=request.user,
                    gonderen_tip='doktor',
                    alici=patient.user,
                    alici_tip='hasta',
                    bildirim_tipi='ilac_eklendi',
                    baslik='Yeni İlaç Reçetesi',
                    mesaj=f'Dr. {doctor.full_name} tarafından size {medication.ilac_adi} ({medication.dozaj}) reçete edilmiştir. Kullanım: {medication.kullanim_sikligi}',
                    ilac=medication
                )
            except Exception as bildirim_error:
                print(f"Bildirim oluşturma hatası: {bildirim_error}")
            
            # SMS bildirimi (opsiyonel)
            try:
                SMSLog.objects.create(
                    recipient_phone=patient.telefon_no,
                    recipient_user=patient.user,
                    message=f"Sayın {patient.full_name}, Dr. {doctor.full_name} tarafından {medication.ilac_adi} ilacı reçete edilmiştir. Kullanım: {medication.kullanim_sikligi}",
                    message_type='IlacEklendi',
                    status='Pending'
                )
            except Exception as sms_error:
                print(f"SMS gönderim hatası: {sms_error}")
            
            return Response({
                'message': 'İlaç başarıyla eklendi ve hastaya bildirim gönderildi',
                'medication_id': medication.id,
                'medication_name': medication.ilac_adi,
                'patient_name': patient.full_name
            }, status=status.HTTP_201_CREATED)
            
        except Patient.DoesNotExist:
            return Response({
                'error': 'Hasta bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"İlaç ekleme genel hatası: {str(e)}")  # Debug için
            return Response({
                'error': f'İlaç eklenemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DoctorNotificationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Doktorun bildirimlerini listele"""
        notifications = Bildirim.objects.filter(
            alici=request.user,
            aktif=True
        ).order_by('-gonderim_tarihi')
        
        notification_list = []
        for notification in notifications:
            notification_data = {
                'id': notification.id,
                'title': notification.baslik,
                'message': notification.mesaj,
                'type': notification.bildirim_tipi,
                'priority': notification.oncelik,
                'is_read': notification.okundu,
                'sent_date': notification.gonderim_tarihi.strftime('%Y-%m-%d %H:%M'),
                'sender_type': notification.gonderen_tip,
                'patient_name': notification.randevu.hasta.full_name if notification.randevu else None,
                'appointment_id': notification.randevu.randevu_id if notification.randevu else None
            }
            notification_list.append(notification_data)
        
        return Response(notification_list)
    
    def post(self, request):
        """Hastaya özel bildirim gönder"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            patient = get_object_or_404(Patient, id=request.data.get('patient_id'))
            
            message = request.data.get('message')
            title = request.data.get('title', 'Doktorunuzdan Mesaj')
            
            # Bildirim oluştur
            notification = Bildirim.objects.create(
                gonderen=request.user,
                gonderen_tip='doktor',
                alici=patient.user,
                alici_tip='hasta',
                bildirim_tipi='genel',
                baslik=title,
                mesaj=message
            )
            
            # SMS gönder
            self._send_sms_notification(
                patient.telefon_no,
                f"Dr. {doctor.full_name}: {message}",
                patient.user,
                'DoktorMesaj'
            )
            
            return Response({
                'message': 'Bildirim gönderildi ve SMS olarak iletildi'
            })
            
        except Exception as e:
            return Response({
                'error': f'Bildirim gönderilemedi: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_sms_notification(self, phone, message, user, message_type):
        """SMS bildirimi gönder"""
        try:
            SMSLog.objects.create(
                recipient_phone=phone,
                recipient_user=user,
                message=message,
                message_type=message_type,
                status='Pending'
            )
        except Exception as e:
            print(f"SMS gönderim hatası: {e}")


# ==================== CAREGIVER MANAGEMENT VIEWS ====================

class DoctorCaregiversView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Mevcut bakıcıları listele"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            
            # Bakıcıları getir (şimdilik tüm aktif bakıcılar)
            # Gelecekte doktorun bulunduğu bölgedeki bakıcılar getirilebilir
            from caregivers.models import Caregiver, CaregiverPatientAssignment
            caregivers = Caregiver.objects.filter(aktif=True)
            
            caregiver_list = []
            for caregiver in caregivers:
                # Her bakıcı için aktif hasta sayısını hesapla
                active_assignments = CaregiverPatientAssignment.objects.filter(
                    caregiver=caregiver,
                    is_active=True
                ).count()
                
                # Maksimum hasta sayısı için default değer (modelde yoksa 5 kabul et)
                max_patients = 5  # Default değer
                
                caregiver_data = {
                    'id': caregiver.id,
                    'name': caregiver.full_name,
                    'phone': caregiver.telefon_no,
                    'email': caregiver.email,
                    'address': caregiver.adres,
                    'experience_years': caregiver.deneyim if caregiver.deneyim else '0-1',
                    'specializations': caregiver.uzmanlik_alanlari.split(',') if caregiver.uzmanlik_alanlari else [],
                    'is_available': active_assignments < max_patients,
                    'current_patient_count': active_assignments,
                    'max_patient_count': max_patients,
                    'rating': float(caregiver.ortalama_puan),
                    'total_reviews': caregiver.degerlendirme_sayisi,
                    'education': caregiver.get_egitim_durumu_display() if caregiver.egitim_durumu else 'Belirtilmemiş',
                    'city': 'İstanbul',  # Default şehir
                    'district': 'Merkez',  # Default ilçe
                    'shift_preference': caregiver.calisma_saatleri if caregiver.calisma_saatleri else 'Esnek',
                    'profile_photo': None,  # Profil fotoğrafı field'ı yok
                    'about': 'Deneyimli bakıcı',  # Default açıklama
                    'certificates': caregiver.sertifikalar if caregiver.sertifikalar else 'Belirtilmemiş'
                }
                caregiver_list.append(caregiver_data)
            
            return Response(caregiver_list)
            
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)


class DoctorCaregiverAssignmentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Doktorun bakıcı atamalarını listele"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            
            # Query parametrelerini kontrol et
            patient_id = request.GET.get('patient_id')
            caregiver_id = request.GET.get('caregiver_id')
            
            # Base queryset - sadece bu doktorun hastalarına yapılan atamalar
            from caregivers.models import CaregiverPatientAssignment
            from appointments.models import Appointment
            
            # Bu doktorun hastalarını bul
            doctor_patients = Appointment.objects.filter(doktor=doctor).values('hasta').distinct()
            patient_ids = [app['hasta'] for app in doctor_patients]
            
            assignments = CaregiverPatientAssignment.objects.filter(
                patient__id__in=patient_ids
            ).select_related('patient', 'caregiver').distinct()
            
            # Filtreleme
            if patient_id:
                assignments = assignments.filter(patient_id=patient_id)
            if caregiver_id:
                assignments = assignments.filter(caregiver_id=caregiver_id)
            
            assignment_list = []
            for assignment in assignments:
                assignment_data = {
                    'id': assignment.id,
                    'patient_id': assignment.patient.id,
                    'patient_name': assignment.patient.full_name,
                    'patient_phone': assignment.patient.telefon_no,
                    'caregiver_id': assignment.caregiver.id,
                    'caregiver_name': assignment.caregiver.full_name,
                    'caregiver_phone': assignment.caregiver.telefon_no,
                    'start_date': assignment.assigned_date.strftime('%Y-%m-%d'),
                    'end_date': assignment.end_date.strftime('%Y-%m-%d') if assignment.end_date else None,
                    'notes': assignment.notes if assignment.notes else '',
                    'is_active': assignment.is_active,
                    'status': 'aktif' if assignment.is_active else 'pasif',
                    'created_date': assignment.assigned_date.strftime('%Y-%m-%d %H:%M'),
                    'assigned_by': f"Dr. {doctor.full_name}",
                    'patient_approval': True,  # Default değer
                    'caregiver_approval': True,  # Default değer
                    'doctor_approval': True,  # Default değer
                    'emergency': False,  # Default değer
                    'special_requirements': assignment.notes if assignment.notes else ''
                }
                assignment_list.append(assignment_data)
            
            return Response(assignment_list)
            
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        """Yeni bakıcı ataması yap"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            patient_id = request.data.get('patient_id')
            caregiver_id = request.data.get('caregiver_id')
            
            if not patient_id or not caregiver_id:
                return Response({
                    'error': 'Hasta ID ve Bakıcı ID gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Hasta kontrolü - sadece bu doktorun hastası olmalı
            from appointments.models import Appointment
            patient = get_object_or_404(Patient, id=patient_id)
            if not Appointment.objects.filter(hasta=patient, doktor=doctor).exists():
                return Response({
                    'error': 'Bu hasta sizin hastanız değil'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Bakıcı kontrolü
            from caregivers.models import Caregiver, CaregiverPatientAssignment
            caregiver = get_object_or_404(Caregiver, id=caregiver_id, aktif=True)
            
            # Mevcut aktif atama kontrolü
            existing_assignment = CaregiverPatientAssignment.objects.filter(
                patient=patient,
                is_active=True
            ).first()
            
            if existing_assignment:
                return Response({
                    'error': f'Bu hasta zaten {existing_assignment.caregiver.full_name} ile eşleştirilmiş'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Bakıcının kapasitesi kontrolü (maksimum 5 hasta default)
            current_assignments = CaregiverPatientAssignment.objects.filter(
                caregiver=caregiver,
                is_active=True
            ).count()
            
            max_patients = 5  # Default maksimum hasta sayısı
            if current_assignments >= max_patients:
                return Response({
                    'error': 'Bu bakıcının hasta kapasitesi dolu'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Başlangıç tarihi kontrolü
            start_date = request.data.get('start_date')
            if not start_date:
                from datetime import date
                start_date = date.today()
            else:
                from datetime import datetime
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            # Yeni atama oluştur
            assignment = CaregiverPatientAssignment.objects.create(
                patient=patient,
                caregiver=caregiver,
                assigned_date=timezone.now(),
                notes=request.data.get('notes', ''),
                is_active=True
            )
            
            # Hastaya bildirim gönder
            try:
                Bildirim.objects.create(
                    gonderen=request.user,
                    gonderen_tip='doktor',
                    alici=patient.user,
                    alici_tip='hasta',
                    bildirim_tipi='bakici_atandi',
                    baslik='Bakıcı Atandı',
                    mesaj=f'Size {caregiver.full_name} adlı bakıcı atanmıştır. Deneyim: {caregiver.deneyim if caregiver.deneyim else "0-1"} yıl. Kendisi sizinle iletişime geçecektir.',
                    oncelik='orta'
                )
            except Exception as e:
                print(f"Hasta bildirim hatası: {e}")
            
            # Bakıcıya bildirim gönder
            try:
                Bildirim.objects.create(
                    gonderen=request.user,
                    gonderen_tip='doktor',
                    alici=caregiver.user,
                    alici_tip='bakici',
                    bildirim_tipi='hasta_atandi',
                    baslik='Yeni Hasta Atandı',
                    mesaj=f'Size {patient.full_name} adlı hasta atanmıştır. Başlangıç tarihi: {assignment.assigned_date.strftime("%d.%m.%Y")}. Lütfen hasta ile iletişime geçiniz.',
                    oncelik='yuksek'
                )
            except Exception as e:
                print(f"Bakıcı bildirim hatası: {e}")
            
            # SMS bildirimleri gönder
            try:
                # Hastaya SMS
                SMSLog.objects.create(
                    recipient_phone=patient.telefon_no,
                    recipient_user=patient.user,
                    message=f"Sayın {patient.full_name}, Dr. {doctor.full_name} tarafından size {caregiver.full_name} adlı bakıcı atanmıştır. İletişim: {caregiver.telefon_no}",
                    message_type='BakiciAtandi',
                    status='Pending'
                )
                
                # Bakıcıya SMS
                SMSLog.objects.create(
                    recipient_phone=caregiver.telefon_no,
                    recipient_user=caregiver.user,
                    message=f"Sayın {caregiver.full_name}, Dr. {doctor.full_name} tarafından size {patient.full_name} adlı hasta atanmıştır. İletişim: {patient.telefon_no}",
                    message_type='HastaAtandi',
                    status='Pending'
                )
            except Exception as e:
                print(f"SMS gönderim hatası: {e}")
            
            return Response({
                'message': 'Bakıcı başarıyla atandı ve bildirimleri gönderildi',
                'assignment_id': assignment.id,
                'patient_name': patient.full_name,
                'caregiver_name': caregiver.full_name,
                'start_date': assignment.assigned_date.strftime('%Y-%m-%d')
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Atama gerçekleştirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, assignment_id):
        """Bakıcı atamasını kaldır"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            from caregivers.models import CaregiverPatientAssignment
            
            # Bu doktorun hastalarına ait atamayı kontrol et
            doctor_patients = Appointment.objects.filter(doktor=doctor).values('hasta').distinct()
            patient_ids = [app['hasta'] for app in doctor_patients]
            
            assignment = get_object_or_404(
                CaregiverPatientAssignment, 
                id=assignment_id,
                patient__id__in=patient_ids
            )
            
            # Atamayı pasif yap (hard delete yapmak yerine)
            assignment.is_active = False
            if not assignment.end_date:
                assignment.end_date = timezone.now()
            assignment.save()
            
            # Bildirimleri gönder
            try:
                # Hastaya bildirim
                Bildirim.objects.create(
                    gonderen=request.user,
                    gonderen_tip='doktor',
                    alici=assignment.patient.user,
                    alici_tip='hasta',
                    bildirim_tipi='bakici_kaldirildi',
                    baslik='Bakıcı Ataması Kaldırıldı',
                    mesaj=f'{assignment.caregiver.full_name} adlı bakıcının ataması Dr. {doctor.full_name} tarafından kaldırılmıştır.',
                    oncelik='orta'
                )
                
                # Bakıcıya bildirim
                Bildirim.objects.create(
                    gonderen=request.user,
                    gonderen_tip='doktor',
                    alici=assignment.caregiver.user,
                    alici_tip='bakici',
                    bildirim_tipi='hasta_kaldirildi',
                    baslik='Hasta Ataması Kaldırıldı',
                    mesaj=f'{assignment.patient.full_name} adlı hasta ataması Dr. {doctor.full_name} tarafından kaldırılmıştır.',
                    oncelik='orta'
                )
            except Exception as e:
                print(f"Bildirim gönderim hatası: {e}")
            
            # SMS bildirimleri gönder
            try:
                # Hastaya SMS
                SMSLog.objects.create(
                    recipient_phone=assignment.patient.telefon_no,
                    recipient_user=assignment.patient.user,
                    message=f"Sayın {assignment.patient.full_name}, {assignment.caregiver.full_name} adlı bakıcının ataması kaldırılmıştır.",
                    message_type='BakiciKaldirildi',
                    status='Pending'
                )
                
                # Bakıcıya SMS
                SMSLog.objects.create(
                    recipient_phone=assignment.caregiver.telefon_no,
                    recipient_user=assignment.caregiver.user,
                    message=f"Sayın {assignment.caregiver.full_name}, {assignment.patient.full_name} adlı hasta ataması kaldırılmıştır.",
                    message_type='HastaKaldirildi',
                    status='Pending'
                )
            except Exception as e:
                print(f"SMS gönderim hatası: {e}")
            
            return Response({
                'message': 'Bakıcı ataması başarıyla kaldırıldı ve bildirimleri gönderildi'
            })
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Atama bulunamadı veya bu atamayı kaldırma yetkiniz yok'
            }, status=status.HTTP_404_NOT_FOUND)


class DoctorCaregiverStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Bakıcı istatistikleri"""
        try:
            doctor = get_object_or_404(Doctor, user=request.user)
            from caregivers.models import Caregiver, CaregiverPatientAssignment
            
            # Bu doktorun hastalarını bul
            from appointments.models import Appointment
            doctor_patients = Appointment.objects.filter(doktor=doctor).values('hasta').distinct()
            patient_ids = [app['hasta'] for app in doctor_patients]
            
            # İstatistikleri hesapla
            total_caregivers = Caregiver.objects.filter(aktif=True).count()
            available_caregivers = Caregiver.objects.filter(
                aktif=True,
                id__in=Caregiver.objects.annotate(
                    current_assignments=models.Count('caregiver_assignments', filter=models.Q(caregiver_assignments__is_active=True))
                ).filter(current_assignments__lt=5).values('id')  # Varsayılan maksimum hasta sayısı 5
            ).count()
            
            total_assignments = CaregiverPatientAssignment.objects.filter(
                patient__id__in=patient_ids
            ).count()
            
            active_assignments = CaregiverPatientAssignment.objects.filter(
                patient__id__in=patient_ids,
                is_active=True
            ).count()
            
            stats = {
                'total_caregivers': total_caregivers,
                'available_caregivers': available_caregivers,
                'total_assignments': total_assignments,
                'active_assignments': active_assignments,
                'assignment_success_rate': round((active_assignments / total_assignments * 100) if total_assignments > 0 else 0, 2)
            }
            
            return Response(stats)
            
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Doktor profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)