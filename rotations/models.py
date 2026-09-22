from django.db import models
from django.conf import settings
from taxis.models import Taxi


class DriverRotation(models.Model):
    SHIFT_CHOICES = (
        ('day', 'Day'),
        ('night', 'Night'),
        ('full', 'Full Day'),
    )
    
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE, related_name='rotations')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rotations')
    shift_type = models.CharField(max_length=10, choices=SHIFT_CHOICES, default='full')
    days_of_week = models.JSONField(default=list, help_text='List of days (1-7 for Monday-Sunday)')
    start_time = models.TimeField(help_text='Shift start time')
    end_time = models.TimeField(help_text='Shift end time')
    start_date = models.DateField(null=True, blank=True, help_text='Optional start date')
    end_date = models.DateField(null=True, blank=True, help_text='Optional end date')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['taxi', 'driver', 'shift_type', 'days_of_week', 'start_time']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.driver.username} - {self.taxi.plate_number} ({self.shift_type})"


class ShiftHandoff(models.Model):
    """Secure handoff between drivers with biometric verification."""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE, related_name='handoffs')
    outgoing_driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='outgoing_handoffs',
        help_text='Driver ending shift'
    )
    incoming_driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incoming_handoffs',
        help_text='Driver starting shift'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Biometric verification
    outgoing_selfie = models.ImageField(upload_to='handoffs/outgoing/', null=True, blank=True)
    incoming_selfie = models.ImageField(upload_to='handoffs/incoming/', null=True, blank=True)
    biometric_verified = models.BooleanField(default=False)
    biometric_match_confidence = models.FloatField(null=True, blank=True)
    
    # Handoff details
    handoff_time = models.DateTimeField(null=True, blank=True)
    handoff_location_lat = models.FloatField(null=True, blank=True)
    handoff_location_lng = models.FloatField(null=True, blank=True)
    odometer_reading = models.FloatField(null=True, blank=True, help_text='Odometer at handoff')
    fuel_level = models.FloatField(null=True, blank=True, help_text='Fuel level percentage')
    
    # Notes
    notes = models.TextField(blank=True, help_text='Any notes about the vehicle condition')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Handoff: {self.outgoing_driver.username} → {self.incoming_driver.username} ({self.taxi.plate_number})"


class DriverShiftHistory(models.Model):
    """Track driver shift history for analytics and compliance."""
    
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shift_history')
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE, related_name='shift_histories')
    rotation = models.ForeignKey(DriverRotation, on_delete=models.SET_NULL, null=True, blank=True)
    
    shift_start = models.DateTimeField()
    shift_end = models.DateTimeField(null=True, blank=True)
    
    # Metrics
    total_distance = models.FloatField(default=0, help_text='Distance traveled in km')
    total_trips = models.IntegerField(default=0, help_text='Number of trips completed')
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Revenue earned')
    
    # Status
    is_active = models.BooleanField(default=True, help_text='Is shift currently active')
    ended_cleanly = models.BooleanField(default=True, help_text='Did shift end normally')
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-shift_start']
        
    def __str__(self):
        return f"{self.driver.username} shift on {self.shift_start.strftime('%Y-%m-%d')}"
