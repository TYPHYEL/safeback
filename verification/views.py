import os
import tempfile
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from .services import get_verification_service


@method_decorator(csrf_exempt, name='dispatch')
class VerifyCNIView(APIView):
    """API endpoint for CNI document verification"""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            cni_file = request.FILES.get('cni_photo')
            if not cni_file:
                return Response(
                    {'detail': 'cni_photo file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional expected name for verification
            expected_name = request.data.get('expected_name', '')

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in cni_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Perform verification
                service = get_verification_service()
                result = service.verify_cni_document(temp_path, expected_name if expected_name else None)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Verification failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class VerifyLicensePlateView(APIView):
    """API endpoint for license plate detection and verification"""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            vehicle_file = request.FILES.get('vehicle_photo')
            if not vehicle_file:
                return Response(
                    {'detail': 'vehicle_photo file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional expected plate number
            expected_plate = request.data.get('expected_plate', '')

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in vehicle_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Perform verification
                service = get_verification_service()
                result = service.detect_license_plate(temp_path, expected_plate if expected_plate else None)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Verification failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class VerifyVehicleDocumentView(APIView):
    """API endpoint for vehicle registration document (carte grise) verification"""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            doc_file = request.FILES.get('vehicle_doc')
            if not doc_file:
                return Response(
                    {'detail': 'vehicle_doc file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional expected plate number
            expected_plate = request.data.get('expected_plate', '')

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in doc_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Perform verification
                service = get_verification_service()
                result = service.verify_vehicle_document(temp_path, expected_plate if expected_plate else None)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Verification failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class CheckImageQualityView(APIView):
    """API endpoint for checking image quality"""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'detail': 'image file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in image_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Perform quality check
                service = get_verification_service()
                result = service.check_image_quality(temp_path)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Quality check failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class CompareDocumentsView(APIView):
    """API endpoint for comparing two documents"""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded files
            doc1_file = request.FILES.get('doc1')
            doc2_file = request.FILES.get('doc2')
            
            if not doc1_file or not doc2_file:
                return Response(
                    {'detail': 'Both doc1 and doc2 files are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save uploaded files temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file1:
                for chunk in doc1_file.chunks():
                    temp_file1.write(chunk)
                temp_path1 = temp_file1.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file2:
                for chunk in doc2_file.chunks():
                    temp_file2.write(chunk)
                temp_path2 = temp_file2.name

            try:
                # Perform comparison
                service = get_verification_service()
                result = service.compare_documents(temp_path1, temp_path2)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary files
                if os.path.exists(temp_path1):
                    os.unlink(temp_path1)
                if os.path.exists(temp_path2):
                    os.unlink(temp_path2)

        except Exception as e:
            return Response(
                {'detail': f'Document comparison failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class DetectFaceView(APIView):
    """API endpoint for face detection in profile photos"""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'detail': 'image file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in image_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Perform face detection
                service = get_verification_service()
                result = service.detect_face(temp_path)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Face detection failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class GenerateFaceEmbeddingView(APIView):
    """API endpoint for generating face embeddings"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'detail': 'image file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in image_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Generate face embedding
                service = get_verification_service()
                result = service.generate_face_embedding(temp_path)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Face embedding generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class VerifyFaceMatchView(APIView):
    """API endpoint for verifying if two faces match"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded files
            image1_file = request.FILES.get('image1')
            image2_file = request.FILES.get('image2')
            
            if not image1_file or not image2_file:
                return Response(
                    {'detail': 'Both image1 and image2 files are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional threshold
            threshold = float(request.data.get('threshold', 0.4))

            # Save uploaded files temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file1:
                for chunk in image1_file.chunks():
                    temp_file1.write(chunk)
                temp_path1 = temp_file1.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file2:
                for chunk in image2_file.chunks():
                    temp_file2.write(chunk)
                temp_path2 = temp_file2.name

            try:
                # Verify face match
                service = get_verification_service()
                result = service.verify_face_match(temp_path1, temp_path2, threshold)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary files
                if os.path.exists(temp_path1):
                    os.unlink(temp_path1)
                if os.path.exists(temp_path2):
                    os.unlink(temp_path2)

        except Exception as e:
            return Response(
                {'detail': f'Face verification failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class VerifyFaceWithEmbeddingView(APIView):
    """API endpoint for verifying face against stored embedding"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def options(self, request, *args, **kwargs):
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    def post(self, request):
        try:
            # Get uploaded file
            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'detail': 'image file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get stored embedding from request
            stored_embedding = request.data.get('embedding')
            if not stored_embedding:
                return Response(
                    {'detail': 'embedding is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional threshold
            threshold = float(request.data.get('threshold', 0.4))

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in image_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Verify face with embedding
                service = get_verification_service()
                result = service.verify_face_with_embedding(temp_path, stored_embedding, threshold)

                return Response(result, status=status.HTTP_200_OK)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            return Response(
                {'detail': f'Face verification with embedding failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
