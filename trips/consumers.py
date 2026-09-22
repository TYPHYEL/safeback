import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TripConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=403)
            return

        self.trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.group_name = f'trip_{self.trip_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Expect JSON with {"lat":..., "lng":..., "timestamp":...}
        try:
            data = json.loads(text_data)
        except Exception:
            return
        # Broadcast to group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'location.message',
                'payload': data,
            }
        )

    async def location_message(self, event):
        payload = event.get('payload')
        await self.send(text_data=json.dumps(payload))
