from rest_framework import serializers
from .models import Rating


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'rater', 'ratee', 'trip', 'score', 'comment', 'created_at']
        read_only_fields = ['rater', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['rater'] = request.user
        return super().create(validated_data)
