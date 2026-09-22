from django.contrib import admin
from .models import BiometricRequest


@admin.register(BiometricRequest)
class BiometricRequestAdmin(admin.ModelAdmin):
    list_display = ('driver', 'status', 'created_at')
    list_filter = ('status',)
