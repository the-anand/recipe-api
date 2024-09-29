'''Test for ingredients API'''
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse('recipe:ingredient-list')


def create_user(email='test@example.com', password='random123'):
    return get_user_model().objects.create_user(email, password)


def detail_url(ing_id):
    return reverse('recipe:ingredient-detail', args=[ing_id])


class PublicIngredientAPITest(TestCase):
    '''Test unauthorized API request'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test authentication required for retrieving ingredient list'''
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITest(TestCase):
    '''Test authenticated API request'''
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredient_list(self):
        '''Test to retrieve ingredient list'''
        Ingredient.objects.create(user=self.user, name='Ing1')
        Ingredient.objects.create(user=self.user, name='Ing2')

        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        '''Test to retrieve ingredient list restricted to authenticated user'''
        new_user = create_user(email='random@example.com')
        Ingredient.objects.create(user=new_user, name='Ing')
        ingredient = Ingredient.objects.create(user=self.user, name='ing2')

        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        '''Test to update ingredient'''
        ingredient = Ingredient.objects.create(user=self.user, name='Ing')
        payload = {'name': 'Ing new'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(payload['name'], ingredient.name)

    def test_ingredient_delete(self):
        '''Test to delete ingredient'''
        ingredient = Ingredient.objects.create(user=self.user, name='Ing')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(user=self.user).exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        '''Test listing ingredients by those assigned to recipes'''
        ing1 = Ingredient.objects.create(user=self.user, name='Ing1')
        ing2 = Ingredient.objects.create(user=self.user, name='Ing2')
        recipe = Recipe.objects.create(
            title='Title',
            link='https://xyz.com',
            time_minutes=25,
            price=Decimal('51.6'),
            description='New description',
            user=self.user
        )
        recipe.ingredients.add(ing1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredoents_unique(self):
        '''Test filtered ingredients returns a unique list'''
        ing = Ingredient.objects.create(user=self.user, name='Ing1')
        Ingredient.objects.create(user=self.user, name='Ing2')
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
        r1.ingredients.add(ing)
        r2.ingredients.add(ing)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
