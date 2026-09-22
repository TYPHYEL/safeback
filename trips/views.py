from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import Trip, Deposit
from .serializers import TripSerializer, DepositSerializer, DepositCreateSerializer
from users.permissions import IsDriver, IsOwnerOrAdmin
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import random
import string
from notifications.models import Device
from notifications import services as notify_service
from django.utils import timezone
from django.db.models import Q
from math import radians, sin, cos, sqrt, atan2


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if getattr(user, 'role', None) == 'driver':
            return self.queryset.filter(driver=user)
        return self.queryset.filter(passengers=user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsDriver()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def _generate_join_code(self, length=6):
        for _ in range(20):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if not Trip.objects.filter(join_code=code).exists():
                return code
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user, join_code=self._generate_join_code())

    def _join_trip(self, trip, user):
        if not trip:
            return Response({'detail': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
        if user == trip.driver:
            return Response({'detail': 'Driver cannot join as passenger'}, status=status.HTTP_400_BAD_REQUEST)
        if trip.passengers.filter(id=user.id).exists():
            return Response(TripSerializer(trip).data)
        taxi = trip.taxi
        if taxi and taxi.capacity is not None and trip.passengers.count() >= taxi.capacity:
            return Response({'detail': 'Trip is full'}, status=status.HTTP_400_BAD_REQUEST)
        trip.passengers.add(user)
        trip.save()
        return Response(TripSerializer(trip).data)

    @action(detail=False, methods=['post'])
    def join_by_code(self, request):
        code = request.data.get('join_code')
        if not code:
            return Response({'detail': 'join_code required'}, status=status.HTTP_400_BAD_REQUEST)
        trip = get_object_or_404(Trip, join_code=code, status='pending')
        return self._join_trip(trip, request.user)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        trip = get_object_or_404(Trip, pk=pk, status='pending')
        return self._join_trip(trip, request.user)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        trip = self.get_object()
        user = request.user
        trip.passengers.remove(user)
        trip.save()
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        trip = self.get_object()
        if request.user != trip.driver:
            return Response({'detail': 'Only driver can start the trip'}, status=status.HTTP_403_FORBIDDEN)
        if trip.status != 'pending':
            return Response({'detail': 'Trip cannot be started'}, status=status.HTTP_400_BAD_REQUEST)
        trip.status = 'active'
        import django.utils.timezone as tz
        trip.started_at = tz.now()
        trip.save()
        try:
            passenger_qs = trip.passengers.all()
            tokens = list(Device.objects.filter(user__in=passenger_qs).values_list('token', flat=True))
            if tokens:
                title = 'Trip started'
                body = f'Driver {trip.driver.username} a démarré le trajet.'
                notify_service.send_multicast(tokens, title, body, data={'trip_id': str(trip.id)})
        except Exception:
            pass
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        trip = self.get_object()
        if request.user != trip.driver:
            return Response({'detail': 'Only driver can end the trip'}, status=status.HTTP_403_FORBIDDEN)
        if trip.status != 'active':
            return Response({'detail': 'Trip cannot be ended'}, status=status.HTTP_400_BAD_REQUEST)
        trip.status = 'completed'
        import django.utils.timezone as tz
        trip.ended_at = tz.now()
        trip.save()
        return Response(TripSerializer(trip).data)

    @action(detail=True, methods=['post'])
    def location(self, request, pk=None):
        trip = self.get_object()
        if request.user != trip.driver:
            return Response({'detail': 'Only driver can update location'}, status=status.HTTP_403_FORBIDDEN)
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        payload = {'lat': lat, 'lng': lng, 'trip_id': trip.id}
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(f'trip_{trip.id}', {'type': 'location.message', 'payload': payload})
        if lat is not None and lng is not None:
            trip.current_lat = lat
            trip.current_lng = lng
            trip.save()
        return Response({'detail': 'location broadcasted'})

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get trip history for current user"""
        user = request.user
        from django.db.models import Q
        trips = self.queryset.filter(Q(driver=user) | Q(passengers=user)).order_by('-created_at')
        page = int(request.query_params.get('page', 1))
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        serializer = TripSerializer(trips[start:end], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active trip for current user"""
        user = request.user
        if getattr(user, 'role', None) == 'driver':
            trip = self.queryset.filter(driver=user, status='active').first()
        else:
            trip = self.queryset.filter(passengers=user, status='active').first()
        if trip:
            return Response(TripSerializer(trip).data)
        return Response({})

    @action(detail=True, methods=['get'])
    def passengers(self, request, pk=None):
        """Get passengers list for a trip"""
        trip = self.get_object()
        from users.serializers import UserSerializer
        serializer = UserSerializer(trip.passengers.all(), many=True)
        return Response(serializer.data)


class DepositViewSet(viewsets.ModelViewSet):
    queryset = Deposit.objects.all()
    serializer_class = DepositSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if getattr(user, 'role', None) == 'driver':
            return self.queryset.filter(driver=user)
        return self.queryset.filter(passenger=user)
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]  # Passagers peuvent créer des dépôts
        if self.action in ('accept', 'reject'):
            return [IsDriver()]
        return [IsAuthenticated()]
    
    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculer la distance en km entre deux points (formule Haversine)"""
        R = 6371  # Rayon de la Terre en km
        
        lat1_rad = radians(float(lat1))
        lat2_rad = radians(float(lat2))
        lng1_rad = radians(float(lng1))
        lng2_rad = radians(float(lng2))
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _calculate_fare(self, distance_km, is_night=False):
        """Calculer le prix en fonction de la distance et du tarif"""
        # Tarif de base: 3000 FCFA jour, 4000 FCFA nuit
        base_fare = 4000 if is_night else 3000
        
        # Tarif par km: 200 FCFA/km jour, 250 FCFA/km nuit
        per_km = 250 if is_night else 200
        
        # Calcul du prix
        fare = base_fare + (distance_km * per_km)
        
        return max(fare, base_fare)  # Minimum le tarif de base
    
    def _is_night_time(self):
        """Déterminer si c'est l'heure de nuit (18h - 6h)"""
        now = timezone.now()
        hour = now.hour
        return hour >= 18 or hour < 6
    
    @action(detail=False, methods=['post'])
    def calculate_fare(self, request):
        """Calculer le prix pour un dépôt"""
        pickup_lat = request.data.get('pickup_lat')
        pickup_lng = request.data.get('pickup_lng')
        dropoff_lat = request.data.get('dropoff_lat')
        dropoff_lng = request.data.get('dropoff_lng')
        
        if not all([pickup_lat, pickup_lng, dropoff_lat, dropoff_lng]):
            return Response(
                {'detail': 'pickup_lat, pickup_lng, dropoff_lat, dropoff_lng are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculer la distance
        distance_km = self._calculate_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        
        # Déterminer si c'est la nuit
        is_night = self._is_night_time()
        
        # Calculer le prix
        fare = self._calculate_fare(distance_km, is_night)
        
        return Response({
            'distance_km': round(distance_km, 2),
            'fare': round(fare, 2),
            'is_night': is_night,
            'min_fare': 4000 if is_night else 3000
        })
    
    @action(detail=False, methods=['post'])
    def create_deposit(self, request):
        """Créer une demande de dépôt"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Deposit request data: {request.data}")
        
        serializer = DepositCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Deposit validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le dépôt
        deposit = Deposit.objects.create(
            passenger=request.user,
            pickup_location=serializer.validated_data['pickup_location'],
            pickup_lat=serializer.validated_data['pickup_lat'],
            pickup_lng=serializer.validated_data['pickup_lng'],
            dropoff_location=serializer.validated_data['dropoff_location'],
            dropoff_lat=serializer.validated_data['dropoff_lat'],
            dropoff_lng=serializer.validated_data['dropoff_lng'],
            distance_km=serializer.validated_data['distance_km'],
            fare=serializer.validated_data['fare'],
            is_night=serializer.validated_data['is_night'],
            status='pending',
            expires_at=timezone.now() + timezone.timedelta(minutes=5)  # Expire après 5 minutes
        )
        
        # Trouver le chauffeur le plus proche
        nearest_driver = self._find_nearest_driver(deposit)
        
        if nearest_driver:
            # Proposer au chauffeur
            deposit.driver = nearest_driver
            deposit.status = 'offered'
            deposit.save()
            
            # Notifier le chauffeur
            try:
                driver_tokens = list(Device.objects.filter(user=nearest_driver).values_list('token', flat=True))
                if driver_tokens:
                    title = 'Nouvelle demande de dépôt'
                    body = f'Course privée: {deposit.pickup_location} → {deposit.dropoff_location} - {deposit.fare} FCFA'
                    notify_service.send_multicast(
                        driver_tokens, 
                        title, 
                        body, 
                        data={'deposit_id': str(deposit.id), 'type': 'deposit_request'}
                    )
            except Exception as e:
                pass  # Continuer même si la notification échoue
        else:
            # Aucun chauffeur trouvé, marquer comme expiré
            deposit.status = 'expired'
            deposit.save()
        
        return Response(DepositSerializer(deposit).data)
    
    def _find_nearest_driver(self, deposit):
        """Trouver le chauffeur le plus proche à vide"""
        from users.models import DriverProfile
        
        # Récupérer tous les chauffeurs actifs sans trajet en cours
        active_drivers = DriverProfile.objects.filter(
            is_active=True,
            user__role='driver'
        ).select_related('user')
        
        # Filtrer les chauffeurs qui n'ont pas de trajet actif
        available_drivers = []
        for driver_profile in active_drivers:
            # Vérifier si le chauffeur a un dépôt ou trajet actif
            has_active_trip = Trip.objects.filter(
                driver=driver_profile.user,
                status__in=['pending', 'active']
            ).exists()
            
            has_active_deposit = Deposit.objects.filter(
                driver=driver_profile.user,
                status__in=['offered', 'accepted', 'active']
            ).exists()
            
            if not has_active_trip and not has_active_deposit:
                available_drivers.append(driver_profile)
        
        if not available_drivers:
            return None
        
        # Trouver le chauffeur le plus proche
        # Pour l'instant, on utilise une position fictive du chauffeur
        # Dans une vraie application, il faudrait stocker la position en temps réel
        nearest_driver = None
        min_distance = float('inf')
        
        for driver_profile in available_drivers:
            # Position fictive du chauffeur (à remplacer par position réelle)
            # Pour la démo, on utilise une position aléatoire proche de Yaoundé
            driver_lat = 3.8480 + (hash(driver_profile.user.id) % 100) / 10000
            driver_lng = 11.5021 + (hash(driver_profile.user.id) % 100) / 10000
            
            distance = self._calculate_distance(
                driver_lat, driver_lng,
                deposit.pickup_lat, deposit.pickup_lng
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_driver = driver_profile.user
        
        return nearest_driver
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accepter une demande de dépôt (chauffeur)"""
        deposit = self.get_object()
        
        if request.user != deposit.driver:
            return Response(
                {'detail': 'Only the assigned driver can accept this deposit'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if deposit.status != 'offered':
            return Response(
                {'detail': 'Deposit cannot be accepted in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if deposit.is_expired():
            deposit.status = 'expired'
            deposit.save()
            return Response(
                {'detail': 'Deposit has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Accepter le dépôt
        deposit.status = 'accepted'
        deposit.driver_trust_score = 5.0  # Score par défaut
        deposit.save()
        
        # Notifier le passager
        try:
            passenger_tokens = list(Device.objects.filter(user=deposit.passenger).values_list('token', flat=True))
            if passenger_tokens:
                title = 'Dépôt accepté'
                body = f'Votre course privée a été acceptée par {deposit.driver.username}'
                notify_service.send_multicast(
                    passenger_tokens,
                    title,
                    body,
                    data={'deposit_id': str(deposit.id), 'type': 'deposit_accepted'}
                )
        except Exception:
            pass
        
        return Response(DepositSerializer(deposit).data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Refuser une demande de dépôt (chauffeur)"""
        deposit = self.get_object()
        
        if request.user != deposit.driver:
            return Response(
                {'detail': 'Only the assigned driver can reject this deposit'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if deposit.status != 'offered':
            return Response(
                {'detail': 'Deposit cannot be rejected in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Réinitialiser et trouver un autre chauffeur
        deposit.driver = None
        deposit.status = 'pending'
        deposit.save()
        
        # Essayer de trouver un autre chauffeur
        nearest_driver = self._find_nearest_driver(deposit)
        if nearest_driver:
            deposit.driver = nearest_driver
            deposit.status = 'offered'
            deposit.save()
            
            # Notifier le nouveau chauffeur
            try:
                driver_tokens = list(Device.objects.filter(user=nearest_driver).values_list('token', flat=True))
                if driver_tokens:
                    title = 'Nouvelle demande de dépôt'
                    body = f'Course privée: {deposit.pickup_location} → {deposit.dropoff_location} - {deposit.fare} FCFA'
                    notify_service.send_multicast(
                        driver_tokens,
                        title,
                        body,
                        data={'deposit_id': str(deposit.id), 'type': 'deposit_request'}
                    )
            except Exception:
                pass
        else:
            deposit.status = 'expired'
            deposit.save()
            
            # Notifier le passager qu'aucun chauffeur n'est disponible
            try:
                passenger_tokens = list(Device.objects.filter(user=deposit.passenger).values_list('token', flat=True))
                if passenger_tokens:
                    title = 'Dépôt expiré'
                    body = 'Aucun chauffeur disponible pour votre course privée'
                    notify_service.send_multicast(
                        passenger_tokens,
                        title,
                        body,
                        data={'deposit_id': str(deposit.id), 'type': 'deposit_expired'}
                    )
            except Exception:
                pass
        
        return Response(DepositSerializer(deposit).data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Démarrer un dépôt (chauffeur)"""
        deposit = self.get_object()
        
        if request.user != deposit.driver:
            return Response(
                {'detail': 'Only the assigned driver can start this deposit'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if deposit.status != 'accepted':
            return Response(
                {'detail': 'Deposit cannot be started in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deposit.status = 'active'
        deposit.started_at = timezone.now()
        deposit.save()
        
        # Notifier le passager
        try:
            passenger_tokens = list(Device.objects.filter(user=deposit.passenger).values_list('token', flat=True))
            if passenger_tokens:
                title = 'Dépôt démarré'
                body = f'Votre chauffeur {deposit.driver.username} a démarré la course'
                notify_service.send_multicast(
                    passenger_tokens,
                    title,
                    body,
                    data={'deposit_id': str(deposit.id), 'type': 'deposit_started'}
                )
        except Exception:
            pass
        
        return Response(DepositSerializer(deposit).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Terminer un dépôt (chauffeur)"""
        deposit = self.get_object()
        
        if request.user != deposit.driver:
            return Response(
                {'detail': 'Only the assigned driver can complete this deposit'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if deposit.status != 'active':
            return Response(
                {'detail': 'Deposit cannot be completed in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deposit.status = 'completed'
        deposit.completed_at = timezone.now()
        deposit.save()
        
        # Notifier le passager
        try:
            passenger_tokens = list(Device.objects.filter(user=deposit.passenger).values_list('token', flat=True))
            if passenger_tokens:
                title = 'Dépôt terminé'
                body = f'Votre course privée est terminée. Prix: {deposit.fare} FCFA'
                notify_service.send_multicast(
                    passenger_tokens,
                    title,
                    body,
                    data={'deposit_id': str(deposit.id), 'type': 'deposit_completed'}
                )
        except Exception:
            pass
        
        return Response(DepositSerializer(deposit).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler un dépôt (passager)"""
        deposit = self.get_object()
        
        if request.user != deposit.passenger:
            return Response(
                {'detail': 'Only the passenger can cancel this deposit'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if deposit.status in ['completed', 'cancelled']:
            return Response(
                {'detail': 'Deposit cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deposit.status = 'cancelled'
        deposit.save()
        
        # Notifier le chauffeur si assigné
        if deposit.driver:
            try:
                driver_tokens = list(Device.objects.filter(user=deposit.driver).values_list('token', flat=True))
                if driver_tokens:
                    title = 'Dépôt annulé'
                    body = 'Le passager a annulé la course privée'
                    notify_service.send_multicast(
                        driver_tokens,
                        title,
                        body,
                        data={'deposit_id': str(deposit.id), 'type': 'deposit_cancelled'}
                    )
            except Exception:
                pass
        
        return Response(DepositSerializer(deposit).data)
