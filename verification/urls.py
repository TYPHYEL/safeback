from django.urls import path
from .views import (
    VerifyCNIView,
    VerifyLicensePlateView,
    VerifyVehicleDocumentView,
    CheckImageQualityView,
    CompareDocumentsView,
    DetectFaceView,
    GenerateFaceEmbeddingView,
    VerifyFaceMatchView,
    VerifyFaceWithEmbeddingView
)

app_name = 'verification'

urlpatterns = [
    path('verify-cni/', VerifyCNIView.as_view(), name='verify_cni'),
    path('verify-license-plate/', VerifyLicensePlateView.as_view(), name='verify_license_plate'),
    path('verify-vehicle-doc/', VerifyVehicleDocumentView.as_view(), name='verify_vehicle_doc'),
    path('check-quality/', CheckImageQualityView.as_view(), name='check_quality'),
    path('compare-documents/', CompareDocumentsView.as_view(), name='compare_documents'),
    path('detect-face/', DetectFaceView.as_view(), name='detect_face'),
    path('generate-face-embedding/', GenerateFaceEmbeddingView.as_view(), name='generate_face_embedding'),
    path('verify-face-match/', VerifyFaceMatchView.as_view(), name='verify_face_match'),
    path('verify-face-embedding/', VerifyFaceWithEmbeddingView.as_view(), name='verify_face_embedding'),
]
