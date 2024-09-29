"""Tests for user API"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL= reverse('user:create')
TOKEN_URL= reverse('user:token')
ME_URL= reverse('user:me')

def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Testing public features"""

    def setUp(self):
        self.client= APIClient()

    def test_create_user_success(self):
        """Testing successful creation of user"""
        payload= {
            'email':'test@example.com',
            'password':'random123',
            'name':'Test',
        }
        res= self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user= get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists(self):
        """Testing if email is already registered"""
        payload= {
            'email':'test@example.com',
            'password':'random123',
            'name':'Test',
        }
        create_user(**payload)
        res= self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_password_error(self):
        """Password is too short i.e. less than 5 char"""
        payload= {
            'email':'test@example.com',
            'password':'pw',
            'name':'Test',
        }
        res= self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists= get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Generates token for valid credentials"""
        user_details= {
            'name':'Test',
            'email':'test@example.com',
            'password':'random123'
        }
        create_user(**user_details)

        payload= {
            'email':user_details['email'],
            'password':user_details['password'],
        }
        res= self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Return error if credentials is invalid"""
        create_user(email='test@example.com', password='goodpass')

        payload= {'email':'test@example.com', 'password': 'badpass'}
        res= self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Return error for blank password"""
        payload= {'email':'test@example.com', 'password':''}
        res= self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Testing authentication requirement for users"""
        res= self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    '''Testing API requests that require authentication'''

    def setUp(self):
        self.user= create_user(
            email='test@example.com',
            password='random123',
            name='Test',
        )
        self.client= APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        '''Testing profile retrieval for logged in user'''
        res= self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name':self.user.name,
            'email':self.user.email,
        })

    def test_post_me_not_allowed(self):
        '''Testing post request not allowed for me endpoint'''
        res= self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        '''Test updating the user profile for the authenticated user'''
        payload={
            'name':'Updated Test',
            'password': 'newrandom123',
        }
        res= self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)