from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Incident
from .serializers import IncidentSerializer, IncidentListSerializer, SosAlertSerializer


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'active' or self.action == 'my':
            return IncidentListSerializer
        return IncidentSerializer

    def get_permissions(self):
        if self.action in ('list', 'active', 'resolve', 'bulk_resolve'):
            return [IsAdminUser()]
        if self.action in ('create', 'report', 'my', 'retrieve'):
            return [IsAuthenticated()]
        if self.action in ('partial_update', 'update'):
            return [IsAdminUser()]
        if self.action == 'destroy':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Incident.objects.select_related('user', 'resolved_by', 'trip').all()
        user = self.request.user
        if user.is_staff:
            if self.action == 'active':
                return qs.filter(status='open')
            return qs
        else:
            return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance

        if instance.alert_type:
            try:
                from .tasks import process_sos_alert
                process_sos_alert.delay(instance.id)
            except (ImportError, Exception):
                pass

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if 'status' in request.data and not request.user.is_staff:
            return Response(
                {'detail': "Seul un administrateur peut modifier le statut."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request, pk=None):
        queryset = self.get_queryset().filter(status='open')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my')
    def my(self, request, pk=None):
        queryset = Incident.objects.filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        incident = self.get_object()
        if incident.status == 'resolved':
            return Response(
                {'detail': 'Cet incident est déjà résolu.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        incident.status = 'resolved'
        incident.resolved_at = timezone.now()
        incident.resolved_by = request.user
        incident.save()

        try:
            from .tasks import notify_incident_resolved
            notify_incident_resolved.delay(incident.id)
        except (ImportError, Exception):
            pass

        serializer = self.get_serializer(incident)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='report')
    def report(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='trigger')
    def trigger(self, request):
        sos_serializer = SosAlertSerializer(data=request.data)
        sos_serializer.is_valid(raise_exception=True)
        data = sos_serializer.validated_data

        incident_data = {
            'alert_type': data['alert_type'],
            'lat': data['lat'],
            'lng': data['lng'],
            'description': data.get('description', ''),
        }
        if data.get('accuracy') is not None:
            incident_data['accuracy'] = data['accuracy']
        if data.get('trip_id'):
            incident_data['trip_id'] = data['trip_id']

        serializer = IncidentSerializer(data=incident_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance

        try:
            from .tasks import process_sos_alert
            process_sos_alert.delay(instance.id)
        except (ImportError, Exception):
            pass

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
