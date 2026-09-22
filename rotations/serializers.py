from rest_framework import serializers
from .models import DriverRotation, ShiftHandoff, DriverShiftHistory


class DriverRotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverRotation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ShiftHandoffSerializer(serializers.ModelSerializer):
    outgoing_driver_name = serializers.CharField(source='outgoing_driver.username', read_only=True)
    incoming_driver_name = serializers.CharField(source='incoming_driver.username', read_only=True)
    taxi_plate = serializers.CharField(source='taxi.plate_number', read_only=True)
    
    class Meta:
        model = ShiftHandoff
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'biometric_verified', 'biometric_match_confidence']


class DriverShiftHistorySerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.username', read_only=True)
    taxi_plate = serializers.CharField(source='taxi.plate_number', read_only=True)
    
    class Meta:
        model = DriverShiftHistory
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
