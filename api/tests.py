import time
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import CustomUser, DriverProfile


class BackendSmokeTests(APITestCase):
    def register_user(self, username, email, password, role):
        return self.client.post(
            '/api/auth/register/',
            data={'username': username, 'email': email, 'password': password, 'role': role},
            format='json'
        )

    def obtain_token(self, username, password):
        return self.client.post(
            '/api/auth/token/',
            data={'username': username, 'password': password},
            format='json'
        )

    def test_backend_main_flow(self):
        # Register driver and passenger
        driver_resp = self.register_user('driver1', 'driver1@example.com', 'DriverPass123!', 'driver')
        self.assertEqual(driver_resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DriverProfile.objects.filter(user__username='driver1').exists())

        passenger_resp = self.register_user('pass1', 'pass1@example.com', 'Pass1234!', 'passenger')
        self.assertEqual(passenger_resp.status_code, status.HTTP_201_CREATED)

        # Obtain JWT tokens
        driver_token_resp = self.obtain_token('driver1', 'DriverPass123!')
        self.assertEqual(driver_token_resp.status_code, status.HTTP_200_OK)
        driver_access = driver_token_resp.data['access']

        passenger_token_resp = self.obtain_token('pass1', 'Pass1234!')
        self.assertEqual(passenger_token_resp.status_code, status.HTTP_200_OK)
        passenger_access = passenger_token_resp.data['access']

        # Driver creates a taxi
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {driver_access}')
        taxi_resp = self.client.post(
            '/api/taxis/',
            data={'plate_number': 'LT1234A', 'brand': 'Toyota', 'model': 'Toyota', 'capacity': 4},
            format='json'
        )
        self.assertEqual(taxi_resp.status_code, status.HTTP_201_CREATED)
        taxi_id = taxi_resp.data['id']

        # Driver creates a trip
        trip_resp = self.client.post(
            '/api/trips/',
            data={'taxi': taxi_id, 'start_lat': '3.848000', 'start_lng': '11.502000'},
            format='json'
        )
        self.assertEqual(trip_resp.status_code, status.HTTP_201_CREATED)
        trip_id = trip_resp.data['id']
        join_code = trip_resp.data['join_code']
        self.assertIsNotNone(join_code)

        # Passenger joins the trip by code
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {passenger_access}')
        join_resp = self.client.post('/api/trips/join_by_code/', data={'join_code': join_code}, format='json')
        self.assertEqual(join_resp.status_code, status.HTTP_200_OK)
        self.assertIn('passengers', join_resp.data)

        # Passenger creates an incident
        incident_resp = self.client.post(
            '/api/incidents/',
            data={'lat': '3.850000', 'lng': '11.500000', 'description': 'Test incident'},
            format='json'
        )
        self.assertEqual(incident_resp.status_code, status.HTTP_201_CREATED)

        # Passenger registers a device
        device_resp = self.client.post(
            '/api/devices/',
            data={'token': 'fake-token-123', 'platform': 'android'},
            format='json'
        )
        self.assertEqual(device_resp.status_code, status.HTTP_201_CREATED)

        # Passenger rates driver for the trip
        rating_resp = self.client.post(
            '/api/ratings/',
            data={'ratee': driver_resp.data['id'], 'trip': trip_id, 'score': 5, 'comment': 'Good ride'},
            format='json'
        )
        self.assertEqual(rating_resp.status_code, status.HTTP_201_CREATED)

        # Driver starts the trip
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {driver_access}')
        start_resp = self.client.post(f'/api/trips/{trip_id}/start/', data={}, format='json')
        self.assertEqual(start_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(start_resp.data['status'], 'active')

        # Driver uploads a document
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {driver_access}')
        sample_file = SimpleUploadedFile('doc.txt', b'fake document content')
        doc_resp = self.client.post('/api/driver-docs/', data={'file': sample_file, 'doc_type': 'license'}, format='multipart')
        self.assertEqual(doc_resp.status_code, status.HTTP_201_CREATED)
        doc_id = doc_resp.data['id']

        # Create admin user and approve the document
        admin_user = CustomUser.objects.create_user(username='admin1', email='admin1@example.com', password='AdminPass123!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_token_resp = self.obtain_token('admin1', 'AdminPass123!')
        self.assertEqual(admin_token_resp.status_code, status.HTTP_200_OK)
        admin_access = admin_token_resp.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_access}')
        approve_resp = self.client.post(f'/api/driver-docs/{doc_id}/approve/')
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_resp.data['status'], 'approved')

        # Check API root is available
        root_resp = self.client.get('/api/')
        self.assertEqual(root_resp.status_code, status.HTTP_200_OK)

    def test_document_reject_flow(self):
        driver_resp = self.register_user('driver3', 'driver3@example.com', 'DriverPass789!', 'driver')
        self.assertEqual(driver_resp.status_code, status.HTTP_201_CREATED)

        driver_token_resp = self.obtain_token('driver3', 'DriverPass789!')
        self.assertEqual(driver_token_resp.status_code, status.HTTP_200_OK)
        driver_access = driver_token_resp.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {driver_access}')
        sample_file = SimpleUploadedFile('doc.txt', b'fake document content')
        doc_resp = self.client.post('/api/driver-docs/', data={'file': sample_file, 'doc_type': 'license'}, format='multipart')
        self.assertEqual(doc_resp.status_code, status.HTTP_201_CREATED)
        doc_id = doc_resp.data['id']

        admin_user = CustomUser.objects.create_user(username='admin3', email='admin3@example.com', password='AdminPass789!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_token_resp = self.obtain_token('admin3', 'AdminPass789!')
        self.assertEqual(admin_token_resp.status_code, status.HTTP_200_OK)
        admin_access = admin_token_resp.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_access}')
        reject_resp = self.client.post(f'/api/driver-docs/{doc_id}/reject/', data={'notes': 'Invalid document'}, format='json')
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_resp.data['status'], 'rejected')
        self.assertEqual(reject_resp.data['notes'], 'Invalid document')

        driver = CustomUser.objects.get(username='driver3')
        self.assertFalse(driver.driver_profile.verified)

    def test_taxi_creation_permissions(self):
        driver_resp = self.register_user('driver4', 'driver4@example.com', 'DriverPass987!', 'driver')
        self.assertEqual(driver_resp.status_code, status.HTTP_201_CREATED)

        passenger_resp = self.register_user('pass2', 'pass2@example.com', 'Pass5678!', 'passenger')
        self.assertEqual(passenger_resp.status_code, status.HTTP_201_CREATED)

        admin_user = CustomUser.objects.create_user(username='admin4', email='admin4@example.com', password='AdminPass987!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        driver_access = self.obtain_token('driver4', 'DriverPass987!').data['access']
        passenger_access = self.obtain_token('pass2', 'Pass5678!').data['access']
        admin_access = self.obtain_token('admin4', 'AdminPass987!').data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {passenger_access}')
        passenger_taxi_resp = self.client.post('/api/taxis/', data={'plate_number': 'PASS-123', 'model': 'Hyundai', 'capacity': 4}, format='json')
        self.assertEqual(passenger_taxi_resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_access}')
        admin_taxi_resp = self.client.post('/api/taxis/', data={'plate_number': 'ADMIN-123', 'model': 'Mercedes', 'capacity': 4}, format='json')
        self.assertEqual(admin_taxi_resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {driver_access}')
        driver_taxi_resp = self.client.post('/api/taxis/', data={'plate_number': 'LT4567B', 'brand': 'Toyota', 'model': 'Toyota', 'capacity': 4}, format='json')
        self.assertEqual(driver_taxi_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(driver_taxi_resp.data['owner']['id'], driver_resp.data['id'])

    def test_biometric_verification_flow(self):
        driver_resp = self.register_user('driver2', 'driver2@example.com', 'DriverPass456!', 'driver')
        self.assertEqual(driver_resp.status_code, status.HTTP_201_CREATED)

        driver_token_resp = self.obtain_token('driver2', 'DriverPass456!')
        self.assertEqual(driver_token_resp.status_code, status.HTTP_200_OK)
        driver_access = driver_token_resp.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {driver_access}')
        selfie = SimpleUploadedFile('selfie.jpg', b'fake-image-content', content_type='image/jpeg')
        reference = SimpleUploadedFile('reference.jpg', b'fake-image-content', content_type='image/jpeg')
        bio_resp = self.client.post('/api/biometric/', data={'selfie': selfie, 'reference': reference}, format='multipart')
        self.assertEqual(bio_resp.status_code, status.HTTP_201_CREATED)
        bio_id = bio_resp.data['id']
        self.assertEqual(bio_resp.data['status'], 'pending')

        admin_user = CustomUser.objects.create_user(username='admin2', email='admin2@example.com', password='AdminPass456!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_token_resp = self.obtain_token('admin2', 'AdminPass456!')
        self.assertEqual(admin_token_resp.status_code, status.HTTP_200_OK)
        admin_access = admin_token_resp.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_access}')
        verify_resp = self.client.post(f'/api/biometric/{bio_id}/verify/')
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertIn(verify_resp.data['status'], ('verified', 'failed'))

        driver = CustomUser.objects.get(username='driver2')
        profile = driver.driver_profile
        if verify_resp.data['status'] == 'verified':
            self.assertTrue(profile.verified)
        else:
            self.assertFalse(profile.verified)
