from rest_framework.routers import DefaultRouter
from .views import DocumentValidationViewSet

router = DefaultRouter()
router.register(r'document-validation', DocumentValidationViewSet, basename='document-validation')

urlpatterns = router.urls
