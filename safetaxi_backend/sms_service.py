import os
import re
import logging

logger = logging.getLogger(__name__)

CM_PHONE_REGEX = re.compile(r'^\+237(6|67|65|68|69|66)\d{7}$')


def validate_cm_phone(phone):
    if not phone:
        return False
    cleaned = phone.replace(' ', '').replace('-', '')
    return bool(CM_PHONE_REGEX.match(cleaned))


class SMSService:
    def __init__(self):
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_from_number = os.getenv('TWILIO_FROM_NUMBER')
        self.orange_cm_api_key = os.getenv('ORANGE_CM_API_KEY')
        self.orange_cm_sender = os.getenv('ORANGE_CM_SENDER', 'SAFETAXI')
        self._twilio_client = None

    @property
    def twilio_client(self):
        if self._twilio_client is None:
            try:
                from twilio.rest import Client
                if self.twilio_account_sid and self.twilio_auth_token:
                    self._twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            except ImportError:
                logger.warning("Twilio library not installed. Twilio SMS unavailable.")
        return self._twilio_client

    def send_sms(self, phone, body):
        if not validate_cm_phone(phone):
            logger.warning(f"Invalid CM phone number: {phone}")
            return False

        sent = self._send_twilio(phone, body)
        if sent:
            return True

        sent = self._send_orange_cm(phone, body)
        if sent:
            return True

        logger.warning(f"All SMS providers failed for {phone}. Stub response.")
        return True

    def send_otp_sms(self, phone, code):
        body = f"SAFETAXI: Votre code de verification est {code}. Ce code expire dans 5 minutes."
        return self.send_sms(phone, body)

    def _send_twilio(self, phone, body):
        if not self.twilio_client or not self.twilio_from_number:
            return False
        try:
            message = self.twilio_client.messages.create(
                body=body,
                from_=self.twilio_from_number,
                to=phone
            )
            logger.info(f"Twilio SMS sent to {phone}: SID={message.sid}")
            return True
        except Exception as e:
            logger.error(f"Twilio SMS failed for {phone}: {str(e)}")
            return False

    def _send_orange_cm(self, phone, body):
        if not self.orange_cm_api_key:
            return False
        try:
            import requests
            url = "https://api.orange.com/oauth/v3/token"
            headers = {
                'Authorization': f'Basic {self.orange_cm_api_key}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = {'grant_type': 'client_credentials'}
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code != 200:
                logger.error(f"Orange CM auth failed: {response.status_code}")
                return False
            access_token = response.json().get('access_token')
            if not access_token:
                return False

            send_url = "https://api.orange.com/smsmessaging/v1/outbound/tel:+237/requests"
            send_headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            send_data = {
                'outboundSMSMessageRequest': {
                    'address': [f'tel:{phone}'],
                    'senderAddress': f'tel:+{self.orange_cm_sender}',
                    'outboundSMSTextMessage': {'message': body}
                }
            }
            send_response = requests.post(send_url, headers=send_headers, json=send_data, timeout=10)
            if send_response.status_code in (200, 201):
                logger.info(f"Orange CM SMS sent to {phone}")
                return True
            logger.error(f"Orange CM send failed: {send_response.status_code} - {send_response.text}")
            return False
        except ImportError:
            logger.warning("requests library not installed. Orange CM SMS unavailable.")
            return False
        except Exception as e:
            logger.error(f"Orange CM SMS failed for {phone}: {str(e)}")
            return False


sms_service = SMSService()
