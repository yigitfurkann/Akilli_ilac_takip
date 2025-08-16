# accounts/views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, PatientRegisterSerializer
from patients.models import Patient

User = get_user_model()

# Kullanıcı tiplerini role stringlerine eşleyen bir sözlük - GÜNCELLENDİ
role_map = {
    'ADMIN': 'admin',
    'DOKTOR': 'doktor',
    'HEMSIRE': 'hemsire', 
    'HASTA': 'hasta',
    # YENİ: Mevcut sistemdeki user_type değerlerini de destekle
    'Hasta': 'hasta',
    'Doktor': 'doktor',
    'Bakici': 'bakici',
}

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        requested_user_type = request.data.get('user_type')  # FE'den gelsin
        
        if not username or not password:
            return Response({'error': 'Kullanıcı adı ve şifre gereklidir.'}, status=400)
        
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({'error': 'Geçersiz kullanıcı adı veya şifre.'}, status=401)
        
        # DEBUGGING: User type kontrolü
        print(f"🔍 LOGIN DEBUG:")
        print(f"User: {user.username}")
        print(f"User.user_type: {user.user_type}")
        print(f"Requested user_type: {requested_user_type}")
        
        # Kullanıcı tipi eşleşmesi ek kontrol - GÜNCELLENDİ
        if requested_user_type:
            # Frontend'den gelen role'ü büyük harfe çevir
            requested_role = requested_user_type.lower()
            # Backend'deki role'ü belirle
            user_role = role_map.get(user.user_type, user.user_type.lower())
            
            print(f"User role (mapped): {user_role}")
            print(f"Requested role: {requested_role}")
            
            if user_role != requested_role:
                return Response({
                    'error': f'Seçilen kullanıcı tipiyle eşleşmiyor! Bu kullanıcı "{user.user_type}" tipindedir.'
                }, status=403)
        
        if not user.is_active:
            return Response({'error': 'Hesabınız aktif değil.'}, status=401)
        
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # User data oluştururken role mapping'i düzgün yap
        user_role = role_map.get(user.user_type, user.user_type.lower())
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user_role,  # Doğru mapping
            'user_type': user.user_type,  # Orijinali de gönder
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        print(f"🎯 Final user_data: {user_data}")
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': user_data
        }, status=200)

class PatientRegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PatientRegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # JWT token oluştur
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                # Role mapping
                user_role = role_map.get(user.user_type, user.user_type.lower())
                
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user_role,  # Düzeltildi
                    'user_type': user.user_type,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
                
                return Response({
                    'message': 'Hasta kaydı başarıyla oluşturuldu.',
                    'access': str(access_token),
                    'refresh': str(refresh),
                    'user': user_data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Kayıt sırasında hata oluştu: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Role mapping
        user_role = role_map.get(user.user_type, user.user_type.lower())
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
            'role': user_role,  # Frontend için role
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
        
        return Response(user_data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Başarıyla çıkış yapıldı.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Çıkış sırasında hata oluştu.'
            }, status=status.HTTP_400_BAD_REQUEST)