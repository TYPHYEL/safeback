from django.db import models
from django.conf import settings
from django.utils import timezone


class Incident(models.Model):
    ALERT_TYPE_CHOICES = (
        ('aggression', 'Aggression'),
        ('accident', 'Accident'),
        ('medical', 'Medical'),
        ('kidnapping', 'Kidnapping'),
        ('robbery', 'Robbery'),
        ('harassment', 'Harassment'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, null=True, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    trip = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_incidents')

    def __str__(self):
        return f"Incident {self.id} - {self.status}"
