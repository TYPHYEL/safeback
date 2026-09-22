from rest_framework.routers import DefaultRouter
from .views import DriverDocumentViewSet

router = DefaultRouter()
router.register(r'driver-docs', DriverDocumentViewSet)

urlpatterns = router.urls
