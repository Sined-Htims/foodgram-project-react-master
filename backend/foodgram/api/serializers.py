# Для Base64ImageField
import base64

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
# Для Base64ImageField
from django.core.files.base import ContentFile
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    RecipeTag, ShoppingList, Tag
)


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    '''Переопределенная модель поля сериализаторов для картинок'''
    def to_internal_value(self, data):
        # Если полученный объект строка, и эта строка
        # начинается с 'data:image'...
        if isinstance(data, str) and data.startswith('data:image'):
            # ...начинаем декодировать изображение из base64.
            # Разделяем строку на части.
            format, imgstr = data.split(';base64,')
            # Извлекаем расширение файла.
            ext = format.split('/')[-1]
            # Декодируем данные и помещаем результат в файл,
            # которому даем название по шаблону.
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


# Users
class UserSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта users'''
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
        '''Отображение на кого подписан'''
        user = self.context.get('request').user
        return user.is_authenticated and user.is_subscribed(obj)

    def create(self, validated_data):
        # Хешируем полученный пароль
        validated_data['password'] = make_password(
            validated_data.get('password')
        )
        return super(UserSerializer, self).create(validated_data)


class SetPasswordSerializer(serializers.Serializer):
    '''Сериализатор для эндпоинта users/set_password/'''
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
    '''Сериализатор для эндпоинта auth/token/login/'''
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


# Tag
class TagSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта tags'''
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


# Ingredient
class IngredientSerializer(serializers.ModelSerializer):
    '''Сериализатор для эндпоинта ingredients'''
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


# Recipes
# Ingredient'ы получаемые из промежуточной модели RecipeIngredient
class RecipeIngredientSerializer(serializers.ModelSerializer):
    '''Вкладываемый сериализатор для RecipeSerializer'''
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
    '''Сериализатор для эндпоинта recipes'''
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
        '''Есть ли рецепт в избранном'''
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(
            user=user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        '''Есть ли рецепт в списке покупок'''
        user = self.context['request'].user
        return user.is_authenticated and ShoppingList.objects.filter(
            owner=user,
            recipe=obj
        ).exists()

    def create(self, validated_data):
        # Получаем список объектов модели из словаря
        tags_list = validated_data.pop('tags')
        # Проверка на то что tags_list не пустой
        if not tags_list:
            raise serializers.ValidationError(
                detail={'tags': 'Обязательное поле.'}
            )
        # Получаем список словарей, т.к. в source указано recipeingredient_set
        # вызываем удаление элемента не с ingredients а с recipeingredient_set
        ingredients_list = validated_data.pop('recipeingredient_set')
        # Проверка на то что ingredients_list не пустой
        if not ingredients_list:
            raise serializers.ValidationError(
                detail={'ingredients': 'Обязательное поле.'}
            )
        recipe = Recipe.objects.create(**validated_data)
        # Передаем объект модели из списка в переменную tag_obj
        for tag_obj in tags_list:
            tag = get_object_or_404(Tag, pk=tag_obj.id)
            RecipeTag.objects.create(recipe=recipe, tag=tag)
        # Передаем словарь с объектами модели,
        # из списка в переменную ingredient_dict
        for ingredient_dict in ingredients_list:
            # Получаем объект модели из словаря
            ingredient_id = ingredient_dict.get('id')
            # Получаем кол-во из словаря
            amount = ingredient_dict.get('amount')
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id.id)
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        tags_list = validated_data.pop('tags')
        if not tags_list:
            raise serializers.ValidationError(
                detail={'tags': 'Обязательное поле.'}
            )
        ingredients_list = validated_data.pop('recipeingredient_set')
        if not ingredients_list:
            raise serializers.ValidationError(
                detail={'ingredients': 'Обязательное поле.'}
            )
        RecipeTag.objects.filter(recipe=instance).delete()
        RecipeIngredient.objects.filter(recipe=instance).delete()
        for tag_obj in tags_list:
            tag = get_object_or_404(Tag, pk=tag_obj.id)
            RecipeTag.objects.create(recipe=instance, tag=tag)
        for ingredient_dict in ingredients_list:
            ingredient_id = ingredient_dict.get('id')
            amount = ingredient_dict.get('amount')
            # Нужно ли проверять существование?
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id.id)
            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient,
                amount=amount
            )
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
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
    Выводит в ответе краткое содержимое рецепта
    '''
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


# Subscription
class SubscriptionsSerializer(UserSerializer):
    '''Сериализатор для эндпоинта users/subscriptions/'''
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

    def get_recipes_count(self, obj):
        '''Считает кол-во рецептов пользователя'''
        return obj.recipes.all().count()

    def get_recipes(self, obj):
        '''Выводит все рецепты пользователя'''
        return ShortRecipeSerializer(obj.recipes.all(), many=True).data
