from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import DriverProfile, PhoneOTP

User = get_user_model()


class CustomUserModelTest(TestCase):
    def test_user_str_representation(self):
        user = User.objects.create_user(
            username='+237670000001',
            password='testpass123',
            role='passenger',
        )
        self.assertEqual(str(user), '+237670000001 (passenger)')


class DriverProfileModelTest(TestCase):
    def test_profile_defaults(self):
        user = User.objects.create_user(
            username='+237670000002',
            password='testpass123',
            role='driver',
        )
        profile = DriverProfile.objects.create(user=user)
        self.assertFalse(profile.verified)
        self.assertFalse(profile.is_active)
        self.assertEqual(profile.documents, {})


class AuthenticationAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.profile_url = '/api/auth/profile/'

    def test_user_registration(self):
        response = self.client.post(
            self.register_url,
            {
                'username': '+237670000010',
                'phone': '+237670000010',
                'password': 'testpass123',
                'role': 'passenger',
                'first_name': 'New',
                'last_name': 'User',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['phone'], '+237670000010')
        self.assertEqual(response.data['role'], 'passenger')

    def test_user_login(self):
        user = User.objects.create_user(
            username='+237670000012',
            password='testpass123',
            role='passenger',
        )
        response = self.client.post(
            self.login_url,
            {'username': user.username, 'password': 'testpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_and_update_profile(self):
        user = User.objects.create_user(
            username='+237670000013',
            password='testpass123',
            role='passenger',
            first_name='Old',
            last_name='Name',
        )
        self.client.force_authenticate(user=user)

        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['phone'], '+237670000013')

        patch_response = self.client.patch(
            self.profile_url,
            {'first_name': 'Updated'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')


class PhoneOTPTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.send_url = '/api/auth/otp/send/'
        self.verify_url = '/api/auth/otp/verify/'

    def test_send_otp(self):
        response = self.client.post(self.send_url, {'phone': '+237670000020'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        otp = PhoneOTP.objects.filter(phone='+237670000020').first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.code), 6)

    def test_verify_otp_correct(self):
        phone = '+237670000021'
        User.objects.create_user(username=phone, password='testpass123', role='passenger')
        PhoneOTP.objects.create(phone=phone, code='123456')

        response = self.client.post(
            self.verify_url,
            {'phone': phone, 'code': '123456'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_verify_otp_incorrect(self):
        phone = '+237670000022'
        PhoneOTP.objects.create(phone=phone, code='123456')

        response = self.client.post(
            self.verify_url,
            {'phone': phone, 'code': '999999'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminDriverApprovalTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin-user',
            password='admin123',
            role='admin',
            is_staff=True,
        )
        self.driver = User.objects.create_user(
            username='+237670000031',
            password='driver123',
            role='driver',
        )
        DriverProfile.objects.create(user=self.driver)
        self.client = APIClient()

    def test_get_pending_drivers(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/admin/drivers/pending/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_approve_driver(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/admin/drivers/{self.driver.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.driver.driver_profile.refresh_from_db()
        self.assertTrue(self.driver.driver_profile.verified)

    def test_non_admin_cannot_approve(self):
        passenger = User.objects.create_user(
            username='+237670000032',
            password='pass123',
            role='passenger',
        )
        self.client.force_authenticate(user=passenger)
        response = self.client.post(f'/api/admin/drivers/{self.driver.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
