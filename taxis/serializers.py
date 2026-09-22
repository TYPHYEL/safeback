from rest_framework import serializers
from users.serializers import UserSerializer
from .models import Taxi


class TaxiSerializer(serializers.ModelSerializer):
    plate_number = serializers.RegexField(
        regex=r'^[A-Z]{2}\d{4}[A-Z]$',
        error_messages={
            'invalid': 'Numéro de plaque invalide. Exemple attendu: LT1234A.',
        },
    )
    owner = UserSerializer(read_only=True)
    active_driver = UserSerializer(read_only=True)
    license_number = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Taxi
        fields = [
            'id',
            'owner',
            'active_driver',
            'plate_number',
            'brand',
            'model',
            'color',
            'license_number',
            'image',
            'capacity',
            'is_active',
            'last_lat',
            'last_lng',
        ]
        read_only_fields = ['owner']

    def validate_capacity(self, value):
        if value < 1 or value > 8:
            raise serializers.ValidationError(
                'La capacité doit être comprise entre 1 et 8 places.'
            )
        return value

    def validate_plate_number(self, value):
        return value.strip().upper()
