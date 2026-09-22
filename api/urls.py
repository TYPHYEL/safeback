from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    RegisterView,
    DriverProfileViewSet,
    LogoutView,
    SendOtpView,
    VerifyOtpView,
    ProfileView,
)
from users.views import (
    FirebaseLoginView,
    EmergencyContactViewSet,
    TrustScoreView,
    FCMTokenView,
    ProfileUpdateView,
)
from taxis.views import TaxiViewSet
from trips.views import TripViewSet, DepositViewSet
from sos.views import IncidentViewSet
from documents.views import DriverDocumentViewSet
from ratings.views import RatingViewSet
from biometric.views import BiometricRequestViewSet
from notifications.views import DeviceViewSet
from rotations.views import DriverRotationViewSet
from ai.views import AIViewSet
from ocr.views import DocumentValidationViewSet
from verification.urls import urlpatterns as verification_urls
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'drivers', DriverProfileViewSet)
router.register(r'taxis', TaxiViewSet)
router.register(r'trips', TripViewSet)
router.register(r'deposits', DepositViewSet)
router.register(r'incidents', IncidentViewSet)
router.register(r'driver-docs', DriverDocumentViewSet)
router.register(r'ratings', RatingViewSet)
router.register(r'biometric', BiometricRequestViewSet)
router.register(r'devices', DeviceViewSet)
router.register(r'rotations', DriverRotationViewSet)
router.register(r'ai', AIViewSet, basename='ai')
router.register(r'document-validation', DocumentValidationViewSet, basename='document-validation')
router.register(r'emergency-contacts', EmergencyContactViewSet, basename='api-emergency-contact')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', RegisterView.as_view({'post': 'register'}), name='auth-register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('auth/firebase/login/', FirebaseLoginView.as_view(), name='auth-firebase-login'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/otp/send/', SendOtpView.as_view(), name='auth-otp-send'),
    path('auth/otp/verify/', VerifyOtpView.as_view(), name='auth-otp-verify'),
    path('auth/profile/', ProfileView.as_view(), name='auth-profile'),
    path('auth/profile/update/', ProfileUpdateView.as_view(), name='auth-profile-update'),
    path('auth/profile/fcm-token/', FCMTokenView.as_view(), name='auth-fcm-token'),
    path('auth/trust-score/', TrustScoreView.as_view(), name='auth-trust-score'),
    # Verification endpoints
    path('verification/', include((verification_urls, 'verification'), namespace='verification')),
    # Alias pour compatibilité frontend
    path('sos/alert/', IncidentViewSet.as_view({'post': 'create'}), name='sos-alert'),
    path('sos/trigger/', IncidentViewSet.as_view({'post': 'trigger'}), name='sos-trigger'),
    path('sos/active/', IncidentViewSet.as_view({'get': 'active'}), name='sos-active'),
    path('sos/my/', IncidentViewSet.as_view({'get': 'my'}), name='sos-my'),
    path('sos/report/', IncidentViewSet.as_view({'post': 'report'}), name='sos-report'),
    path('sos/<str:pk>/resolve/', IncidentViewSet.as_view({'post': 'resolve'}), name='sos-resolve'),
    # Trip start endpoint for frontend compatibility
    path('trips/start/', TripViewSet.as_view({'post': 'create'}), name='trips-start'),
    # Admin endpoints
    path('admin/drivers/pending/', DriverProfileViewSet.as_view({'get': 'pending'}), name='admin-pending-drivers'),
    path('admin/drivers/<str:pk>/approve/', UserViewSet.as_view({'post': 'approve_driver'}), name='admin-approve-driver'),
    path('admin/drivers/<str:pk>/reject/', UserViewSet.as_view({'post': 'reject_driver'}), name='admin-reject-driver'),
    path('admin/dashboard/', UserViewSet.as_view({'get': 'dashboard'}), name='admin-dashboard'),
]
