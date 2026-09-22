import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

from notifications.services import send_to_topic, send_to_user
from users.models import CustomUser, EmergencyContact
from users.services import sms_service

logger = logging.getLogger(__name__)


@shared_task(name='sos.process_sos_alert', bind=True, max_retries=3, default_retry_delay=30)
def process_sos_alert(self, incident_id: int):
    from .models import Incident

    try:
        incident = Incident.objects.select_related('user', 'trip').get(id=incident_id)
    except Incident.DoesNotExist:
        logger.warning('SOS alert not found: %s', incident_id)
        return {'status': 'not_found', 'incident_id': incident_id}

    user = incident.user
    alert_type = incident.alert_type or 'other'
    lat = float(incident.lat) if incident.lat is not None else None
    lng = float(incident.lng) if incident.lng is not None else None
    location = 'Position indisponible'
    if lat is not None and lng is not None:
        location = f'https://maps.google.com/?q={lat},{lng}'

    message = (
        f"ALERTE SAFE TAXI: {alert_type.upper()}\n"
        f"Localisation: {location}\n"
        f"Détails: {incident.description or 'Aucun détail fourni'}"
    )

    # 1. SMS to emergency contacts
    contact_count = 0
    if user:
        for contact in EmergencyContact.objects.filter(user=user):
            if not contact.can_receive_sms or not getattr(contact, 'phone', '').strip():
                continue
            sms_message = (
                f"ALERTE SOS SAFE TAXI\n"
                f"Contact: {contact.name} ({contact.relation})\n"
                f"Type: {alert_type}\n"
                f"Localisation: {location}\n"
                f"Merci de vous rendre sur place ou d'appeler les secours."
            )
            try:
                sms_service.send_sms(contact.phone, sms_message)
                contact_count += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning('Failed to SMS emergency contact %s for incident %s: %s', contact.phone, incident.id, exc)

    # 2. FCM push to user and to admins
    notifs_sent = 0
    if user:
        result = send_to_user(user, 'Alerte SOS', message, {'type': 'sos', 'incident_id': str(incident.id)})
        notifs_sent += result.get('success', 0)

    admin_users = CustomUser.objects.filter(is_staff=True)
    for admin in admin_users:
        result = send_to_user(admin, 'Alerte SOS', message, {'type': 'sos', 'incident_id': str(incident.id)})
        notifs_sent += result.get('success', 0)

    topic_result = send_to_topic('sos_alerts', 'Alerte SOS', message, {'type': 'sos', 'incident_id': str(incident.id)})
    notifs_sent += topic_result.get('success', 0)

    payload = {
        'action': 'sos_trigger',
        'incident_id': incident.id,
        'alert_type': alert_type,
        'lat': lat,
        'lng': lng,
        'description': incident.description,
        'user_id': user.id if user else None,
        'username': user.username if user else None,
    }

    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            'sos_alerts',
            {
                'type': 'sos.alert',
                'payload': payload,
            },
        )

    logger.info(
        'SOS process completed: incident_id=%s contacts=%s fcm_success=%s',
        incident.id,
        contact_count,
        notifs_sent,
    )
    return {
        'status': 'ok',
        'incident_id': incident.id,
        'contacts_sms': contact_count,
        'notifications_sent': notifs_sent,
    }


@shared_task(name='sos.cleanup_expired_alerts')
def cleanup_expired_alerts():
    from .models import Incident

    cutoff = timezone.now() - timedelta(hours=24)
    expired = Incident.objects.filter(status='open', created_at__lt=cutoff)
    count = expired.count()
    expired.update(status='cancelled')
    logger.info('Cleaned up %s expired SOS alerts', count)
    return {'status': 'ok', 'count': count}


@shared_task(name='sos.notify_incident_resolved')
def notify_incident_resolved(incident_id: int):
    from .models import Incident

    try:
        incident = Incident.objects.select_related('user').get(id=incident_id)
    except Incident.DoesNotExist:
        return {'status': 'not_found', 'incident_id': incident_id}

    if incident.user:
        send_to_user(
            incident.user,
            'Incident résolu',
            'Votre signalement SOS a été traité et clôturé.',
            {'type': 'incident_resolved', 'incident_id': str(incident.id)},
        )
    return {'status': 'ok', 'incident_id': incident.id}
