'''Tests for recipe API'''

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    '''Create and returna recipe detail URL'''
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    '''Create and return an image upload URL'''
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    '''Create and return a sample recipe'''
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 15,
        'price': Decimal('56.25'),
        'description': 'Sample descriptions',
        'link': 'http://example.com',
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    '''Create and return a new user'''
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITest(TestCase):
    '''Testing unauthenticated API request'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test to ensure auth is required to call API'''
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITest(TestCase):
    '''Test authenticated API request'''

    def setUp(self):
        self.user = create_user(email='user@example.com', password='random123')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrive_recipes(self):
        '''Test to retrive a list of recipes'''
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        '''Test to retrive list of recipes to the owner'''
        other_user = create_user(
            email='user2@example.com',
            password='random123'
            )
        create_recipe(user=self.user)
        create_recipe(user=other_user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        '''Test to get recipe detail'''
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        '''Test to create a recipe'''
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 15,
            'price': Decimal('56.25'),
            'description': 'Sample descriptions',
            'link': 'http://example.com',
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key, value in payload.items():
            self.assertEqual(value, getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_partial_update_of_recipe(self):
        '''Test to partial update a recipe'''
        original_link = 'https://exampl.com'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link,
        )

        payload = {'title': 'New title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        '''Test to fully update a recipe'''
        recipe = create_recipe(user=self.user)
        payload = {
            'title': 'New title',
            'link': 'https://xyz.com',
            'time_minutes': 25,
            'price': Decimal('51.6'),
            'description': 'New description',
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        '''Test changing the recipe user is not allowed'''
        new_user = create_user(email='new@example.com', password='random123')
        recipe = create_recipe(user=self.user)
        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        '''Test to delete a recipe'''
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_user_recipe_error(self):
        '''Test trying to delete another users recipe gives error'''
        new_user = create_user(email='new@example.com', password='random123')
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        '''Test creating a recipe with new tags'''
        payload = {
            'title': 'Title',
            'link': 'https://xyz.com',
            'time_minutes': 25,
            'price': Decimal('51.6'),
            'tags': [{'name': 'Tag1'}, {'name': 'Tag2'}],
            'description': 'New description',
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(name=tag['name']).exists())

    def test_create_recipe_with_existing_tags(self):
        '''Test to create recipe with existing tags'''
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        payload = {
            'title': 'Title',
            'link': 'https://xyz.com',
            'time_minutes': 25,
            'price': Decimal('51.6'),
            'tags': [{'name': 'Tag1'}, {'name': 'Tag2'}],
            'description': 'New description',
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag1, recipe.tags.all())
        for tag in payload['tags']:
            self.assertTrue(recipe.tags
                            .filter(user=self.user, name=tag['name']).exists())

    def test_create_tag_on_update(self):
        '''Test creating tag when updating a recipe'''
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Tag1'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Tag1')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        '''Test to assign existing tag when updating a recipe'''
        existing_tag = Tag.objects.create(user=self.user, name='Old tag')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(existing_tag)

        other_tag = Tag.objects.create(user=self.user, name='Other tag')
        payload = {'tags': [{'name': 'Other tag'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(other_tag, recipe.tags.all())
        self.assertNotIn(existing_tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        '''Test to clear recipe tag'''
        tag = Tag.objects.create(user=self.user, name='Tag')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredient(self):
        '''Test to create recipe with new ingredient'''
        payload = {
            'title': 'Title',
            'link': 'https://xyz.com',
            'time_minutes': 25,
            'price': Decimal('51.6'),
            'ingredients': [{'name': 'Ing1'}, {'name': 'Ing2'}],
            'description': 'New description',
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ing in payload['ingredients']:
            self.assertTrue(recipe.ingredients
                            .filter(user=self.user, name=ing['name']).exists())

    def test_create_recipe_with_existing_ingredients(self):
        '''Test to create recipe with existing ingredients'''
        Ingredient.objects.create(user=self.user, name='Old ing')
        payload = {
            'title': 'Title',
            'link': 'https://xyz.com',
            'time_minutes': 25,
            'price': Decimal('51.6'),
            'ingredients': [{'name': 'Old ing'}, {'name': 'Ing2'}],
            'description': 'New description',
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ing in payload['ingredients']:
            self.assertTrue(recipe.ingredients
                            .filter(user=self.user, name=ing['name']).exists())

    def test_create_ingredient_on_update(self):
        '''Test to create ingredient on recipe update'''
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        payload = {'ingredients': [{'name': 'Ing1'}]}
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ing = Ingredient.objects.get(user=self.user, name='Ing1')
        self.assertIn(new_ing, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        '''Test to assign existing ingredient when updating a recipe'''
        old_ing = Ingredient.objects.create(user=self.user, name='Old_ing')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(old_ing)

        new_ing = Ingredient.objects.create(user=self.user, name='New ing')
        payload = {'ingredients': [{'name': 'New ing'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(new_ing, recipe.ingredients.all())
        self.assertNotIn(old_ing, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        '''Test to clear recipe ingredients'''
        new_ing = Ingredient.objects.create(user=self.user, name='Ing')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(new_ing)
        payload = {'ingredients': []}
        url = detail_url(recipe.id)

        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        '''Test filtering recipes by tags'''
        r1 = create_recipe(user=self.user, title='Recipe1')
        r2 = create_recipe(user=self.user, title='Recipe2')
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='Recipe3')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        '''Test filtering recipes by ingredients'''
        r1 = create_recipe(user=self.user, title='Recipe1')
        r2 = create_recipe(user=self.user, title='Recipe2')
        ing1 = Ingredient.objects.create(user=self.user, name='Ing1')
        ing2 = Ingredient.objects.create(user=self.user, name='Ing2')
        r1.ingredients.add(ing1)
        r2.ingredients.add(ing2)
        r3 = create_recipe(user=self.user, title='Recipe3')

        params = {'ingredients': f'{ing1.id},{ing2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    '''Test for image upload API'''

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='random123'
            )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        '''Test uploading an image to recipe'''
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        '''Test uploading invalid image'''
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'not an image'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
