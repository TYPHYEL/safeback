from math import asin, cos, radians, sin, sqrt
from datetime import datetime, date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from users.permissions import IsDriverOrOwner, IsOwnerOrAdmin
from users.serializers import UserSerializer

from .models import Taxi
from .serializers import TaxiSerializer
import time

User = get_user_model()


class TaxiViewSet(viewsets.ModelViewSet):
    queryset = Taxi.objects.all()
    serializer_class = TaxiSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsDriverOrOwner()]
        if self.action in ('update', 'partial_update', 'destroy', 'assign_driver'):
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def _distance_km(self, lat1, lng1, lat2, lng2):
        lat1_rad, lng1_rad = radians(lat1), radians(lng1)
        lat2_rad, lng2_rad = radians(lat2), radians(lng2)
        dlon = lng2_rad - lng1_rad
        dlat = lat2_rad - lat1_rad
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return 6371 * c

    def _send_driver_notification(self, driver, taxi, shift_start=None, shift_end=None):
        try:
            from notifications.services import send_multicast
            from notifications.models import Device
            tokens = list(
                Device.objects.filter(user=driver).values_list('token', flat=True)
            )
            title = 'Nouvelle affectation de taxi'
            body = f"Vous avez été affecté au taxi {taxi.plate_number}."
            if shift_start and shift_end:
                body += f" Shift: {shift_start} - {shift_end}"
            send_multicast(tokens, title, body, {
                'type': 'taxi_assigned',
                'taxi_id': str(taxi.id),
                'plate_number': taxi.plate_number,
            })
        except (ImportError, Exception):
            pass

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        taxi = self.get_object()
        taxi.is_active = False
        taxi.save()
        return Response({'detail': 'Taxi suspended'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        taxi = self.get_object()
        taxi.is_active = True
        taxi.save()
        return Response({'detail': 'Taxi activated'})

    @extend_schema(
        summary='Lister les taxis proches',
        description='Retourne les taxis actifs dans un rayon donné autour des coordonnées fournies.',
        parameters=[
            OpenApiParameter(name='lat', type=float, required=True, description='Latitude de référence'),
            OpenApiParameter(name='lng', type=float, required=True, description='Longitude de référence'),
            OpenApiParameter(name='radius', type=float, required=False, description='Rayon en kilomètres'),
        ],
        responses={200: TaxiSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get taxis nearby based on lat/lng and radius"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')

        if not lat or not lng:
            return Response({'detail': 'lat and lng required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat)
            lng = float(lng)
            radius = float(request.query_params.get('radius', 2.0))
        except ValueError:
            return Response({'detail': 'Invalid lat/lng or radius'}, status=status.HTTP_400_BAD_REQUEST)

        if radius <= 0 or radius > 50:
            return Response(
                {'detail': 'radius must be between 0 and 50 km'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lat_delta = radius / 111.0
        lng_delta = radius / (111.0 * max(cos(radians(lat)), 0.1))

        candidates = Taxi.objects.filter(
            is_active=True,
            last_lat__gte=lat - lat_delta,
            last_lat__lte=lat + lat_delta,
            last_lng__gte=lng - lng_delta,
            last_lng__lte=lng + lng_delta,
        )

        nearby_taxis = []
        for taxi in candidates:
            if taxi.last_lat is None or taxi.last_lng is None:
                continue
            km = self._distance_km(lat, lng, float(taxi.last_lat), float(taxi.last_lng))
            if km <= radius:
                nearby_taxis.append((km, taxi))

        nearby_taxis.sort(key=lambda item: item[0])
        taxis = [taxi for _, taxi in nearby_taxis]
        serializer = TaxiSerializer(taxis, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def qrcode(self, request, pk=None):
        """Generate QR code data for taxi"""
        taxi = self.get_object()
        qr_data = f"safetaxi:{pk}:{int(time.time())}"
        return Response({'qr_data': qr_data, 'taxi_id': pk})

    @action(detail=True, methods=['get'], url_path='drivers')
    def drivers(self, request, pk=None):
        """Get list of drivers associated with this taxi via rotations or active driver"""
        taxi = self.get_object()
        driver_ids = set()
        drivers_list = []

        try:
            from rotations.models import DriverRotation
            rotations = DriverRotation.objects.filter(taxi=taxi, is_active=True).select_related('driver')
            for rot in rotations:
                if rot.driver_id and rot.driver_id not in driver_ids:
                    driver_ids.add(rot.driver_id)
                    drivers_list.append(rot.driver)
        except ImportError:
            pass

        if not drivers_list:
            if taxi.active_driver and taxi.active_driver_id not in driver_ids:
                drivers_list.append(taxi.active_driver)
            if taxi.owner and taxi.owner_id not in driver_ids:
                if taxi.owner.role == 'driver':
                    drivers_list.append(taxi.owner)

        serializer = UserSerializer(drivers_list, many=True)
        return Response({
            'taxi_id': taxi.id,
            'drivers': serializer.data,
            'count': len(drivers_list),
        })

    @action(detail=True, methods=['post'], url_path='assign-driver')
    def assign_driver(self, request, pk=None):
        """Assign a driver to the taxi, optionally creating a rotation entry"""
        taxi = self.get_object()
        driver_id = request.data.get('driver_id')
        shift_start = request.data.get('shift_start')
        shift_end = request.data.get('shift_end')

        if not driver_id:
            return Response(
                {'detail': 'driver_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            driver = User.objects.get(pk=driver_id)
        except User.DoesNotExist:
            return Response(
                {'detail': "Chauffeur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if driver.role not in ('driver', 'owner', 'admin'):
            return Response(
                {'detail': "L'utilisateur n'est pas un chauffeur."},
                status=status.HTTP_400_BAD_REQUEST
            )

        rotation_created = False
        try:
            from rotations.models import DriverRotation
            rotation_kwargs = {
                'taxi': taxi,
                'driver': driver,
                'is_active': True,
            }
            if shift_start:
                try:
                    if isinstance(shift_start, str) and len(shift_start) <= 8:
                        rotation_kwargs['start_time'] = datetime.strptime(shift_start, '%H:%M').time()
                    else:
                        rotation_kwargs['start_time'] = datetime.strptime(shift_start, '%H:%M:%S').time()
                except (ValueError, TypeError):
                    rotation_kwargs['start_time'] = datetime.now().time()
            else:
                rotation_kwargs['start_time'] = datetime.now().time()

            if shift_end:
                try:
                    if isinstance(shift_end, str) and len(shift_end) <= 8:
                        rotation_kwargs['end_time'] = datetime.strptime(shift_end, '%H:%M').time()
                    else:
                        rotation_kwargs['end_time'] = datetime.strptime(shift_end, '%H:%M:%S').time()
                except (ValueError, TypeError):
                    end = datetime.now()
                    end = end.replace(hour=23, minute=59, second=0)
                    rotation_kwargs['end_time'] = end.time()
            else:
                end = datetime.now()
                end = end.replace(hour=23, minute=59, second=0)
                rotation_kwargs['end_time'] = end.time()

            rotation_kwargs.setdefault('shift_type', 'full')
            rotation_kwargs.setdefault('days_of_week', list(range(1, 8)))

            DriverRotation.objects.create(**rotation_kwargs)
            rotation_created = True
        except ImportError:
            pass

        taxi.active_driver = driver
        taxi.save()

        self._send_driver_notification(driver, taxi, shift_start, shift_end)

        result = {
            'detail': 'Chauffeur affecté avec succès.',
            'taxi_id': taxi.id,
            'driver_id': driver.id,
            'driver_username': driver.username,
            'active_driver_updated': True,
            'rotation_created': rotation_created,
        }
        if shift_start:
            result['shift_start'] = shift_start
        if shift_end:
            result['shift_end'] = shift_end

        return Response(result, status=status.HTTP_200_OK)
