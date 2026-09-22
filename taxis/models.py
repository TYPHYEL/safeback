from django.db import models
from django.conf import settings
from django.utils import timezone


class Taxi(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_taxis')
    plate_number = models.CharField(max_length=64)
    brand = models.CharField(max_length=64, blank=True, null=True)
    model = models.CharField(max_length=128, blank=True)
    color = models.CharField(max_length=64, blank=True, null=True)
    license_number = models.CharField(max_length=64, blank=True, null=True)
    image = models.ImageField(upload_to='taxi_images/', blank=True, null=True)
    capacity = models.IntegerField(default=4)
    is_active = models.BooleanField(default=True)
    active_driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_taxi')
    last_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    qr_code = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plate_number} ({self.owner})"
