'''Test for tags API'''
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    '''Creata and return a tag detail url'''
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='random123'):
    return get_user_model().objects.create_user(email, password)


class PublicTagsAPITests(TestCase):
    '''Test unauthenticated API requests'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test authentication required for retrieving tags'''
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITests(TestCase):
    '''Test authenticated Tags API requests'''

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        '''Test retrieving a list of tags'''
        Tag.objects.create(user=self.user, name='tag1')
        Tag.objects.create(user=self.user, name='Tag2')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        '''Test tag list is restrictd to authenticated user'''
        new_user = create_user('newuser@example.com')
        Tag.objects.create(user=new_user, name='Tag name')
        tag = Tag.objects.create(user=self.user, name='Only tag')

        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_tag_update(self):
        '''Test updating tag'''
        tag = Tag.objects.create(user=self.user, name='Tag1')
        payload = {'name': 'Newtag'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(payload['name'], tag.name)

    def test_tag_delete(self):
        '''Test to delete tag'''
        tag = Tag.objects.create(user=self.user, name='Tag1')
        url = detail_url(tag.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        '''Test listing tags by those assigned to recipes'''
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        recipe = Recipe.objects.create(
            title='Title',
            link='https://xyz.com',
            time_minutes=25,
            price=Decimal('51.6'),
            description='New description',
            user=self.user
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tagss_unique(self):
        '''Test filtered tags returns a unique list'''
        tag = Tag.objects.create(user=self.user, name='Tag1')
        Tag.objects.create(user=self.user, name='Tag2')
        r1 = Recipe.objects.create(
            title='Title1',
            link='https://xyz.com',
            time_minutes=25,
            price=Decimal('51.6'),
            description='New description',
            user=self.user
        )
        r2 = Recipe.objects.create(
            title='Title2',
            link='https://xyz.com',
            time_minutes=25,
            price=Decimal('51.6'),
            description='New description',
            user=self.user
        )
        r1.tags.add(tag)
        r2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
