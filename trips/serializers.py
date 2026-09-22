from rest_framework import serializers
from decimal import Decimal
from .models import Trip, Deposit


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['id', 'taxi', 'driver', 'passengers', 'status', 'join_code', 'start_lat', 'start_lng', 'current_lat', 'current_lng', 'started_at', 'ended_at', 'created_at']
        read_only_fields = ['driver', 'status', 'join_code', 'started_at', 'ended_at', 'created_at']


class DepositSerializer(serializers.ModelSerializer):
    passenger_name = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()
    driver_trust_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Deposit
        fields = [
            'id', 'passenger', 'passenger_name', 'driver', 'driver_name', 'taxi',
            'status', 'pickup_location', 'pickup_lat', 'pickup_lng',
            'dropoff_location', 'dropoff_lat', 'dropoff_lng',
            'distance_km', 'fare', 'is_night',
            'pickup_time', 'started_at', 'completed_at', 'created_at', 'expires_at',
            'driver_trust_score'
        ]
        read_only_fields = ['id', 'driver', 'taxi', 'status', 'started_at', 'completed_at', 'created_at', 'expires_at', 'driver_trust_score']
    
    def get_passenger_name(self, obj):
        return f"{obj.passenger.first_name} {obj.passenger.last_name}".strip() or obj.passenger.username
    
    def get_driver_name(self, obj):
        if obj.driver:
            return f"{obj.driver.first_name} {obj.driver.last_name}".strip() or obj.driver.username
        return None
    
    def get_driver_trust_score(self, obj):
        if obj.driver:
            # Try to get trust score from driver profile
            from users.models import DriverProfile
            try:
                profile = DriverProfile.objects.get(user=obj.driver)
                return 5.0  # Default trust score, can be enhanced
            except DriverProfile.DoesNotExist:
                return 5.0
        return None


class DepositCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une demande de dépôt"""
    
    # Convertir les floats en Decimal pour les champs DecimalField
    pickup_lat = serializers.FloatField()
    pickup_lng = serializers.FloatField()
    dropoff_lat = serializers.FloatField()
    dropoff_lng = serializers.FloatField()
    distance_km = serializers.FloatField()
    fare = serializers.FloatField()
    
    class Meta:
        model = Deposit
        fields = [
            'pickup_location', 'pickup_lat', 'pickup_lng',
            'dropoff_location', 'dropoff_lat', 'dropoff_lng',
            'distance_km', 'fare', 'is_night'
        ]
    
    def validate_fare(self, value):
        """Valider que le prix respecte les minimums"""
        is_night = self.initial_data.get('is_night', False)
        min_fare = 4000 if is_night else 3000
        if value < min_fare:
            raise serializers.ValidationError(f"Le prix minimum est de {min_fare} FCFA")
        return value
    
    def to_internal_value(self, data):
        """Convertir les floats en Decimal pour le modèle"""
        data = super().to_internal_value(data)
        # Convertir les floats en Decimal
        for field in ['pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng', 'distance_km', 'fare']:
            if field in data and isinstance(data[field], float):
                data[field] = Decimal(str(data[field]))
        return data
