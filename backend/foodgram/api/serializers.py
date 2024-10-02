import base64

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from recipes.models import (
    Favorite, Ingredient, Recipe,
    RecipeIngredient, ShoppingList, Tag
)


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    '''Переопределенная модель поля сериализаторов для картинок.'''
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта users.'''
    password = serializers.CharField(
        write_only=True,
        validators=[
            MinLengthValidator(settings.MIN_LENGTH_PASSWORD),
            MaxLengthValidator(settings.MAX_LENGTH_PASSWORD)
        ]
    )
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        '''Отображение на кого подписан.'''
        user = self.context.get('request').user
        return user.is_authenticated and user.is_subscribed(obj)

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password')
        )
        return super(UserSerializer, self).create(validated_data)

# New
    def to_representation(self, instance):
        request = self.context.get('request', None)
        if request.method == 'POST':
            return {
                'email': instance.email,
                'id': instance.id,
                'username': instance.username,
                'first_name': instance.first_name,
                'last_name': instance.last_name
            }
        else:
            return super().to_representation(instance)


class SetPasswordSerializer(serializers.Serializer):
    '''Сериализатор для эндпоинта users/set_password/.'''
    current_password = serializers.CharField(
        validators=[
            MinLengthValidator(settings.MIN_LENGTH_PASSWORD),
            MaxLengthValidator(settings.MAX_LENGTH_PASSWORD)
        ],
        write_only=True,
        required=True
    )
    new_password = serializers.CharField(
        validators=[
            MinLengthValidator(settings.MIN_LENGTH_PASSWORD),
            MaxLengthValidator(settings.MAX_LENGTH_PASSWORD)
        ],
        write_only=True,
        required=True
    )


class LoginSerializer(serializers.Serializer):
    '''Сериализатор для эндпоинта auth/token/login/.'''
    email = serializers.CharField(
        max_length=settings.MAX_LENGTH_EMAIL,
        write_only=True,
        required=True
    )
    password = serializers.CharField(
        validators=[
            MinLengthValidator(settings.MIN_LENGTH_PASSWORD),
            MaxLengthValidator(settings.MAX_LENGTH_PASSWORD)
        ],
        write_only=True,
        required=True
    )


class TagSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта tag.'''
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта ingredients.'''
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    '''Вкладываемый сериализатор для RecipeSerializer.'''
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = instance.ingredient.id
        representation['name'] = instance.ingredient.name
        representation['measurement_unit'] = instance.ingredient.measurement_unit
        representation['amount'] = instance.amount
        return representation


class RecipeSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта recipes.'''
    author = UserSerializer(read_only=True)
    image = Base64ImageField(required=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
    )
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipeingredient_set',
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        '''Есть ли рецепт в избранном.'''
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(
            user=user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        '''Есть ли рецепт в списке покупок.'''
        user = self.context['request'].user
        return user.is_authenticated and ShoppingList.objects.filter(
            owner=user,
            recipe=obj
        ).exists()

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                detail='Обязательное поле.'
            )
        ingredient_ids = {ingredient.get('id') for ingredient in ingredients}
        if len(ingredient_ids) != len(ingredients):
            raise serializers.ValidationError(
                'Нельзя передавать два одинаковых ингредиента.'
            )
        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                detail='Обязательное поле.'
            )
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                'Нельзя передавать два одинаковых тега.'
            )
        return tags

    def create(self, validated_data):
        tags_list = validated_data.pop('tags')
        ingredients_list = validated_data.pop('recipeingredient_set')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_list)
        for ingredient_dict in ingredients_list:
            ingredient_id = ingredient_dict.get('id')
            amount = ingredient_dict.get('amount')
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id.id)
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        tags_list = validated_data.pop('tags', None)
        ingredients_list = validated_data.pop('recipeingredient_set', None)
        if tags_list:
            instance.tags.set(tags_list, clear=True)
        if ingredients_list:
            RecipeIngredient.objects.filter(recipe=instance).delete()
            for ingredient_dict in ingredients_list:
                ingredient_id = ingredient_dict.get('id')
                amount = ingredient_dict.get('amount')
                ingredient = get_object_or_404(Ingredient, pk=ingredient_id.id)
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=amount
                )
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(instance.tags, many=True).data
        return representation


class ShortRecipeSerializer(serializers.ModelSerializer):
    '''
    Вкладываемый сериализатор для SubscriptionsSerializer.
    А так же используется в представлениях для добавления/удаления
    в избранное и список покупок.
    Выводит в ответе краткое содержимое рецепта.
    '''
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionsSerializer(UserSerializer):
    '''Сериализатор для эндпоинта users/subscriptions/.'''
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )

    def to_representation(self, instance):
        return super(
            serializers.ModelSerializer, self
        ).to_representation(instance)

    def get_recipes_count(self, obj):
        '''Считает кол-во рецептов пользователя.'''
        return obj.recipes.all().count()

    def get_recipes(self, obj):
        '''Выводит все рецепты пользователя.'''
        recipes_limit = self.context.get('recipes_limit')
        queryset = obj.recipes.all()
        if recipes_limit:
            queryset = queryset[:int(recipes_limit)]
        return ShortRecipeSerializer(queryset, many=True).data
