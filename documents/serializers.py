from rest_framework import serializers
from .models import DriverDocument


class DriverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverDocument
        fields = ['id', 'driver', 'file', 'doc_type', 'status', 'notes', 'uploaded_at']
        read_only_fields = ['status', 'uploaded_at', 'driver']


class DriverDocumentAdminSerializer(DriverDocumentSerializer):
    class Meta(DriverDocumentSerializer.Meta):
        read_only_fields = ['uploaded_at']
        fields = DriverDocumentSerializer.Meta.fields
