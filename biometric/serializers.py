from rest_framework import serializers
from .models import BiometricRequest


class BiometricRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricRequest
        fields = ['id', 'driver', 'selfie', 'reference', 'status', 'result', 'created_at']
        read_only_fields = ['status', 'result', 'created_at', 'driver']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['driver'] = request.user
        return super().create(validated_data)
