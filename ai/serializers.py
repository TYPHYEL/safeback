from rest_framework import serializers


class RiskAnalysisSerializer(serializers.Serializer):
    location = serializers.CharField()
    time = serializers.CharField()
    weather = serializers.CharField(required=False)
    additional_context = serializers.CharField(required=False)


class ChatMessageSerializer(serializers.Serializer):
    messages = serializers.ListField(child=serializers.DictField())
