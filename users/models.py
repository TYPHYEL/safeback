from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('passenger', 'Passenger'),
        ('driver', 'Driver'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='passenger')

    def __str__(self):
        return f"{self.username} ({self.role})"


class PhoneOTP(models.Model):
    phone = models.CharField(max_length=32, unique=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP {self.phone} ({self.code})"


class DriverProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_profile')
    phone_number = models.CharField(max_length=32, blank=True, null=True)
    license_number = models.CharField(max_length=64, blank=True, null=True)
    vehicle_type = models.CharField(max_length=100, blank=True, null=True)
    plate_number = models.CharField(max_length=20, blank=True, null=True)
    license_photo = models.ImageField(upload_to='driver_licenses/', blank=True, null=True)
    vehicle_photo = models.ImageField(upload_to='driver_vehicles/', blank=True, null=True)
    cni_photo = models.ImageField(upload_to='driver_cni/', blank=True, null=True)
    profile_photo = models.ImageField(upload_to='driver_profiles/', blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    documents = models.JSONField(default=dict, blank=True)
    qr_code = models.CharField(max_length=64, unique=True, blank=True, null=True)
    face_embedding = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"DriverProfile {self.user.username}"


class EmergencyContact(models.Model):
    RELATION_CHOICES = (
        ('parent', 'Parent'),
        ('sibling', 'Frere/Soeur'),
        ('spouse', 'Conjoint(e)'),
        ('child', 'Enfant'),
        ('friend', 'Ami(e)'),
        ('colleague', 'Collegue'),
        ('other', 'Autre'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES, default='other')
    can_receive_sms = models.BooleanField(default=True)
    can_receive_call = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.relation}) - {self.user.username}"
