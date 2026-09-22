from rest_framework.routers import DefaultRouter
from .views import DriverRotationViewSet, ShiftHandoffViewSet, DriverShiftHistoryViewSet

router = DefaultRouter()
router.register(r'rotations', DriverRotationViewSet, basename='rotation')
router.register(r'handoffs', ShiftHandoffViewSet, basename='handoff')
router.register(r'shift-history', DriverShiftHistoryViewSet, basename='shift-history')

urlpatterns = router.urls
