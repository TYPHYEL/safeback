import random
import uuid
import string
import logging
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings as django_settings

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.throttling import ScopedRateThrottle
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, DriverProfile, PhoneOTP, EmergencyContact
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    DriverProfileSerializer,
    EmergencyContactSerializer,
    TrustScoreSerializer,
)
from .services import sms_service, validate_cm_phone, normalize_cm_phone

logger = logging.getLogger(__name__)

# Firebase Admin SDK initialization
try:
    import firebase_admin
    from firebase_admin import credentials as fb_credentials, auth
    import os

    # Chemin absolu basé sur l'emplacement de ce fichier (users/views.py)
    # → remonte à backend/ puis cherche dans safetaxi_backend/
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    _BACKEND_DIR = os.path.dirname(_THIS_DIR)
    _DEFAULT_CREDS = os.path.join(_BACKEND_DIR, 'safetaxi_backend', 'firebase-service-account.json')

    firebase_creds_path = os.environ.get('FIREBASE_CREDENTIALS', _DEFAULT_CREDS)

    if not firebase_admin._apps:
        if os.path.exists(firebase_creds_path):
            cred = fb_credentials.Certificate(firebase_creds_path)
            firebase_admin.initialize_app(cred)
            print(f"Firebase Admin SDK initialized: {firebase_creds_path}")
        else:
            print(f"Firebase credentials not found at: {firebase_creds_path}")
except Exception as e:
    print(f"Firebase initialization error: {e}")


def generate_unique_qr_code():
    """Generate a unique QR code for a driver"""
    # Generate a unique 16-character alphanumeric code
    chars = string.ascii_uppercase + string.digits
    while True:
        qr_code = ''.join(random.choices(chars, k=16))
        # Check if this QR code already exists
        if not DriverProfile.objects.filter(qr_code=qr_code).exists():
            return qr_code


