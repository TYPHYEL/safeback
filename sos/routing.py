from django.urls import path
from .consumers import SosAlertConsumer

websocket_urlpatterns = [
    path('ws/sos/alerts/', SosAlertConsumer.as_asgi()),
]
