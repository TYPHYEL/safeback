from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.models import DriverProfile

from taxis.models import Taxi

from .models import Trip

User = get_user_model()


class TripModelTest(TestCase):
    def test_trip_creation(self):
        owner = User.objects.create_user(username='+237670000200', password='testpass123', role='owner')
        driver = User.objects.create_user(username='+237670000201', password='testpass123', role='driver')
        taxi = Taxi.objects.create(owner=owner, plate_number='LT1111A', model='Toyota', capacity=4)
        trip = Trip.objects.create(taxi=taxi, driver=driver)

        self.assertEqual(trip.status, 'pending')
        self.assertEqual(str(trip), f'Trip {trip.id} ({trip.status})')


class TripAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username='+237670000203', password='testpass123', role='owner')
        self.driver = User.objects.create_user(username='+237670000204', password='testpass123', role='driver')
        DriverProfile.objects.create(user=self.driver, verified=True)
        self.passenger = User.objects.create_user(username='+237670000205', password='testpass123', role='passenger')
        self.taxi = Taxi.objects.create(
            owner=self.owner,
            plate_number='LT2222B',
            model='Honda',
            color='Blue',
            capacity=4,
        )

    def _create_trip(self, status_value='pending'):
        trip = Trip.objects.create(
            taxi=self.taxi,
            driver=self.driver,
            status=status_value,
            started_at=timezone.now() if status_value == 'active' else None,
        )
        if not trip.join_code:
            trip.join_code = 'JOIN12'
            trip.save(update_fields=['join_code'])
        return trip

    def test_create_trip_as_driver(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.post(
            '/api/trips/',
            {'taxi': self.taxi.id, 'start_lat': '3.848000', 'start_lng': '11.502000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertTrue(response.data['join_code'])

    def test_join_trip_by_code(self):
        trip = self._create_trip()
        trip.join_code = 'CODE12'
        trip.save(update_fields=['join_code'])

        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            '/api/trips/join_by_code/',
            {'join_code': 'CODE12'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertIn(self.passenger, trip.passengers.all())

    def test_leave_trip(self):
        trip = self._create_trip()
        trip.passengers.add(self.passenger)

        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(f'/api/trips/{trip.id}/leave/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertNotIn(self.passenger, trip.passengers.all())

    def test_start_and_end_trip_as_driver(self):
        trip = self._create_trip()
        trip.passengers.add(self.passenger)

        self.client.force_authenticate(user=self.driver)
        start_response = self.client.post(f'/api/trips/{trip.id}/start/', format='json')
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'active')

        end_response = self.client.post(f'/api/trips/{trip.id}/end/', format='json')
        self.assertEqual(end_response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'completed')
        self.assertIsNotNone(trip.ended_at)

    def test_trip_history_for_passenger(self):
        trip = self._create_trip(status_value='completed')
        trip.started_at = timezone.now() - timedelta(hours=2)
        trip.ended_at = timezone.now() - timedelta(hours=1)
        trip.save(update_fields=['started_at', 'ended_at'])
        trip.passengers.add(self.passenger)

        self.client.force_authenticate(user=self.passenger)
        response = self.client.get('/api/trips/history/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['id'] == trip.id for item in response.data))

    def test_active_trip_for_passenger_returns_object(self):
        trip = self._create_trip(status_value='active')
        trip.passengers.add(self.passenger)

        self.client.force_authenticate(user=self.passenger)
        response = self.client.get('/api/trips/active/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], trip.id)

    def test_capacity_limit(self):
        trip = self._create_trip()
        for index in range(self.taxi.capacity):
            passenger = User.objects.create_user(
                username=f'+2376700012{index:02d}',
                password='testpass123',
                role='passenger',
            )
            trip.passengers.add(passenger)

        extra_passenger = User.objects.create_user(
            username='+237670000299',
            password='testpass123',
            role='passenger',
        )
        self.client.force_authenticate(user=extra_passenger)
        response = self.client.post(f'/api/trips/{trip.id}/join/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
