from django.urls import path
from .consumers import TripConsumer

websocket_urlpatterns = [
    path('ws/trips/<int:trip_id>/', TripConsumer.as_asgi()),
]
