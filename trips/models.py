from django.db import models
from django.conf import settings
from django.utils import timezone
from taxis.models import Taxi


class Trip(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    taxi = models.ForeignKey(Taxi, on_delete=models.SET_NULL, null=True, related_name='trips')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='driven_trips')
    passengers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='trips', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    join_code = models.CharField(max_length=8, unique=True, blank=True, null=True)
    start_location = models.CharField(max_length=255, blank=True, null=True)
    end_location = models.CharField(max_length=255, blank=True, null=True)
    start_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estimated_duration = models.IntegerField(null=True, blank=True, help_text='Duration in minutes')
    fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Trip {self.id} ({self.status})"


class Deposit(models.Model):
    """Course privée pour un seul passager"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),      # En attente de chauffeur
        ('offered', 'Offered'),      # Proposé à un chauffeur
        ('accepted', 'Accepted'),    # Accepté par chauffeur
        ('active', 'Active'),        # En cours
        ('completed', 'Completed'),  # Terminé
        ('cancelled', 'Cancelled'),  # Annulé
        ('expired', 'Expired'),      # Expiré (pas de chauffeur trouvé)
    )
    
    passenger = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deposits')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='deposit_drives')
    taxi = models.ForeignKey(Taxi, on_delete=models.SET_NULL, null=True, blank=True, related_name='deposits')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Points de départ et d'arrivée
    pickup_location = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_location = models.CharField(max_length=255)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Prix et distance
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, help_text='Distance en km')
    fare = models.DecimalField(max_digits=10, decimal_places=2, help_text='Prix proposé en FCFA')
    is_night = models.BooleanField(default=False, help_text='Tarif de nuit appliqué')
    
    # Horaires
    pickup_time = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Expiration de la demande')
    
    # Trust score du chauffeur au moment de l'acceptation
    driver_trust_score = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Deposit {self.id} - {self.passenger.username} ({self.status})"
    
    def is_expired(self):
        """Vérifie si la demande de dépôt est expirée"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