class RegisterView(viewsets.GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class SendOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_send'

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        phone = ''
        if isinstance(request.data, dict):
            phone = request.data.get('phone', '').strip()
        elif isinstance(request.data, (int, str)):
            phone = str(request.data).strip()
        else:
            return Response({'detail': 'Invalid data format'}, status=status.HTTP_400_BAD_REQUEST)

        if not phone:
            return Response({'detail': 'phone is required'}, status=status.HTTP_400_BAD_REQUEST)

        phone = normalize_cm_phone(phone)
        if not validate_cm_phone(phone):
            return Response(
                {'detail': 'Format de numero invalide. Utilisez le format +237 suivi de 9 chiffres (ex: +237612345678)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = str(random.randint(100000, 999999)).zfill(6)
        otp, _ = PhoneOTP.objects.update_or_create(
            phone=phone,
            defaults={'code': code, 'created_at': timezone.now(), 'is_verified': False},
        )

        sms_sent = False
        if not django_settings.DEBUG and sms_service.is_configured():
            sms_sent = sms_service.send_otp_sms(phone, code)

        res_data = {'detail': 'OTP sent', 'sms_sent': sms_sent}
        if django_settings.DEBUG or not sms_sent:
            res_data['code'] = code
        return Response(res_data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyOtpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp_verify'

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        code = request.data.get('code', '').strip()
        if not phone or not code:
            return Response({'detail': 'phone and code are required'}, status=status.HTTP_400_BAD_REQUEST)

        otp = PhoneOTP.objects.filter(phone=phone, code=code).first()
        if not otp:
            return Response({'detail': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        elapsed = timezone.now() - otp.created_at
        if elapsed.total_seconds() > 900:
            return Response({'detail': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_verified = True
        otp.save()

        user, created = CustomUser.objects.get_or_create(
            username=phone,
            defaults={'role': 'passenger', 'is_active': True},
        )

        first_name = (request.data.get('first_name') or '').strip()
        last_name = (request.data.get('last_name') or '').strip()
        email = (request.data.get('email') or '').strip()
        role_raw = (request.data.get('role') or '').strip()
        password = (request.data.get('password') or '').strip()
        birth_date_str = (request.data.get('birth_date') or '').strip()
        gender = (request.data.get('gender') or '').strip()
        VALID_ROLES = {'passenger', 'driver', 'owner', 'admin'}
        role = role_raw if role_raw in VALID_ROLES else None

        fields_to_update = []
        if first_name and (created or not user.first_name):
            user.first_name = first_name
            fields_to_update.append('first_name')
        if last_name and (created or not user.last_name):
            user.last_name = last_name
            fields_to_update.append('last_name')
        if email and (created or not user.email):
            user.email = email
            fields_to_update.append('email')
        if role and (created or user.role == 'passenger'):
            user.role = role
            fields_to_update.append('role')
        if password and created:
            user.set_password(password)
            fields_to_update.append('password')
        if fields_to_update:
            user.save(update_fields=fields_to_update)

        # Handle driver registration with photos
        if user.role == 'driver':
            driver_profile, created = DriverProfile.objects.get_or_create(user=user)
            
            # Generate unique QR code if not already set
            if not driver_profile.qr_code:
                driver_profile.qr_code = generate_unique_qr_code()
            
            # Handle license photo upload
            license_photo = request.FILES.get('license_photo')
            if license_photo:
                driver_profile.license_photo = license_photo
                driver_profile.license_number = license_photo.name
            
            # Handle vehicle photo upload
            vehicle_photo = request.FILES.get('vehicle_photo')
            if vehicle_photo:
                driver_profile.vehicle_photo = vehicle_photo
            
            # Handle CNI photo upload
            cni_photo = request.FILES.get('cni_photo')
            if cni_photo:
                driver_profile.cni_photo = cni_photo
            
            # Handle profile photo upload
            profile_photo = request.FILES.get('profile_photo')
            if profile_photo:
                driver_profile.profile_photo = profile_photo
                
                # Generate face embedding from profile photo
                try:
                    from verification.services import get_verification_service
                    import tempfile
                    import os
                    
                    # Save profile photo temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        for chunk in profile_photo.chunks():
                            temp_file.write(chunk)
                        temp_path = temp_file.name
                    
                    try:
                        service = get_verification_service()
                        embedding_result = service.generate_face_embedding(temp_path)
                        
                        if embedding_result.get('valid') and embedding_result.get('embedding'):
                            driver_profile.face_embedding = embedding_result['embedding']
                            logger.info(f"Face embedding generated for driver {user.username}")
                        else:
                            logger.warning(f"Failed to generate face embedding for driver {user.username}: {embedding_result.get('error')}")
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error generating face embedding: {e}")
            
            # Handle birth date
            if birth_date_str:
                from datetime import datetime
                try:
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                    driver_profile.birth_date = birth_date
                except ValueError:
                    pass  # Invalid date format, skip
            
            driver_profile.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class FirebaseLoginView(APIView):
    permission_classes = [AllowAny]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        firebase_token = request.data.get('firebase_token')
        phone = request.data.get('phone')

        if not firebase_token or not phone:
            return Response(
                {'detail': 'firebase_token and phone are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Données d'inscription optionnelles (présentes uniquement au premier enregistrement)
        first_name = (request.data.get('first_name') or '').strip()
        last_name  = (request.data.get('last_name')  or '').strip()
        email      = (request.data.get('email')      or '').strip()
        role_raw   = (request.data.get('role')       or 'passenger').strip()

        # Valider le rôle pour éviter toute injection
        VALID_ROLES = {'passenger', 'driver', 'owner', 'admin'}
        role = role_raw if role_raw in VALID_ROLES else 'passenger'

        try:
            # Vérifier si Firebase Admin est initialisé
            if not firebase_admin._apps:
                return Response(
                    {'detail': 'Firebase not configured on server. Add firebase-service-account.json.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Vérifier le token Firebase
            decoded_token = auth.verify_id_token(firebase_token)
            firebase_phone = decoded_token.get('phone_number')

            if firebase_phone != phone:
                return Response(
                    {'detail': 'Phone number mismatch between token and request'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Créer ou récupérer l'utilisateur
            user, created = CustomUser.objects.get_or_create(
                username=phone,
                defaults={
                    'is_active': True,
                    'first_name': first_name,
                    'last_name':  last_name,
                    'role':       role,
                    **(({'email': email}) if email else {}),
                },
            )

            # Si l'utilisateur existait déjà mais que des champs sont vides,
            # mettre à jour avec les données fournies (sans écraser les données existantes)
            if not created:
                fields_to_update = []
                if first_name and not user.first_name:
                    user.first_name = first_name
                    fields_to_update.append('first_name')
                if last_name and not user.last_name:
                    user.last_name = last_name
                    fields_to_update.append('last_name')
                if email and not user.email:
                    user.email = email
                    fields_to_update.append('email')
                # Le rôle n'est mis à jour que si l'utilisateur n'a pas encore de rôle spécifique
                if role != 'passenger' and user.role == 'passenger':
                    user.role = role
                    fields_to_update.append('role')
                if fields_to_update:
                    user.save(update_fields=fields_to_update)

            # Créer le profil chauffeur si nécessaire
            if user.role == 'driver':
                driver_profile, created = DriverProfile.objects.get_or_create(user=user)
                
                # Generate unique QR code if not already set
                if not driver_profile.qr_code:
                    driver_profile.qr_code = generate_unique_qr_code()
                    driver_profile.save()

            # Générer les tokens JWT
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    'access':  str(refresh.access_token),
                    'refresh': str(refresh),
                    'user':    UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {'detail': f'Firebase verification failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        for field in ('first_name', 'last_name', 'email'):
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response(UserSerializer(user).data)


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        return ProfileView().patch(request)

    def put(self, request):
        return ProfileView().patch(request)


class TrustScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from ratings.utils import calculate_trust_score
        result = calculate_trust_score(request.user)
        serializer = TrustScoreSerializer(result)
        return Response(serializer.data)


class FCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from notifications.models import Device
        token = request.data.get('token', '').strip()
        platform = request.data.get('platform', '').strip() or 'unknown'
        if not token:
            return Response({'detail': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)
        device, created = Device.objects.update_or_create(
            user=request.user,
            token=token,
            defaults={'platform': platform},
        )
        return Response(
            {'detail': 'FCM token registered', 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class EmergencyContactViewSet(viewsets.ModelViewSet):
    queryset = EmergencyContact.objects.all()
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or self.action in ('approve_driver', 'reject_driver', 'dashboard'):
            return self.queryset
        return self.queryset.filter(id=user.id)

    def get_permissions(self):
        if self.action in ('approve_driver', 'reject_driver', 'dashboard'):
            return [IsAuthenticated(), IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        user = self.get_object()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def approve_driver(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        try:
            profile = user.driver_profile
            profile.verified = True
            profile.save()
            return Response({'detail': 'Driver approved'})
        except DriverProfile.DoesNotExist:
            return Response({'detail': 'Driver profile not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def suspend(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'detail': 'User suspended'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def reject_driver(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        try:
            profile = user.driver_profile
            profile.verified = False
            profile.save()
            return Response({'detail': 'Driver rejected'})
        except DriverProfile.DoesNotExist:
            return Response({'detail': 'Driver profile not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def dashboard(self, request):
        from django.db.models import Count, Q
        from taxis.models import Taxi
        from trips.models import Trip
        from sos.models import Incident
        stats = {
            'total_taxis': Taxi.objects.count(),
            'total_drivers': DriverProfile.objects.count(),
            'total_passengers': CustomUser.objects.filter(role='passenger').count(),
            'active_trips': Trip.objects.filter(status='active').count(),
            'pending_drivers': DriverProfile.objects.filter(verified=False).count(),
            'sos_alerts': Incident.objects.count(),
        }
        return Response(stats)


class DriverProfileViewSet(viewsets.ModelViewSet):
    queryset = DriverProfile.objects.all()
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new driver profile"""
        from .serializers import DriverProfileSerializer
        serializer = DriverProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, created = DriverProfile.objects.update_or_create(
            user=request.user,
            defaults=serializer.validated_data,
        )
        response_serializer = DriverProfileSerializer(profile)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate driver shift"""
        profile = self.get_object()
        profile.is_active = True
        profile.save(update_fields=['is_active'])
        return Response({'detail': 'Driver activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate driver shift"""
        profile = self.get_object()
        profile.is_active = False
        profile.save(update_fields=['is_active'])
        return Response({'detail': 'Driver deactivated'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def pending(self, request):
        """Get pending drivers for admin approval"""
        pending = self.queryset.filter(verified=False)
        serializer = DriverProfileSerializer(pending, many=True)
        return Response(serializer.data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'token blacklisted'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'invalid token'}, status=status.HTTP_400_BAD_REQUEST)
