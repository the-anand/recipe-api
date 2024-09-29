from rest_framework import serializers

from core.models import Recipe, Tag, Ingredient


class TagSerializer(serializers.ModelSerializer):
    '''Serializer for tags'''

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    '''Serializer for recipe'''
    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = [
            'id',
            'title',
            'time_minutes',
            'price',
            'link',
            'tags',
            'ingredients']
        read_only_fields = ['id']

    def _get_or_create_tags(self, tags, recipe):
        '''Hanling getting or creating tags as needed'''
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(user=auth_user, **tag)
            recipe.tags.add(tag_obj)

    def _get_or_create_ingredients(self, ingredients, recipe):
        '''Handling getting or creating ingredients as needed'''
        auth_user = self.context['request'].user
        for ingredient in ingredients:
            ing_obj, created = Ingredient.objects \
                .get_or_create(user=auth_user, **ingredient)
            recipe.ingredients.add(ing_obj)

    def create(self, validated_data):
        '''Logic to create nested serializer tags'''
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)
        self._get_or_create_ingredients(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        '''Logic to update nested serializer tags'''
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        ingredients = validated_data.pop('ingredients', None)
        if ingredients is not None:
            instance.ingredients.clear()
            self._get_or_create_ingredients(ingredients, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    '''Serializer for a recipe detail'''

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description', 'image']


class RecipeImageSerializer(serializers.ModelSerializer):
    '''Serializer to upload images to recipe'''

    class Meta:
        model = Recipe
        fields = ['id', 'image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}
