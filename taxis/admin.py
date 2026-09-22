from django.contrib import admin
from .models import Taxi


@admin.register(Taxi)
class TaxiAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'owner', 'is_active', 'capacity')
