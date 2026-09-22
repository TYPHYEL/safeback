from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import DriverRotation, ShiftHandoff, DriverShiftHistory
from .serializers import DriverRotationSerializer, ShiftHandoffSerializer, DriverShiftHistorySerializer
from .services import verify_handoff_biometric
from users.permissions import IsOwnerOrAdmin


class DriverRotationViewSet(viewsets.ModelViewSet):
    queryset = DriverRotation.objects.all()
    serializer_class = DriverRotationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(driver=user)

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a rotation"""
        rotation = self.get_object()
        rotation.is_active = True
        rotation.save()
        return Response({'detail': 'Rotation activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a rotation"""
        rotation = self.get_object()
        rotation.is_active = False
        rotation.save()
        return Response({'detail': 'Rotation deactivated'})


class ShiftHandoffViewSet(viewsets.ModelViewSet):
    queryset = ShiftHandoff.objects.all()
    serializer_class = ShiftHandoffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(
            outgoing_driver=user
        ) | self.queryset.filter(incoming_driver=user)

    def perform_create(self, serializer):
        serializer.save(outgoing_driver=self.request.user)

    @action(detail=True, methods=['post'])
    def verify_biometric(self, request, pk=None):
        """Verify biometric match for handoff"""
        handoff = self.get_object()
        
        # Check if selfies are provided
        outgoing_selfie = request.FILES.get('outgoing_selfie')
        incoming_selfie = request.FILES.get('incoming_selfie')
        
        if not outgoing_selfie or not incoming_selfie:
            return Response(
                {'error': 'Both outgoing and incoming selfies required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save selfies
        handoff.outgoing_selfie = outgoing_selfie
        handoff.incoming_selfie = incoming_selfie
        handoff.save()
        
        # Verify biometric match
        result = verify_handoff_biometric(handoff)
        
        handoff.biometric_verified = result['match']
        handoff.biometric_match_confidence = result.get('confidence')
        handoff.status = 'in_progress' if result['match'] else 'failed'
        handoff.save()
        
        return Response({
            'verified': result['match'],
            'confidence': result.get('confidence'),
            'reason': result.get('reason')
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete the handoff process"""
        handoff = self.get_object()
        
        if not handoff.biometric_verified:
            return Response(
                {'error': 'Biometric verification required before completion'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update handoff details
        handoff.handoff_time = timezone.now()
        handoff.handoff_location_lat = request.data.get('lat')
        handoff.handoff_location_lng = request.data.get('lng')
        handoff.odometer_reading = request.data.get('odometer')
        handoff.fuel_level = request.data.get('fuel_level')
        handoff.notes = request.data.get('notes', '')
        handoff.status = 'completed'
        handoff.save()
        
        # End outgoing driver's shift
        outgoing_shift = DriverShiftHistory.objects.filter(
            driver=handoff.outgoing_driver,
            taxi=handoff.taxi,
            is_active=True
        ).first()
        
        if outgoing_shift:
            outgoing_shift.shift_end = timezone.now()
            outgoing_shift.is_active = False
            outgoing_shift.ended_cleanly = True
            outgoing_shift.save()
        
        # Start incoming driver's shift
        DriverShiftHistory.objects.create(
            driver=handoff.incoming_driver,
            taxi=handoff.taxi,
            shift_start=timezone.now(),
            is_active=True
        )
        
        return Response({'detail': 'Handoff completed successfully'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel the handoff"""
        handoff = self.get_object()
        handoff.status = 'cancelled'
        handoff.save()
        return Response({'detail': 'Handoff cancelled'})


class DriverShiftHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DriverShiftHistory.objects.all()
    serializer_class = DriverShiftHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(driver=user)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get current active shift for the user"""
        active_shift = self.queryset.filter(
            driver=request.user,
            is_active=True
        ).first()
        
        if active_shift:
            serializer = self.get_serializer(active_shift)
            return Response(serializer.data)
        
        return Response({'detail': 'No active shift'}, status=status.HTTP_404_NOT_FOUND)
