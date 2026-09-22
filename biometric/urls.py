from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import BiometricRequestViewSet, verify_face_direct

router = DefaultRouter()
router.register(r'biometric', BiometricRequestViewSet)

urlpatterns = router.urls + [
    path('biometric/verify/', verify_face_direct, name='verify_face_direct'),
]
