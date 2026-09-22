from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import OCRService
import os
import tempfile

class DocumentValidationViewSet(viewsets.ViewSet):
    permission_classes = []  # Allow access during registration
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ocr_service = OCRService()
    
    @action(detail=False, methods=['post'])
    def validate_cni(self, request):
        """Validate CNI document and extract information"""
        cni_photo = request.FILES.get('cni_photo')
        
        if not cni_photo:
            return Response(
                {'detail': 'CNI photo is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            for chunk in cni_photo.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # Extract text using OCR
            text = self.ocr_service.extract_text_from_image(temp_path)
            
            if not text:
                return Response(
                    {'detail': 'Unable to extract text from CNI photo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse CNI information
            cni_info = self.ocr_service.parse_cni_info(text)
            
            return Response({
                'success': True,
                'extracted_text': text,
                'parsed_info': cni_info
            })
        except Exception as e:
            return Response(
                {'detail': f'Error processing CNI: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @action(detail=False, methods=['post'])
    def validate_license(self, request):
        """Validate driver license document and extract information"""
        license_photo = request.FILES.get('license_photo')
        
        if not license_photo:
            return Response(
                {'detail': 'License photo is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            for chunk in license_photo.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # Extract text using OCR
            text = self.ocr_service.extract_text_from_image(temp_path)
            
            if not text:
                return Response(
                    {'detail': 'Unable to extract text from license photo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse license information
            license_info = self.ocr_service.parse_license_info(text)
            
            return Response({
                'success': True,
                'extracted_text': text,
                'parsed_info': license_info
            })
        except Exception as e:
            return Response(
                {'detail': f'Error processing license: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @action(detail=False, methods=['post'])
    def validate_vehicle(self, request):
        """Validate vehicle photo for license plate visibility"""
        vehicle_photo = request.FILES.get('vehicle_photo')
        
        if not vehicle_photo:
            return Response(
                {'detail': 'Vehicle photo is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            for chunk in vehicle_photo.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # Validate vehicle photo
            validation_result = self.ocr_service.validate_vehicle_photo(temp_path)
            
            return Response({
                'success': True,
                'validation': validation_result
            })
        except Exception as e:
            return Response(
                {'detail': f'Error processing vehicle photo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @action(detail=False, methods=['post'])
    def validate_registration(self, request):
        """Validate vehicle registration (carte grise) and compare plate number."""
        registration_photo = request.FILES.get('registration_photo')
        expected_plate = request.data.get('plate_number')

        if not registration_photo:
            return Response(
                {'detail': 'Registration photo is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not expected_plate:
            return Response(
                {'detail': 'Plate number is required for validation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            for chunk in registration_photo.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        try:
            text = self.ocr_service.extract_text_from_image(temp_path)
            if not text:
                return Response(
                    {'detail': 'Unable to extract text from registration photo'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            plate, confidence = self.ocr_service.detect_license_plate(text)
            matched = False
            if plate:
                actual_plate = plate.replace(' ', '').upper()
                expected = expected_plate.replace(' ', '').upper()
                matched = actual_plate == expected

            return Response({
                'success': True,
                'extracted_text': text,
                'registration_plate': plate,
                'confidence': confidence,
                'expected_plate': expected_plate,
                'plate_match': matched,
              'message': 'Plaque correspondante' if matched else 'Plaque ne correspond pas à la carte grise',
            })
        except Exception as e:
            return Response(
                {'detail': f'Error processing registration: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @action(detail=False, methods=['post'])
    def compare_documents(self, request):
        """Compare CNI and license information"""
        cni_photo = request.FILES.get('cni_photo')
        license_photo = request.FILES.get('license_photo')
        
        if not cni_photo or not license_photo:
            return Response(
                {'detail': 'Both CNI and license photos are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save uploaded files temporarily
        cni_temp = None
        license_temp = None
        
        try:
            # Save CNI photo
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in cni_photo.chunks():
                    temp_file.write(chunk)
                cni_temp = temp_file.name
            
            # Save license photo
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                for chunk in license_photo.chunks():
                    temp_file.write(chunk)
                license_temp = temp_file.name
            
            # Extract and parse CNI info
            cni_text = self.ocr_service.extract_text_from_image(cni_temp)
            cni_info = self.ocr_service.parse_cni_info(cni_text) if cni_text else {}
            
            # Extract and parse license info
            license_text = self.ocr_service.extract_text_from_image(license_temp)
            license_info = self.ocr_service.parse_license_info(license_text) if license_text else {}
            
            # Compare documents
            comparison = self.ocr_service.compare_documents(cni_info, license_info, {})
            
            return Response({
                'success': True,
                'cni_info': cni_info,
                'license_info': license_info,
                'comparison': comparison
            })
        except Exception as e:
            return Response(
                {'detail': f'Error comparing documents: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temporary files
            if cni_temp and os.path.exists(cni_temp):
                os.unlink(cni_temp)
            if license_temp and os.path.exists(license_temp):
                os.unlink(license_temp)
