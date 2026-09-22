from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Incident
from trips.models import Trip

User = get_user_model()


class IncidentSerializer(serializers.ModelSerializer):
    resolved_by_username = serializers.SerializerMethodField(read_only=True)
    trip_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    resolution = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id',
            'user',
            'alert_type',
            'lat',
            'lng',
            'accuracy',
            'description',
            'status',
            'trip',
            'trip_id',
            'created_at',
            'resolved_at',
            'resolved_by',
            'resolved_by_username',
            'resolution',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'resolved_at', 'resolved_by', 'trip']

    def get_resolved_by_username(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.username
        return None

    def get_resolution(self, obj):
        if obj.status == 'resolved':
            return {
                'resolved': True,
                'resolved_at': obj.resolved_at,
                'resolved_by': obj.resolved_by.id if obj.resolved_by else None,
                'resolved_by_username': self.get_resolved_by_username(obj),
            }
        return {'resolved': False}

    def validate(self, attrs):
        if self.instance is None:
            has_alert = attrs.get('alert_type')
            has_desc = attrs.get('description')
            has_lat_lng = attrs.get('lat') and attrs.get('lng')
            if not has_alert and not has_desc and not has_lat_lng:
                raise serializers.ValidationError({
                    'detail': 'Au moins un des champs alert_type, description ou coordonnées (lat/lng) est requis.'
                })
        return attrs

    def create(self, validated_data):
        trip_id = validated_data.pop('trip_id', None)
        if trip_id:
            try:
                validated_data['trip'] = Trip.objects.get(id=trip_id)
            except Trip.DoesNotExist:
                pass
        return super().create(validated_data)


class SosAlertSerializer(serializers.Serializer):
    alert_type = serializers.ChoiceField(choices=Incident.ALERT_TYPE_CHOICES, required=True)
    lat = serializers.FloatField(required=True)
    lng = serializers.FloatField(required=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    trip_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        return attrs


class IncidentListSerializer(serializers.ModelSerializer):
    user_username = serializers.SerializerMethodField(read_only=True)
    trip_id = serializers.PrimaryKeyRelatedField(source='trip', read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id',
            'user',
            'user_username',
            'alert_type',
            'lat',
            'lng',
            'accuracy',
            'status',
            'trip_id',
            'created_at',
            'resolved_at',
        ]

    def get_user_username(self, obj):
        if obj.user:
            return obj.user.username
        return None
