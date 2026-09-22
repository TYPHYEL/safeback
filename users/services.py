import os
import re
import logging

logger = logging.getLogger(__name__)

CM_PHONE_REGEX = re.compile(r'^\+237[67]\d{8}$')


def validate_cm_phone(phone: str) -> bool:
    if not phone:
        return False
    cleaned = re.sub(r'[\s\-\.]', '', str(phone))
    return bool(CM_PHONE_REGEX.match(cleaned))


def normalize_cm_phone(phone: str) -> str:
    cleaned = re.sub(r'[\s\-\.]', '', str(phone))
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    if not cleaned.startswith('+') and len(cleaned) == 9:
        cleaned = '+237' + cleaned
    return cleaned


class SMSService:
    _instance = None
    _provider_configured = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_provider()
        return cls._instance

    def _init_provider(self):
        provider = os.getenv('SMS_PROVIDER', '').lower()
        api_key = os.getenv('SMS_API_KEY', '')
        sender_id = os.getenv('SMS_SENDER_ID', 'SAFETAXI')

        self.provider = provider
        self.api_key = api_key
        self.sender_id = sender_id
        SMSService._provider_configured = bool(provider and api_key)

    @classmethod
    def is_configured(cls) -> bool:
        if cls._provider_configured is None:
            cls()
        return cls._provider_configured

    def send_sms(self, phone: str, message: str) -> bool:
        if not self.is_configured():
            logger.warning(f"SMS provider not configured; skipping SMS to {phone}")
            return False
        try:
            return self._send_sms(phone, message)
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            return False

    def send_otp_sms(self, phone: str, code: str) -> bool:
        if not self.is_configured():
            logger.warning(f"SMS provider not configured; skipping OTP SMS to {phone}")
            return False

        message = f"SAFETAXI: Votre code de verification est {code}. Valable 15 minutes."
        try:
            return self.send_sms(phone, message)
        except Exception as e:
            logger.error(f"Failed to send OTP SMS to {phone}: {e}")
            return False

    def _send_sms(self, phone: str, message: str) -> bool:
        if self.provider == 'twilio':
            return self._send_twilio(phone, message)
        elif self.provider == 'infobip':
            return self._send_infobip(phone, message)
        elif self.provider == 'orangemoney':
            return self._send_orange(phone, message)
        else:
            logger.warning(f"Unknown SMS provider: {self.provider}")
            return False

    def _send_twilio(self, phone: str, message: str) -> bool:
        try:
            from twilio.rest import Client
            account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
            twilio_number = os.getenv('TWILIO_PHONE_NUMBER', self.sender_id)
            if not account_sid or not auth_token or not twilio_number:
                logger.warning("Twilio credentials incomplete")
                return False
            client = Client(account_sid, auth_token)
            client.messages.create(body=message, from_=twilio_number, to=phone)
            logger.info(f"OTP SMS sent via Twilio to {phone}")
            return True
        except Exception as e:
            logger.error(f"Twilio send failed: {e}")
            return False

    def _send_infobip(self, phone: str, message: str) -> bool:
        try:
            import requests
            base_url = os.getenv('INFOBIP_BASE_URL', 'https://api.infobip.com')
            headers = {
                'Authorization': f'App {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            payload = {
                'messages': [{
                    'from': self.sender_id,
                    'destinations': [{'to': phone}],
                    'text': message,
                }]
            }
            resp = requests.post(f'{base_url}/sms/2/text/advanced', json=payload, headers=headers, timeout=10)
            ok = resp.status_code == 200
            if ok:
                logger.info(f"OTP SMS sent via Infobip to {phone}")
            else:
                logger.warning(f"Infobip send failed: {resp.status_code} {resp.text}")
            return ok
        except Exception as e:
            logger.error(f"Infobip send failed: {e}")
            return False

    def _send_orange(self, phone: str, message: str) -> bool:
        try:
            import requests
            base_url = os.getenv('ORANGE_SMS_BASE_URL', 'https://api.orange.com')
            client_id = os.getenv('ORANGE_CLIENT_ID', '')
            client_secret = os.getenv('ORANGE_CLIENT_SECRET', '')
            if not client_id or not client_secret:
                logger.warning("Orange SMS credentials incomplete")
                return False
            auth_resp = requests.post(
                f'{base_url}/oauth/v3/token',
                data={'grant_type': 'client_credentials'},
                auth=(client_id, client_secret),
                timeout=10,
            )
            if auth_resp.status_code != 200:
                logger.warning(f"Orange auth failed: {auth_resp.status_code}")
                return False
            access_token = auth_resp.json().get('access_token')
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }
            sender_address = os.getenv('ORANGE_SENDER_ADDRESS', self.sender_id)
            payload = {
                'outboundSMSMessageRequest': {
                    'address': f'tel:{phone}',
                    'senderAddress': sender_address,
                    'outboundSMSTextMessage': {'message': message},
                }
            }
            resp = requests.post(
                f'{base_url}/smsmessaging/v1/outbound/{sender_address}/requests',
                json=payload,
                headers=headers,
                timeout=10,
            )
            ok = resp.status_code in (200, 201)
            if ok:
                logger.info(f"OTP SMS sent via Orange to {phone}")
            else:
                logger.warning(f"Orange send failed: {resp.status_code} {resp.text}")
            return ok
        except Exception as e:
            logger.error(f"Orange send failed: {e}")
            return False


sms_service = SMSService()
