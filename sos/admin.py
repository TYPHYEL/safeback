from django.contrib import admin
from django.utils import timezone
from .models import Incident


@admin.action(description='Résoudre les incidents sélectionnés')
def resolve_selected(modeladmin, request, queryset):
    queryset.update(
        status='resolved',
        resolved_at=timezone.now(),
        resolved_by=request.user,
    )


@admin.action(description='Résoudre en masse les incidents sélectionnés')
def bulk_resolve(modeladmin, request, queryset):
    count = 0
    for incident in queryset.filter(status__in=['open', 'cancelled']):
        incident.status = 'resolved'
        incident.resolved_at = timezone.now()
        incident.resolved_by = request.user
        incident.save()
        count += 1
    modeladmin.message_user(request, f"{count} incident(s) résolu(s) avec succès.")


@admin.action(description='Annuler les incidents sélectionnés')
def cancel_selected(modeladmin, request, queryset):
    queryset.update(status='cancelled')


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'alert_type',
        'status',
        'lat',
        'lng',
        'created_at',
    )
    list_filter = (
        'status',
        'alert_type',
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'description',
    )
    readonly_fields = (
        'created_at',
        'resolved_at',
    )
    actions = (
        resolve_selected,
        bulk_resolve,
        cancel_selected,
    )
    list_select_related = ('user', 'resolved_by', 'trip')
    raw_id_fields = ('user', 'resolved_by', 'trip')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('user', 'alert_type', 'status', 'trip')
        }),
        ('Localisation', {
            'fields': ('lat', 'lng', 'accuracy')
        }),
        ('Détails', {
            'fields': ('description',)
        }),
        ('Dates', {
            'fields': ('created_at', 'resolved_at', 'resolved_by'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'resolved_by', 'trip')
