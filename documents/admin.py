from django.contrib import admin
from .models import DriverDocument


@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ('driver', 'doc_type', 'status', 'uploaded_at')
    list_filter = ('status', 'doc_type')
