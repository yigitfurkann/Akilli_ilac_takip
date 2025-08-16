# caregivers/views.py - Mevcut view'lara EK OLARAK aşağıdaki güncellemeleri yapın

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q

from .models import Caregiver, CaregiverPatientAssignment, CaregiverNote
from patients.models import Patient
from appointments.models import Appointment
from medications.models import Ilac
from notifications.models import Bildirim
from .serializers import CaregiverSerializer, CaregiverPatientAssignmentSerializer

class CaregiverDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Bakıcı dashboard istatistikleri"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının hastalarını getir
            assigned_patients = CaregiverPatientAssignment.objects.filter(
                caregiver=caregiver,
                is_active=True
            ).values_list('patient_id', flat=True)
            
            # İstatistikleri hesapla
            today = timezone.now().date()
            
            # Bugünkü randevular
            today_appointments = Appointment.objects.filter(
                hasta_id__in=assigned_patients,
                randevu_tarihi__date=today,
                durum__in=['Onaylandi', 'Beklemede']
            ).count()
            
            # Kritik ilaçlar (bugün alınması gereken)
            critical_medications = Ilac.objects.filter(
                hasta_id__in=assigned_patients,
                aktif=True,
                baslangic_tarihi__lte=today
            ).filter(
                Q(bitis_tarihi__isnull=True) | Q(bitis_tarihi__gte=today)
            ).count()
            
            # Acil bildirimler
            urgent_notifications = Bildirim.objects.filter(
                alici=request.user,
                aktif=True,
                okundu=False,
                oncelik='acil'
            ).count()
            
            stats = {
                'totalPatients': len(assigned_patients),
                'todayAppointments': today_appointments,
                'criticalMedications': critical_medications,
                'urgentNotifications': urgent_notifications
            }
            
            return Response(stats)
            
        except Caregiver.DoesNotExist:
            return Response({
                'error': 'Bakıcı profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'İstatistikler getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CaregiverPatientsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Bakıcının atanmış hastalarını listele - Doktor notları ile birlikte"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Aktif hasta atamalarını getir
            assignments = CaregiverPatientAssignment.objects.filter(
                caregiver=caregiver,
                is_active=True
            ).select_related('patient', 'patient__user')
            
            patient_list = []
            
            for assignment in assignments:
                patient = assignment.patient
                
                # Hastanın istatistiklerini hesapla
                today = timezone.now().date()
                
                # Aktif ilaç sayısı
                active_medications = Ilac.objects.filter(
                    hasta=patient,
                    aktif=True,
                    baslangic_tarihi__lte=today
                ).filter(
                    Q(bitis_tarihi__isnull=True) | Q(bitis_tarihi__gte=today)
                ).count()
                
                # Yaklaşan randevu sayısı
                upcoming_appointments = Appointment.objects.filter(
                    hasta=patient,
                    randevu_tarihi__date__gte=today,
                    durum__in=['Onaylandi', 'Beklemede']
                ).count()
                
                # Son randevu bilgisi
                last_appointment = Appointment.objects.filter(
                    hasta=patient
                ).order_by('-randevu_tarihi').first()
                
                # ======= YENİ: Doktor notları - son 30 gün =======
                thirty_days_ago = today - timedelta(days=30)
                recent_doctor_notes = Appointment.objects.filter(
                    hasta=patient,
                    randevu_tarihi__date__gte=thirty_days_ago,
                    doktor_notlari__isnull=False
                ).exclude(doktor_notlari__exact='').order_by('-randevu_tarihi')[:3]
                
                # Son ilaçlar (son 30 gün)
                recent_medications = Ilac.objects.filter(
                    hasta=patient,
                    olusturulma_tarihi__date__gte=thirty_days_ago
                ).order_by('-olusturulma_tarihi')[:3]
                
                # Kritik uyarı sayısı
                critical_alerts = 0
                if active_medications > 5:
                    critical_alerts += 1
                if patient.medical_conditions and ('diyabet' in patient.medical_conditions.lower() or 'hipertansiyon' in patient.medical_conditions.lower()):
                    critical_alerts += 1
                
                # Sağlık durumu (basit bir hesaplama)
                health_status = 'good'  # Default
                if active_medications > 5:
                    health_status = 'fair'
                if critical_alerts > 0:
                    health_status = 'poor'
                if active_medications == 0 and upcoming_appointments == 0:
                    health_status = 'excellent'
                
                # ======= YENİ: Doktor notlarını formatla =======
                formatted_doctor_notes = []
                for note_appointment in recent_doctor_notes:
                    formatted_doctor_notes.append({
                        'date': note_appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                        'doctor_name': note_appointment.doktor.full_name,
                        'doctor_specialty': note_appointment.doktor.uzmanlik,
                        'note': note_appointment.doktor_notlari,
                        'appointment_type': note_appointment.randevu_tipi,
                        'is_urgent': any(word in note_appointment.doktor_notlari.lower() 
                                       for word in ['acil', 'kritik', 'önemli', 'dikkat'])
                    })
                
                # ======= YENİ: Son ilaçları formatla =======
                formatted_recent_medications = []
                for medication in recent_medications:
                    formatted_recent_medications.append({
                        'name': medication.ilac_adi,
                        'dosage': medication.dozaj,
                        'frequency': medication.kullanim_sikligi,
                        'doctor_name': medication.doktor.full_name,
                        'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                        'is_active': medication.aktif
                    })
                
                patient_data = {
                    # Mevcut alanlar (değişmedi)
                    'id': patient.id,
                    'first_name': patient.ad,
                    'last_name': patient.soyad,
                    'age': patient.age,
                    'gender': patient.gender_display if hasattr(patient, 'gender_display') else (patient.cinsiyet or ''),
                    'phone': patient.telefon_no,
                    'address': patient.adres,
                    'blood_type': patient.blood_type if hasattr(patient, 'blood_type') else None,
                    'medical_conditions': patient.medical_conditions if hasattr(patient, 'medical_conditions') else None,
                    'allergies': patient.allergies if hasattr(patient, 'allergies') else None,
                    'emergency_contact_name': patient.acil_durum_kisi,
                    'emergency_contact_phone': patient.acil_durum_telefon,
                    'active_medications': active_medications,
                    'upcoming_appointments': upcoming_appointments,
                    'critical_alerts': critical_alerts,
                    'health_status': health_status,
                    'last_seen': assignment.last_contact_date,
                    'assignment_date': assignment.assigned_date.strftime('%Y-%m-%d'),
                    
                    # ======= YENİ ALANLAR =======
                    'last_appointment': {
                        'date': last_appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M') if last_appointment else None,
                        'doctor_name': last_appointment.doktor.full_name if last_appointment else None,
                        'type': last_appointment.randevu_tipi if last_appointment else None,
                        'status': last_appointment.durum if last_appointment else None
                    },
                    'recent_doctor_notes': formatted_doctor_notes,
                    'recent_medications': formatted_recent_medications,
                    'has_urgent_notes': any(note['is_urgent'] for note in formatted_doctor_notes),
                    'doctor_notes_count': len(formatted_doctor_notes)
                }
                patient_list.append(patient_data)
            
            return Response(patient_list)
            
        except Caregiver.DoesNotExist:
            return Response({
                'error': 'Bakıcı profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Hastalar getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CaregiverProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Bakıcı profil bilgilerini getir"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            serializer = CaregiverSerializer(caregiver)
            return Response(serializer.data)
        except Caregiver.DoesNotExist:
            return Response({
                'error': 'Bakıcı profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request):
        """Bakıcı profil bilgilerini güncelle"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            serializer = CaregiverSerializer(caregiver, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Caregiver.DoesNotExist:
            return Response({
                'error': 'Bakıcı profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)


class CaregiverNotificationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Bakıcının bildirimlerini listele"""
        try:
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
                    'read_date': notification.okunma_tarihi.strftime('%Y-%m-%d %H:%M') if notification.okunma_tarihi else None,
                    'sender_type': notification.gonderen_tip,
                    'is_urgent': notification.oncelik == 'acil',
                    'is_overdue': False  # Bu alan için logic ekleyebilirsiniz
                }
                notification_list.append(notification_data)
            
            return Response(notification_list)
            
        except Exception as e:
            return Response({
                'error': f'Bildirimler getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hastanın detaylarını getir - GÜNCELLEMELER İLE"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            patient = assignment.patient
            today = timezone.now().date()
            
            # ======= YENİ: Hasta için tüm doktor notları (son 90 gün) =======
            ninety_days_ago = today - timedelta(days=90)
            doctor_notes = Appointment.objects.filter(
                hasta=patient,
                randevu_tarihi__date__gte=ninety_days_ago,
                doktor_notlari__isnull=False
            ).exclude(doktor_notlari__exact='').order_by('-randevu_tarihi')
            
            # ======= YENİ: Tüm ilaçları getir (son 90 gün) =======
            all_medications = Ilac.objects.filter(
                hasta=patient,
                olusturulma_tarihi__date__gte=ninety_days_ago
            ).order_by('-olusturulma_tarihi')
            
            # ======= YENİ: Yaklaşan randevular =======
            upcoming_appointments = Appointment.objects.filter(
                hasta=patient,
                randevu_tarihi__date__gte=today,
                durum__in=['Onaylandi', 'Beklemede']
            ).order_by('randevu_tarihi')[:5]
            
            # ======= YENİ: Doktor notlarını formatla =======
            formatted_doctor_notes = []
            for note_appointment in doctor_notes:
                formatted_doctor_notes.append({
                    'id': note_appointment.randevu_id,
                    'date': note_appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M'),
                    'doctor_name': note_appointment.doktor.full_name,
                    'doctor_specialty': note_appointment.doktor.uzmanlik,
                    'note': note_appointment.doktor_notlari,
                    'appointment_type': note_appointment.randevu_tipi,
                    'patient_complaints': note_appointment.hasta_notlari,
                    'is_urgent': any(word in note_appointment.doktor_notlari.lower() 
                                   for word in ['acil', 'kritik', 'önemli', 'dikkat'])
                })
            
            # ======= YENİ: İlaçları formatla =======
            formatted_medications = []
            for medication in all_medications:
                formatted_medications.append({
                    'id': medication.id,
                    'name': medication.ilac_adi,
                    'active_ingredient': medication.etken_madde,
                    'dosage': medication.dozaj,
                    'frequency': medication.kullanim_sikligi,
                    'meal_relation': medication.yemek_iliskisi,
                    'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                    'end_date': medication.bitis_tarihi.strftime('%Y-%m-%d') if medication.bitis_tarihi else None,
                    'doctor_name': medication.doktor.full_name,
                    'instructions': medication.kullanim_talimatlari,
                    'side_effects': getattr(medication, 'yan_etkiler', ''),
                    'warnings': getattr(medication, 'uyarilar', ''),
                    'is_active': medication.aktif,
                    'created_date': medication.olusturulma_tarihi.strftime('%Y-%m-%d')
                })
            
            # ======= YENİ: Yaklaşan randevuları formatla =======
            formatted_appointments = []
            for appointment in upcoming_appointments:
                formatted_appointments.append({
                    'id': appointment.randevu_id,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                    'time': appointment.randevu_tarihi.strftime('%H:%M'),
                    'doctor_name': appointment.doktor.full_name,
                    'doctor_specialty': appointment.doktor.uzmanlik,
                    'type': appointment.randevu_tipi,
                    'status': appointment.durum,
                    'is_online': getattr(appointment, 'online_randevu_mu', False)
                })
            
            # Hasta detaylarını döndür - Mevcut alanlar + yeni alanlar
            patient_data = {
                # Mevcut alanlar (değişmedi)
                'id': patient.id,
                'first_name': patient.ad,
                'last_name': patient.soyad,
                'full_name': patient.full_name,
                'age': patient.age,
                'gender': patient.get_cinsiyet_display() if patient.cinsiyet else 'Belirtilmemiş',
                'phone': patient.telefon_no,
                'email': patient.email,
                'address': patient.adres,
                'birth_date': patient.dogum_tarihi.strftime('%Y-%m-%d') if patient.dogum_tarihi else None,
                'blood_type': patient.blood_type if hasattr(patient, 'blood_type') else None,
                'medical_conditions': patient.medical_conditions if hasattr(patient, 'medical_conditions') else None,
                'allergies': patient.allergies if hasattr(patient, 'allergies') else None,
                'emergency_contact_name': patient.acil_durum_kisi,
                'emergency_contact_phone': patient.acil_durum_telefon,
                'registration_date': patient.kayit_tarihi.strftime('%Y-%m-%d %H:%M'),
                'assignment_date': assignment.assigned_date.strftime('%Y-%m-%d'),
                'last_contact': assignment.last_contact_date.strftime('%Y-%m-%d %H:%M') if assignment.last_contact_date else None,
                
                # ======= YENİ ALANLAR =======
                'doctor_notes': formatted_doctor_notes,
                'medications': formatted_medications,
                'upcoming_appointments': formatted_appointments,
                
                # İstatistikler
                'total_appointments': Appointment.objects.filter(hasta=patient).count(),
                'total_medications': Ilac.objects.filter(hasta=patient).count(),
                'active_medications_count': Ilac.objects.filter(
                    hasta=patient, 
                    aktif=True,
                    baslangic_tarihi__lte=today
                ).filter(
                    Q(bitis_tarihi__isnull=True) | Q(bitis_tarihi__gte=today)
                ).count(),
                'urgent_notes_count': sum(1 for note in formatted_doctor_notes if note['is_urgent'])
            }
            
            return Response(patient_data)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'error': f'Hasta detayları getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientMedicationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hastanın ilaçlarını getir"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            medications = Ilac.objects.filter(hasta=assignment.patient).order_by('-olusturulma_tarihi')
            
            medication_list = []
            for medication in medications:
                medication_data = {
                    'id': medication.id,
                    'name': medication.ilac_adi,
                    'dosage': medication.dozaj,
                    'frequency': medication.kullanim_sikligi,
                    'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                    'end_date': medication.bitis_tarihi.strftime('%Y-%m-%d') if medication.bitis_tarihi else None,
                    'is_active': medication.aktif,
                    'doctor_name': medication.doktor.full_name,
                }
                medication_list.append(medication_data)
            
            return Response(medication_list)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)


class PatientAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hastanın randevularını getir"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            appointments = Appointment.objects.filter(hasta=assignment.patient).order_by('-randevu_tarihi')
            
            appointment_list = []
            for appointment in appointments:
                appointment_data = {
                    'id': appointment.randevu_id,  # Mevcut kod ile uyumlu
                    'doctor_name': appointment.doktor.full_name,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                    'time': appointment.randevu_tarihi.strftime('%H:%M'),
                    'status': appointment.durum,
                    'type': appointment.randevu_tipi,
                }
                appointment_list.append(appointment_data)
            
            return Response(appointment_list)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)


class PatientNotesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hasta hakkındaki notları getir"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            notes = CaregiverNote.objects.filter(
                caregiver=caregiver,
                patient=assignment.patient
            ).order_by('-created_date')
            
            notes_list = []
            for note in notes:
                note_data = {
                    'id': note.id,
                    'note': note.note,
                    'note_type': note.note_type,
                    'is_urgent': note.is_urgent,
                    'created_date': note.created_date.strftime('%Y-%m-%d %H:%M')
                }
                notes_list.append(note_data)
            
            return Response(notes_list)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)
    
    def post(self, request, patient_id):
        """Hasta hakkında yeni not ekle"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            note = CaregiverNote.objects.create(
                caregiver=caregiver,
                patient=assignment.patient,
                note=request.data.get('note'),
                note_type=request.data.get('note_type', 'general'),
                is_urgent=request.data.get('is_urgent', False)
            )
            
            return Response({
                'message': 'Not başarıyla eklendi',
                'note_id': note.id
            }, status=status.HTTP_201_CREATED)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)


class EmergencyAlertView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, patient_id):
        """Acil durum bildirimi gönder"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            patient = assignment.patient
            alert_message = request.data.get('message', '')
            
            # Bildirim oluştur
            Bildirim.objects.create(
                gonderen=request.user,
                gonderen_tip='bakici',
                alici=patient.user,
                alici_tip='hasta',
                bildirim_tipi='acil_durum',
                oncelik='acil',
                baslik='Bakıcınızdan Acil Durum Bildirimi',
                mesaj=f'Bakıcınız {caregiver.full_name} acil durum bildirimi gönderdi: {alert_message}'
            )
            
            return Response({
                'message': 'Acil durum bildirimi gönderildi'
            }, status=status.HTTP_201_CREATED)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)


# ======= YENİ ENDPOINT: Sadece doktor notları =======
class PatientDoctorNotesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hastanın doktor notlarını getir"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            # Query parametreleri
            days_back = int(request.GET.get('days', 90))  # Default 90 gün
            limit = int(request.GET.get('limit', 20))     # Default 20 kayıt
            
            # Belirtilen gün sayısı kadar geriye git
            start_date = timezone.now().date() - timedelta(days=days_back)
            
            doctor_notes = Appointment.objects.filter(
                hasta=assignment.patient,
                randevu_tarihi__date__gte=start_date,
                doktor_notlari__isnull=False
            ).exclude(
                doktor_notlari__exact=''
            ).order_by('-randevu_tarihi')[:limit]
            
            notes_list = []
            for appointment in doctor_notes:
                note_data = {
                    'id': appointment.randevu_id,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M'),
                    'doctor_name': appointment.doktor.full_name,
                    'doctor_specialty': appointment.doktor.uzmanlik,
                    'appointment_type': appointment.randevu_tipi,
                    'doctor_note': appointment.doktor_notlari,
                    'patient_complaint': appointment.hasta_notlari,
                    'appointment_status': appointment.durum,
                    'is_urgent': any(word in appointment.doktor_notlari.lower() 
                                   for word in ['acil', 'kritik', 'önemli', 'dikkat'] 
                                   if appointment.doktor_notlari),
                    'created_date': appointment.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M')
                }
                notes_list.append(note_data)
            
            return Response({
                'patient_id': patient_id,
                'patient_name': assignment.patient.full_name,
                'total_notes': len(notes_list),
                'date_range': f'{start_date} - {timezone.now().date()}',
                'notes': notes_list
            })
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'error': f'Doktor notları getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)# caregivers/views.py - Mevcut view'lara ek olarak aşağıdaki view'ları ekleyin

from django.db.models import Q
from datetime import datetime, timedelta

class CaregiverPatientsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Bakıcının atanmış hastalarını listele - Doktor notları ile birlikte"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Aktif hasta atamalarını getir
            assignments = CaregiverPatientAssignment.objects.filter(
                caregiver=caregiver,
                is_active=True
            ).select_related('patient', 'patient__user')
            
            patient_list = []
            
            for assignment in assignments:
                patient = assignment.patient
                
                # Hastanın istatistiklerini hesapla
                today = timezone.now().date()
                
                # Aktif ilaç sayısı
                active_medications = Ilac.objects.filter(
                    hasta=patient,
                    aktif=True,
                    baslangic_tarihi__lte=today
                ).filter(
                    Q(bitis_tarihi__isnull=True) | Q(bitis_tarihi__gte=today)
                ).count()
                
                # Yaklaşan randevu sayısı
                upcoming_appointments = Appointment.objects.filter(
                    hasta=patient,
                    randevu_tarihi__date__gte=today,
                    durum__in=['Onaylandi', 'Beklemede']
                ).count()
                
                # Son randevu bilgisi
                last_appointment = Appointment.objects.filter(
                    hasta=patient
                ).order_by('-randevu_tarihi').first()
                
                # Doktor notları - son 30 gün içindeki randevu notları
                thirty_days_ago = today - timedelta(days=30)
                doctor_notes = Appointment.objects.filter(
                    hasta=patient,
                    randevu_tarihi__date__gte=thirty_days_ago,
                    doktor_notlari__isnull=False
                ).exclude(doktor_notlari__exact='').order_by('-randevu_tarihi')[:5]
                
                # Hasta için yazılan son ilaçlar (son 30 gün)
                recent_medications = Ilac.objects.filter(
                    hasta=patient,
                    olusturulma_tarihi__date__gte=thirty_days_ago
                ).order_by('-olusturulma_tarihi')[:5]
                
                # Kritik uyarı sayısı (örnek hesaplama)
                critical_alerts = 0
                if active_medications > 5:
                    critical_alerts += 1
                if patient.medical_conditions and ('diyabet' in patient.medical_conditions.lower() or 'hipertansiyon' in patient.medical_conditions.lower()):
                    critical_alerts += 1
                
                # Sağlık durumu (basit bir hesaplama)
                health_status = 'good'  # Default
                if active_medications > 5:
                    health_status = 'fair'
                if critical_alerts > 0:
                    health_status = 'poor'
                if active_medications == 0 and upcoming_appointments == 0:
                    health_status = 'excellent'
                
                # Doktor notlarını düzenle
                formatted_doctor_notes = []
                for note_appointment in doctor_notes:
                    formatted_doctor_notes.append({
                        'date': note_appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                        'doctor_name': note_appointment.doktor.full_name,
                        'note': note_appointment.doktor_notlari,
                        'appointment_type': note_appointment.randevu_tipi
                    })
                
                # Son ilaçları düzenle
                formatted_medications = []
                for medication in recent_medications:
                    formatted_medications.append({
                        'name': medication.ilac_adi,
                        'dosage': medication.dozaj,
                        'frequency': medication.kullanim_sikligi,
                        'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                        'end_date': medication.bitis_tarihi.strftime('%Y-%m-%d') if medication.bitis_tarihi else None,
                        'doctor_name': medication.doktor.full_name,
                        'instructions': medication.kullanim_talimatlari,
                        'is_active': medication.aktif
                    })
                
                patient_data = {
                    'id': patient.id,
                    'first_name': patient.ad,
                    'last_name': patient.soyad,
                    'age': patient.age,
                    'gender': patient.gender_display if hasattr(patient, 'gender_display') else (patient.cinsiyet or ''),
                    'phone': patient.telefon_no,
                    'address': patient.adres,
                    'blood_type': patient.blood_type if hasattr(patient, 'blood_type') else None,
                    'medical_conditions': patient.medical_conditions if hasattr(patient, 'medical_conditions') else None,
                    'allergies': patient.allergies if hasattr(patient, 'allergies') else None,
                    'emergency_contact_name': patient.acil_durum_kisi,
                    'emergency_contact_phone': patient.acil_durum_telefon,
                    'active_medications': active_medications,
                    'upcoming_appointments': upcoming_appointments,
                    'critical_alerts': critical_alerts,
                    'health_status': health_status,
                    'last_seen': assignment.last_contact_date,
                    'assignment_date': assignment.assigned_date.strftime('%Y-%m-%d'),
                    
                    # YENİ: Doktor bilgileri
                    'last_appointment': {
                        'date': last_appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M') if last_appointment else None,
                        'doctor_name': last_appointment.doktor.full_name if last_appointment else None,
                        'type': last_appointment.randevu_tipi if last_appointment else None,
                        'status': last_appointment.durum if last_appointment else None
                    },
                    'doctor_notes': formatted_doctor_notes,
                    'recent_medications': formatted_medications,
                    
                    # Hastanın doktorları (son 6 ay içinde randevusu olan)
                    'doctors': list(Appointment.objects.filter(
                        hasta=patient,
                        randevu_tarihi__date__gte=today - timedelta(days=180)
                    ).values(
                        'doktor__doktor_id',
                        'doktor__ad', 
                        'doktor__soyad',
                        'doktor__uzmanlik',
                        'doktor__telefon_no'
                    ).distinct())
                }
                patient_list.append(patient_data)
            
            return Response(patient_list)
            
        except Caregiver.DoesNotExist:
            return Response({
                'error': 'Bakıcı profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Hastalar getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hastanın detaylarını getir - Doktor notları dahil"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            patient = assignment.patient
            today = timezone.now().date()
            
            # Hasta için tüm doktor notları (son 90 gün)
            ninety_days_ago = today - timedelta(days=90)
            doctor_notes = Appointment.objects.filter(
                hasta=patient,
                randevu_tarihi__date__gte=ninety_days_ago,
                doktor_notlari__isnull=False
            ).exclude(doktor_notlari__exact='').order_by('-randevu_tarihi')
            
            # Tüm ilaçları getir (son 90 gün)
            all_medications = Ilac.objects.filter(
                hasta=patient,
                olusturulma_tarihi__date__gte=ninety_days_ago
            ).order_by('-olusturulma_tarihi')
            
            # Yaklaşan randevular
            upcoming_appointments = Appointment.objects.filter(
                hasta=patient,
                randevu_tarihi__date__gte=today,
                durum__in=['Onaylandi', 'Beklemede']
            ).order_by('randevu_tarihi')[:5]
            
            # Doktor notlarını formatla
            formatted_doctor_notes = []
            for note_appointment in doctor_notes:
                formatted_doctor_notes.append({
                    'id': note_appointment.randevu_id,
                    'date': note_appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M'),
                    'doctor_name': note_appointment.doktor.full_name,
                    'doctor_specialty': note_appointment.doktor.uzmanlik,
                    'note': note_appointment.doktor_notlari,
                    'appointment_type': note_appointment.randevu_tipi,
                    'patient_complaints': note_appointment.hasta_notlari,
                    'is_urgent': 'acil' in note_appointment.doktor_notlari.lower() if note_appointment.doktor_notlari else False
                })
            
            # İlaçları formatla
            formatted_medications = []
            for medication in all_medications:
                formatted_medications.append({
                    'id': medication.id,
                    'name': medication.ilac_adi,
                    'active_ingredient': medication.etken_madde,
                    'dosage': medication.dozaj,
                    'frequency': medication.kullanim_sikligi,
                    'meal_relation': medication.yemek_iliskisi,
                    'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                    'end_date': medication.bitis_tarihi.strftime('%Y-%m-%d') if medication.bitis_tarihi else None,
                    'doctor_name': medication.doktor.full_name,
                    'instructions': medication.kullanim_talimatlari,
                    'side_effects': medication.yan_etkiler if hasattr(medication, 'yan_etkiler') else '',
                    'warnings': medication.uyarilar if hasattr(medication, 'uyarilar') else '',
                    'is_active': medication.aktif,
                    'created_date': medication.olusturulma_tarihi.strftime('%Y-%m-%d')
                })
            
            # Yaklaşan randevuları formatla
            formatted_appointments = []
            for appointment in upcoming_appointments:
                formatted_appointments.append({
                    'id': appointment.randevu_id,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                    'time': appointment.randevu_tarihi.strftime('%H:%M'),
                    'doctor_name': appointment.doktor.full_name,
                    'doctor_specialty': appointment.doktor.uzmanlik,
                    'type': appointment.randevu_tipi,
                    'status': appointment.durum,
                    'is_online': appointment.online_randevu_mu if hasattr(appointment, 'online_randevu_mu') else False
                })
            
            # Hasta detaylarını döndür
            patient_data = {
                'id': patient.id,
                'first_name': patient.ad,
                'last_name': patient.soyad,
                'full_name': patient.full_name,
                'age': patient.age,
                'gender': patient.get_cinsiyet_display() if patient.cinsiyet else 'Belirtilmemiş',
                'phone': patient.telefon_no,
                'email': patient.email,
                'address': patient.adres,
                'birth_date': patient.dogum_tarihi.strftime('%Y-%m-%d') if patient.dogum_tarihi else None,
                'blood_type': patient.blood_type if hasattr(patient, 'blood_type') else None,
                'medical_conditions': patient.medical_conditions if hasattr(patient, 'medical_conditions') else None,
                'allergies': patient.allergies if hasattr(patient, 'allergies') else None,
                'emergency_contact_name': patient.acil_durum_kisi,
                'emergency_contact_phone': patient.acil_durum_telefon,
                'registration_date': patient.kayit_tarihi.strftime('%Y-%m-%d %H:%M'),
                'assignment_date': assignment.assigned_date.strftime('%Y-%m-%d'),
                'last_contact': assignment.last_contact_date.strftime('%Y-%m-%d %H:%M') if assignment.last_contact_date else None,
                
                # Doktor bilgileri
                'doctor_notes': formatted_doctor_notes,
                'medications': formatted_medications,
                'upcoming_appointments': formatted_appointments,
                
                # İstatistikler
                'total_appointments': Appointment.objects.filter(hasta=patient).count(),
                'total_medications': Ilac.objects.filter(hasta=patient).count(),
                'active_medications_count': Ilac.objects.filter(
                    hasta=patient, 
                    aktif=True,
                    baslangic_tarihi__lte=today
                ).filter(
                    Q(bitis_tarihi__isnull=True) | Q(bitis_tarihi__gte=today)
                ).count(),
            }
            
            return Response(patient_data)
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'error': f'Hasta detayları getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientDoctorNotesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, patient_id):
        """Belirli bir hastanın doktor notlarını getir"""
        try:
            caregiver = get_object_or_404(Caregiver, user=request.user)
            
            # Bakıcının bu hastaya erişim yetkisi var mı kontrol et
            assignment = get_object_or_404(
                CaregiverPatientAssignment,
                caregiver=caregiver,
                patient_id=patient_id,
                is_active=True
            )
            
            # Query parametreleri
            days_back = int(request.GET.get('days', 90))  # Default 90 gün
            limit = int(request.GET.get('limit', 20))     # Default 20 kayıt
            
            # Belirtilen gün sayısı kadar geriye git
            start_date = timezone.now().date() - timedelta(days=days_back)
            
            doctor_notes = Appointment.objects.filter(
                hasta=assignment.patient,
                randevu_tarihi__date__gte=start_date,
                doktor_notlari__isnull=False
            ).exclude(
                doktor_notlari__exact=''
            ).order_by('-randevu_tarihi')[:limit]
            
            notes_list = []
            for appointment in doctor_notes:
                note_data = {
                    'id': appointment.randevu_id,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d %H:%M'),
                    'doctor_name': appointment.doktor.full_name,
                    'doctor_specialty': appointment.doktor.uzmanlik,
                    'appointment_type': appointment.randevu_tipi,
                    'doctor_note': appointment.doktor_notlari,
                    'patient_complaint': appointment.hasta_notlari,
                    'appointment_status': appointment.durum,
                    'is_urgent': any(word in appointment.doktor_notlari.lower() 
                                   for word in ['acil', 'kritik', 'önemli', 'dikkat'] 
                                   if appointment.doktor_notlari),
                    'created_date': appointment.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M')
                }
                notes_list.append(note_data)
            
            return Response({
                'patient_id': patient_id,
                'patient_name': assignment.patient.full_name,
                'total_notes': len(notes_list),
                'date_range': f'{start_date} - {timezone.now().date()}',
                'notes': notes_list
            })
            
        except CaregiverPatientAssignment.DoesNotExist:
            return Response({
                'error': 'Bu hastaya erişim yetkiniz bulunmuyor'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'error': f'Doktor notları getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)