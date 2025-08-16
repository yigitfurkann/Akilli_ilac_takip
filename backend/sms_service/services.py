# sms_service/services.py

import base64
import hashlib
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import json
import logging
import requests

from .models import SMSLog, SMSTemplate, SystemLog

logger = logging.getLogger(__name__)

class HuaweiSMSService:
    """
    Huawei Cloud SMS servisi - circular import düzeltildi
    """
    
    def __init__(self):
        # Settings'den konfigürasyon al
        self.access_key = getattr(settings, 'HUAWEI_ACCESS_KEY', '')
        self.secret_key = getattr(settings, 'HUAWEI_SECRET_KEY', '')
        self.endpoint = getattr(settings, 'HUAWEI_SMS_ENDPOINT', 'https://smsapi.ap-southeast-1.myhuaweicloud.com')
        self.app_key = getattr(settings, 'HUAWEI_SMS_APP_KEY', '')
        self.app_secret = getattr(settings, 'HUAWEI_SMS_APP_SECRET', '')
        self.sender = getattr(settings, 'HUAWEI_SMS_SENDER', 'SMS-INFO')
    
    def _generate_auth_header(self, timestamp):
        """Huawei Cloud WSSE Authentication"""
        try:
            # Nonce oluştur
            nonce = base64.b64encode(timestamp.encode()).decode()
            
            # PasswordDigest hesapla
            password_digest = base64.b64encode(
                hashlib.sha256(
                    (nonce + timestamp + self.app_secret).encode('utf-8')
                ).digest()
            ).decode()
            
            # Headers
            auth_header = 'WSSE realm="SDP",profile="UsernameToken",type="Appkey"'
            x_wsse_header = f'UsernameToken Username="{self.app_key}",PasswordDigest="{password_digest}",Nonce="{nonce}",Created="{timestamp}"'
            
            return auth_header, x_wsse_header
            
        except Exception as e:
            logger.error(f"Auth header hatası: {str(e)}")
            return None, None
    
    def _format_phone_number(self, phone_number):
        """Telefon numarasını uluslararası formata çevir"""
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        
        if clean_phone.startswith('90'):
            return f"+{clean_phone}"
        elif clean_phone.startswith('0'):
            return f"+90{clean_phone[1:]}"
        elif len(clean_phone) == 10:
            return f"+90{clean_phone}"
        else:
            return f"+90{clean_phone}"
    
    def send_sms(self, phone_number, message, template_id=None, user=None, message_type='General'):
        """
        SMS gönder - mevcut SMSLog modeli ile uyumlu
        """
        sms_log = None
        
        try:
            # SMS log kaydı oluştur
            sms_log = SMSLog.objects.create(
                recipient_phone=phone_number,
                recipient_user=user,
                message=message,
                message_type=message_type,
                template_id=template_id,
                status='Pending'
            )
            
            # Telefon numarasını formatla
            formatted_phone = self._format_phone_number(phone_number)
            
            # Timestamp
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Auth headers
            auth_header, x_wsse_header = self._generate_auth_header(timestamp)
            
            if not auth_header or not x_wsse_header:
                raise Exception("Authentication başarısız")
            
            # Request body
            body_data = {
                "from": self.sender,
                "to": [formatted_phone],
                "smsContent": [message],
                "statusCallback": f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/api/sms/callback/"
            }
            
            # Template varsa kullan
            if template_id:
                body_data["templateId"] = template_id
            
            body = json.dumps(body_data)
            
            # Headers
            headers = {
                'Authorization': auth_header,
                'X-WSSE': x_wsse_header,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # API çağrısı
            url = f"{self.endpoint}/sms/batchSendSms/v1"
            
            logger.info(f"SMS gönderiliyor: {formatted_phone}")
            
            response = requests.post(url, headers=headers, data=body, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Message ID'yi al
                message_id = None
                if result.get('result') and len(result['result']) > 0:
                    message_id = result['result'][0].get('msgId')
                
                # SMS log güncelle
                if hasattr(sms_log, 'mark_sent'):
                    sms_log.mark_sent(message_id)
                else:
                    sms_log.status = 'Sent'
                    sms_log.message_id = message_id
                    sms_log.sent_at = timezone.now()
                    sms_log.save()
                
                # System log
                SystemLog.log(
                    level='INFO',
                    category='SMS',
                    message=f'SMS gönderildi: {formatted_phone}',
                    user=user,
                    extra_data={'message_id': message_id}
                )
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'sms_log_id': sms_log.id
                }
            else:
                # Hata durumu
                error_msg = f"HTTP {response.status_code}: {response.text}"
                if hasattr(sms_log, 'mark_failed'):
                    sms_log.mark_failed(error_msg)
                else:
                    sms_log.status = 'Failed'
                    sms_log.error_message = error_msg
                    sms_log.save()
                
                SystemLog.log(
                    level='ERROR',
                    category='SMS',
                    message=f'SMS hatası: {formatted_phone} - {error_msg}',
                    user=user
                )
                
                return {
                    'success': False,
                    'error': error_msg,
                    'sms_log_id': sms_log.id
                }
                
        except Exception as e:
            error_msg = f"SMS servis hatası: {str(e)}"
            
            if sms_log:
                if hasattr(sms_log, 'mark_failed'):
                    sms_log.mark_failed(error_msg)
                else:
                    sms_log.status = 'Failed'
                    sms_log.error_message = error_msg
                    sms_log.save()
            
            SystemLog.log(
                level='ERROR',
                category='SMS',
                message=error_msg,
                user=user
            )
            
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'sms_log_id': sms_log.id if sms_log else None
            }
    
    def send_with_template(self, phone_number, template_name, template_params, user=None):
        """Şablon kullanarak SMS gönder"""
        try:
            template = SMSTemplate.objects.get(name=template_name, is_active=True)
            
            # Template parametrelerini message içine yerleştir
            if hasattr(template, 'format_message'):
                message = template.format_message(*template_params)
            else:
                # Basit string formatting
                message = template.content
                for i, param in enumerate(template_params):
                    message = message.replace(f'{{{i}}}', str(param))
            
            return self.send_sms(
                phone_number=phone_number,
                message=message,
                template_id=getattr(template, 'template_id', None),
                user=user,
                message_type=getattr(template, 'category', 'General')
            )
            
        except SMSTemplate.DoesNotExist:
            # Şablon yoksa düz metin gönder
            message = ' '.join(str(param) for param in template_params)
            return self.send_sms(phone_number, message, user=user)
    
    def send_medication_reminder(self, patient_phone, patient_name, medication_name, time_str, user=None):
        """İlaç hatırlatması gönder"""
        message = f"Sayın {patient_name}, {medication_name} ilacınızı alma zamanı geldi. Saat: {time_str}"
        
        return self.send_sms(
            phone_number=patient_phone,
            message=message,
            user=user,
            message_type='IlacHatirlatma'
        )
    
    def send_appointment_reminder(self, patient_phone, patient_name, doctor_name, appointment_time, user=None):
        """Randevu hatırlatması gönder"""
        message = f"Sayın {patient_name}, Dr. {doctor_name} ile randevunuz {appointment_time} tarihinde."
        
        return self.send_sms(
            phone_number=patient_phone,
            message=message,
            user=user,
            message_type='RandevuHatirlatma'
        )
    
    def send_general_reminder(self, patient_phone, patient_name, reminder_message, user=None):
        """Genel hatırlatma gönder"""
        message = f"Sayın {patient_name}, {reminder_message}"
        
        return self.send_sms(
            phone_number=patient_phone,
            message=message,
            user=user,
            message_type='GenelHatirlatma'
        )

# Singleton instance - CIRCULAR IMPORT HATASI DÜZELTİLDİ
# Artık kendisini import etmiyor
sms_service = HuaweiSMSService()