from django.db import models
from django.conf import settings


class Device(models.Model):
    # store FCM token per user/device
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    token = models.CharField(max_length=512)
    platform = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f"Device {self.user} {self.platform}"
