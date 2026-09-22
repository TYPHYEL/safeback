from django.contrib import admin
from django.utils import timezone
from .models import Trip, Deposit


@admin.action(description='Terminer les trajets sélectionnés')
def complete_selected(modeladmin, request, queryset):
    updated = queryset.filter(status__in=['pending', 'active']).count()
    queryset.filter(status__in=['pending', 'active']).update(
        status='completed',
        ended_at=timezone.now(),
    )
    modeladmin.message_user(request, f'{updated} trajet(s) marqué(s) comme terminé(s).')


@admin.action(description='Annuler les trajets sélectionnés')
def cancel_selected(modeladmin, request, queryset):
    updated = queryset.exclude(status='cancelled').count()
    queryset.exclude(status='cancelled').update(status='cancelled', ended_at=timezone.now())
    modeladmin.message_user(request, f'{updated} trajet(s) annulé(s).')


@admin.action(description='Valider les demandes sélectionnées')
def accept_deposits(modeladmin, request, queryset):
    updated = queryset.exclude(status='completed').count()
    queryset.exclude(status='completed').update(status='accepted')
    modeladmin.message_user(request, f'{updated} demande(s) validée(s).')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'taxi', 'status', 'started_at', 'ended_at', 'created_at')
    list_filter = ('status', 'driver__role', 'created_at')
    search_fields = ('driver__username', 'taxi__plate_number', 'join_code')
    raw_id_fields = ('taxi', 'driver')
    ordering = ('-created_at',)
    actions = (complete_selected, cancel_selected)


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'passenger', 'driver', 'taxi', 'status', 'pickup_location', 'dropoff_location', 'created_at')
    list_filter = ('status', 'is_night', 'created_at')
    search_fields = ('passenger__username', 'driver__username', 'pickup_location', 'dropoff_location')
    raw_id_fields = ('passenger', 'driver', 'taxi')
    ordering = ('-created_at',)
    actions = (accept_deposits,)
