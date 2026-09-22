from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Incident

User = get_user_model()


class IncidentModelTest(TestCase):
    def test_incident_creation(self):
        user = User.objects.create_user(
            username='+237670000300',
            password='testpass123',
            role='passenger',
        )
        incident = Incident.objects.create(
            user=user,
            lat=3.8480,
            lng=11.5021,
            description='Emergency situation',
        )
        self.assertEqual(incident.user, user)
        self.assertEqual(incident.status, 'open')
        self.assertEqual(str(incident), f'Incident {incident.id} - open')


class IncidentAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.passenger = User.objects.create_user(
            username='+237670000301',
            password='testpass123',
            role='passenger',
        )
        self.driver = User.objects.create_user(
            username='+237670000302',
            password='testpass123',
            role='driver',
        )
        self.admin = User.objects.create_user(
            username='admin-incident',
            password='testpass123',
            role='admin',
            is_staff=True,
        )

    def test_create_incident(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            '/api/incidents/',
            {
                'lat': '3.8500',
                'lng': '11.5100',
                'description': 'I need help urgently',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'open')

    def test_create_incident_with_alert_type(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            '/api/incidents/',
            {'lat': '3.8500', 'lng': '11.5100', 'alert_type': 'aggression'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_sees_all_incidents(self):
        incident1 = Incident.objects.create(user=self.passenger, lat=3.8480, lng=11.5021, description='One')
        incident2 = Incident.objects.create(user=self.driver, lat=3.8500, lng=11.5100, description='Two')
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/incidents/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        incident_ids = [inc['id'] for inc in response.data]
        self.assertIn(incident1.id, incident_ids)
        self.assertIn(incident2.id, incident_ids)

    def test_passenger_cannot_list_all_incidents(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get('/api/incidents/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_incident_status(self):
        incident = Incident.objects.create(user=self.passenger, lat=3.8480, lng=11.5021, description='Emergency')
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f'/api/incidents/{incident.id}/',
            {'status': 'resolved'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'resolved')

    def test_unauthenticated_cannot_create_incident(self):
        response = self.client.post(
            '/api/incidents/',
            {'lat': '3.8500', 'lng': '11.5100', 'description': 'Emergency'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
