from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DriverDocument
from .serializers import DriverDocumentSerializer, DriverDocumentAdminSerializer
from users.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin


class DriverDocumentViewSet(viewsets.ModelViewSet):
    queryset = DriverDocument.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.user and self.request.user.is_staff:
            return DriverDocumentAdminSerializer
        return DriverDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(driver=user)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)

    def get_permissions(self):
        if self.action in ('partial_update', 'update', 'destroy'):
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        doc = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        doc.status = 'approved'
        doc.save()
        # When a driver document is approved, mark their DriverProfile as verified
        try:
            profile = doc.driver.driver_profile
            profile.verified = True
            # store reference to document
            docs = profile.documents or {}
            docs.setdefault('approved_documents', []).append(doc.file.name)
            profile.documents = docs
            profile.save()
        except Exception:
            # ignore if profile missing
            pass
        return Response(DriverDocumentSerializer(doc).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        doc = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        doc.status = 'rejected'
        doc.notes = request.data.get('notes', '')
        doc.save()
        return Response(DriverDocumentSerializer(doc).data)
