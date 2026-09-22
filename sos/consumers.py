import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class SosAlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'sos_alerts'
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            await self.close(code=403)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            return

        action = data.get('action')
        if action == 'sos_trigger':
            user = self.scope.get('user')
            payload = {
                'action': 'sos_trigger',
                'incident_id': data.get('incident_id'),
                'alert_type': data.get('alert_type'),
                'lat': data.get('lat'),
                'lng': data.get('lng'),
                'accuracy': data.get('accuracy'),
                'description': data.get('description'),
                'user_id': user.id if user else None,
                'username': user.username if user else None,
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'sos.alert',
                    'payload': payload,
                }
            )

    async def sos_alert(self, event):
        payload = event.get('payload')
        await self.send(text_data=json.dumps({
            'type': 'sos.alert',
            'data': payload,
        }))
