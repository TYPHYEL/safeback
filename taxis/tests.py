from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.models import DriverProfile

from .models import Taxi
from .serializers import TaxiSerializer

User = get_user_model()


class TaxiModelTest(TestCase):
    def test_taxi_str_representation(self):
        owner = User.objects.create_user(
            username='+237670000100',
            password='testpass123',
            role='owner',
        )
        taxi = Taxi.objects.create(
            owner=owner,
            plate_number='LT1234A',
            model='Toyota Corolla',
            color='Yellow',
            capacity=4,
        )
        self.assertEqual(str(taxi), 'LT1234A (+237670000100 (owner))')


class TaxiSerializerTest(TestCase):
    def test_reject_invalid_plate_number(self):
        serializer = TaxiSerializer(
            data={
                'plate_number': 'INVALID',
                'brand': 'Toyota',
                'model': 'Corolla',
                'color': 'Yellow',
                'capacity': 4,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('plate_number', serializer.errors)


class TaxiAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='+237670000102',
            password='testpass123',
            role='owner',
        )
        self.passenger = User.objects.create_user(
            username='+237670000103',
            password='testpass123',
            role='passenger',
        )
        self.driver = User.objects.create_user(
            username='+237670000104',
            password='testpass123',
            role='driver',
        )
        DriverProfile.objects.create(user=self.driver, verified=True)

        self.taxi = Taxi.objects.create(
            owner=self.owner,
            plate_number='LT2345B',
            brand='Honda',
            model='Civic',
            color='Blue',
            capacity=4,
            last_lat=Decimal('3.848000'),
            last_lng=Decimal('11.502100'),
        )

    def test_create_taxi_as_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            '/api/taxis/',
            {
                'plate_number': 'LT3456C',
                'brand': 'Toyota',
                'model': 'Camry',
                'color': 'Black',
                'capacity': 4,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['plate_number'], 'LT3456C')

    def test_create_taxi_as_driver(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.post(
            '/api/taxis/',
            {
                'plate_number': 'LT4567D',
                'brand': 'Kia',
                'model': 'Rio',
                'color': 'White',
                'capacity': 4,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_taxi_as_passenger_forbidden(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            '/api/taxis/',
            {
                'plate_number': 'LT5678E',
                'brand': 'Toyota',
                'model': 'Yaris',
                'color': 'Black',
                'capacity': 4,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nearby_taxis(self):
        Taxi.objects.create(
            owner=self.owner,
            plate_number='LT6789F',
            brand='Toyota',
            model='Avensis',
            color='Red',
            capacity=4,
            last_lat=Decimal('3.850000'),
            last_lng=Decimal('11.503000'),
            is_active=True,
        )
        Taxi.objects.create(
            owner=self.owner,
            plate_number='LT7890G',
            brand='Honda',
            model='Fit',
            color='Green',
            capacity=4,
            last_lat=Decimal('4.050000'),
            last_lng=Decimal('12.000000'),
            is_active=True,
        )

        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(
            '/api/taxis/nearby/',
            {'lat': '3.8480', 'lng': '11.5021', 'radius': '10'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nearby_plates = [taxi['plate_number'] for taxi in response.data]
        self.assertIn('LT6789F', nearby_plates)
        self.assertNotIn('LT7890G', nearby_plates)

    def test_get_taxi_qr_code(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(f'/api/taxis/{self.taxi.id}/qrcode/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('qr_data', response.data)

    def test_update_taxi_as_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f'/api/taxis/{self.taxi.id}/',
            {'color': 'Red'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.taxi.refresh_from_db()
        self.assertEqual(self.taxi.color, 'Red')
