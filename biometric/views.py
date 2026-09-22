from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.conf import settings
from django.db import close_old_connections, transaction
from .models import BiometricRequest
from .serializers import BiometricRequestSerializer
from .services import verify_face
from threading import Thread
import sys
import tempfile
import os
from users.permissions import IsAdminOrReadOnly


class BiometricRequestViewSet(viewsets.ModelViewSet):
    queryset = BiometricRequest.objects.all()
    serializer_class = BiometricRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(driver=user)

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy', 'verify'):
            return [IsAdminOrReadOnly()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        obj = serializer.save()

        def process_biometric(obj_id):
            try:
                close_old_connections()
                br = BiometricRequest.objects.get(id=obj_id)
                br.status = 'processing'
                br.save()
                selfie_path = br.selfie.path if br.selfie else None
                reference_path = br.reference.path if br.reference else None
                result = verify_face(selfie_path, reference_path)
                br.result = result
                br.status = 'verified' if result.get('match') else 'failed'
                br.save()
                if result.get('match'):
                    try:
                        profile = br.driver.driver_profile
                        profile.verified = True
                        profile.save()
                    except Exception:
                        pass
            except BiometricRequest.DoesNotExist:
                return
            finally:
                close_old_connections()

        run_async = not (
            'test' in sys.argv
            or settings.DATABASES['default']['ENGINE'].endswith('sqlite3')
        )
        if run_async:
            transaction.on_commit(
                lambda: Thread(
                    target=process_biometric,
                    args=(obj.id,),
                    daemon=True,
                ).start()
            )
        else:
            process_biometric(obj.id)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'processing'
        obj.save()
        selfie_path = obj.selfie.path if obj.selfie else None
        reference_path = obj.reference.path if obj.reference else None
        result = verify_face(selfie_path, reference_path)
        obj.result = result
        obj.status = 'verified' if result.get('match') else 'failed'
        obj.save()
        if result.get('match'):
            try:
                profile = obj.driver.driver_profile
                profile.verified = True
                profile.save()
            except Exception:
                pass
        return Response(BiometricRequestSerializer(obj).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_face_direct(request):
    """Direct face verification endpoint for real-time verification.
    
    Expects multipart/form-data with:
    - selfie: image file
    - reference: image file (optional)
    
    Returns:
    - match: bool
    - confidence: float
    - reason: str
    """
    selfie_file = request.FILES.get('selfie')
    reference_file = request.FILES.get('reference')
    
    if not selfie_file:
        return Response(
            {'match': False, 'confidence': 0.0, 'reason': 'No selfie provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Save uploaded files to temp directory
    temp_dir = tempfile.gettempdir()
    selfie_path = os.path.join(temp_dir, f'selfie_{request.user.id}.jpg')
    reference_path = None
    
    try:
        # Save selfie
        with open(selfie_path, 'wb') as f:
            for chunk in selfie_file.chunks():
                f.write(chunk)
        
        # Save reference if provided
        if reference_file:
            reference_path = os.path.join(temp_dir, f'reference_{request.user.id}.jpg')
            with open(reference_path, 'wb') as f:
                for chunk in reference_file.chunks():
                    f.write(chunk)
        
        # Verify faces
        result = verify_face(selfie_path, reference_path)
        
        return Response(result)
        
    except Exception as e:
        return Response(
            {'match': False, 'confidence': 0.0, 'reason': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # Clean up temp files
        try:
            if os.path.exists(selfie_path):
                os.remove(selfie_path)
            if reference_path and os.path.exists(reference_path):
                os.remove(reference_path)
        except Exception:
            pass
