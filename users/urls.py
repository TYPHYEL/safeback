from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    RegisterView,
    DriverProfileViewSet,
    EmergencyContactViewSet,
    SendOtpView,
    VerifyOtpView,
    ProfileView,
    ProfileUpdateView,
    TrustScoreView,
    FCMTokenView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import LogoutView
from users.views import FirebaseLoginView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'drivers', DriverProfileViewSet)
router.register(r'emergency-contacts', EmergencyContactViewSet, basename='emergency-contact')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', RegisterView.as_view({'post': 'register'}), name='auth-register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/otp/send/', SendOtpView.as_view(), name='auth-otp-send'),
    path('auth/otp/verify/', VerifyOtpView.as_view(), name='auth-otp-verify'),
    path('auth/profile/', ProfileView.as_view(), name='auth-profile'),
    path('auth/profile/update/', ProfileUpdateView.as_view(), name='auth-profile-update'),
    path('auth/profile/fcm-token/', FCMTokenView.as_view(), name='auth-fcm-token'),
    path('auth/trust-score/', TrustScoreView.as_view(), name='auth-trust-score'),
    path('auth/firebase/login/', FirebaseLoginView.as_view(), name='auth-firebase-login'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
]
