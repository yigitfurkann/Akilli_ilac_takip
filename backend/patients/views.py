from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
from .models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from medications.models import Ilac
from notifications.models import Bildirim
from .serializers import PatientSerializer

class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            patient = get_object_or_404(Patient, user=request.user)
            serializer = PatientSerializer(patient)
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Hasta profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request):
        try:
            patient = get_object_or_404(Patient, user=request.user)
            serializer = PatientSerializer(patient, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Hasta profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)

class PatientDoctorsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            doctors = Doctor.objects.filter(is_active=True)
            doctor_list = []
            for doctor in doctors:
                doctor_data = {
                    'id': doctor.doktor_id,
                    'name': doctor.full_name,
                    'specialty': doctor.uzmanlik,
                    'address': doctor.muayenehane_adresi,
                    'phone': doctor.telefon_no,
                    'working_hours': doctor.get_calisma_saatleri(),
                    'diploma_no': doctor.diploma_no
                }
                doctor_list.append(doctor_data)
            return Response(doctor_list)
        except Exception as e:
            return Response({
                'error': f'Doktor listesi getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PatientAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            patient = get_object_or_404(Patient, user=request.user)
            appointments = Appointment.objects.filter(hasta=patient).order_by('-randevu_tarihi')
            appointment_list = []
            for appointment in appointments:
                appointment_data = {
                    'id': appointment.randevu_id,
                    'doctor_name': appointment.doktor.full_name,
                    'doctor_specialty': appointment.doktor.uzmanlik,
                    'date': appointment.randevu_tarihi.strftime('%Y-%m-%d'),
                    'time': appointment.randevu_tarihi.strftime('%H:%M'),
                    'duration': appointment.randevu_suresi,
                    'status': appointment.durum,
                    'type': appointment.randevu_tipi,
                    'patient_notes': appointment.hasta_notlari,
                    'doctor_notes': appointment.doktor_notlari,
                    'is_online': appointment.online_randevu_mu,
                    'can_cancel': appointment.can_be_cancelled,
                    'created_date': appointment.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M')
                }
                appointment_list.append(appointment_data)
            return Response(appointment_list)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Hasta profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Randevular getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        try:
            patient = get_object_or_404(Patient, user=request.user)
            doctor_id = request.data.get('doctor_id')
            if not doctor_id:
                return Response({
                    'error': 'Doktor seçimi gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            doctor = get_object_or_404(Doctor, doktor_id=doctor_id)
            appointment_date_str = request.data.get('appointment_date')
            if not appointment_date_str:
                return Response({
                    'error': 'Randevu tarihi gereklidir'
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                appointment_date = datetime.fromisoformat(appointment_date_str.replace('Z', '+00:00'))
                if appointment_date.tzinfo is None:
                    appointment_date = timezone.make_aware(appointment_date)
            except ValueError as e:
                return Response({
                    'error': f'Geçersiz tarih formatı: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            if appointment_date < timezone.now():
                return Response({
                    'error': 'Geçmiş tarihe randevu oluşturamazsınız'
                }, status=status.HTTP_400_BAD_REQUEST)
            appointment = Appointment.objects.create(
                hasta=patient,
                doktor=doctor,
                randevu_tarihi=appointment_date,
                randevu_suresi=request.data.get('duration', 30),
                randevu_tipi=request.data.get('appointment_type', 'Muayene'),
                hasta_notlari=request.data.get('notes', ''),
                online_randevu_mu=request.data.get('is_online', False)
            )
            Bildirim.objects.create(
                gonderen=request.user,
                gonderen_tip='hasta',
                alici=doctor.user,
                alici_tip='doktor',
                bildirim_tipi='randevu_talebi',
                oncelik='normal',
                baslik='Yeni Randevu Talebi',
                mesaj=f'{patient.full_name} adlı hasta {appointment.randevu_tarihi.strftime("%d.%m.%Y %H:%M")} tarihinde {appointment.randevu_tipi} randevusu talep etti.',
                randevu=appointment
            )
            return Response({
                'message': 'Randevu talebiniz başarıyla gönderildi. Doktor onayından sonra size bildirim gelecektir.',
                'appointment_id': appointment.randevu_id,
                'status': appointment.durum
            }, status=status.HTTP_201_CREATED)
        except Doctor.DoesNotExist:
            return Response({
                'error': 'Seçilen doktor bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Hasta profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Randevu oluşturulamadı: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, appointment_id):
        try:
            patient = get_object_or_404(Patient, user=request.user)
            appointment = get_object_or_404(Appointment, randevu_id=appointment_id, hasta=patient)
            if appointment.cancel():
                Bildirim.objects.create(
                    gonderen=request.user,
                    gonderen_tip='hasta',
                    alici=appointment.doktor.user,
                    alici_tip='doktor',
                    bildirim_tipi='randevu_iptal',
                    baslik='Randevu İptal Edildi',
                    mesaj=f'{patient.full_name} adlı hastanın {appointment.randevu_tarihi.strftime("%d.%m.%Y %H:%M")} tarihli randevusu iptal edildi.',
                    randevu=appointment
                )
                return Response({
                    'message': 'Randevu başarıyla iptal edildi'
                })
            else:
                return Response({
                    'error': 'Randevu iptal edilemedi. Bu randevu iptal edebilir durumda değil.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Appointment.DoesNotExist:
            return Response({
                'error': 'Randevu bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Randevu iptal edilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PatientMedicationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            patient = get_object_or_404(Patient, user=request.user)
            medications = Ilac.objects.filter(hasta=patient).order_by('-olusturulma_tarihi')
            medication_list = []
            for medication in medications:
                medication_data = {
                    'id': medication.id,
                    'name': medication.ilac_adi,
                    'active_ingredient': medication.etken_madde,
                    'dosage': medication.dozaj,
                    'frequency': medication.kullanim_sikligi,
                    'meal_relation': medication.get_yemek_iliskisi_display() if medication.yemek_iliskisi else 'Belirtilmemiş',
                    'start_date': medication.baslangic_tarihi.strftime('%Y-%m-%d'),
                    'end_date': medication.bitis_tarihi.strftime('%Y-%m-%d') if medication.bitis_tarihi else None,
                    'instructions': medication.kullanim_talimatlari,
                    'side_effects': medication.yan_etkiler,
                    'warnings': medication.uyarilar,
                    'is_active': medication.aktif,
                    'is_current': medication.is_current,
                    'is_expired': medication.is_expired,
                    'days_remaining': medication.days_remaining,
                    'doctor_name': medication.doktor.full_name,
                    'created_date': medication.olusturulma_tarihi.strftime('%Y-%m-%d %H:%M')
                }
                medication_list.append(medication_data)
            return Response(medication_list)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Hasta profili bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)

class PatientNotificationsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
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
                    'is_urgent': notification.is_urgent,
                    'is_overdue': notification.is_overdue
                }
                notification_list.append(notification_data)
            return Response(notification_list)
        except Exception as e:
            return Response({
                'error': f'Bildirimler getirilemedi: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, notification_id):
        try:
            notification = get_object_or_404(
                Bildirim, 
                id=notification_id, 
                alici=request.user
            )
            notification.mark_as_read()
            return Response({
                'message': 'Bildirim okundu olarak işaretlendi'
            })
        except Bildirim.DoesNotExist:
            return Response({
                'error': 'Bildirim bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)

# --- CLASS DIŞINA EKLENECEK FONKSİYONLAR ---
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_notifications_statistics(request):
    user = request.user
    total = Bildirim.objects.filter(alici=user, aktif=True).count()
    read = Bildirim.objects.filter(alici=user, aktif=True, okundu=True).count()
    unread = Bildirim.objects.filter(alici=user, aktif=True, okundu=False).count()
    return Response({
        "success": True,
        "statistics": {
            "total": total,
            "read": read,
            "unread": unread
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def patient_notifications_mark_all_read(request):
    user = request.user
    updated = Bildirim.objects.filter(alici=user, aktif=True, okundu=False).update(okundu=True)
    return Response({
        "success": True,
        "message": f"{updated} bildirim okundu olarak işaretlendi."
    })
