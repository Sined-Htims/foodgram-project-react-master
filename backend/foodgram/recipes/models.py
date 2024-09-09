from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from recipes.validators import HexValidator

User = get_user_model()


class Tag(models.Model):
    '''Модель тэгов'''
    name = models.CharField(
        verbose_name='Название',
        max_length=settings.MAX_LENGTH_TEG,
        unique=True
    )
    color = models.CharField(
        verbose_name='Цветовой HEX-код',
        max_length=settings.MAX_LENGTH_HEX_COLOR,
        unique=True,
        # Валидатор для проверки в каком виде передан цвет
        validators=[HexValidator]
    )
    slug = models.SlugField(
        verbose_name='Уникальное имя',
        max_length=settings.MAX_LENGTH_TEG,
        unique=True
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    '''Модель ингредиентов'''
    name = models.CharField(
        verbose_name='Продукт',
        unique=True,  # Походу не должен быть uniq, из-за импорта
        max_length=settings.MAX_LENGTH_INGREDIENT
    )
    measurement_unit = models.CharField(
        verbose_name='Система измерения',
        max_length=settings.MAX_LENGTH_INGREDIENT
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    '''Модель рецептов'''
    name = models.CharField(
        verbose_name='Название',
        max_length=settings.MAX_LENGTH_RECIPES
    )
    image = models.ImageField(
        verbose_name='Изображение',
        # Путь куда сохраняется загруженные файлы
        # основная папка указана в settings.py
        upload_to='recipes/images/'
    )
    text = models.TextField(verbose_name='Описание')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[MinValueValidator(1)]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    tags = models.ManyToManyField(
        Tag,
        through='RecipeTag',
        verbose_name='Тэги'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


# Обсудить метод удаления!
class RecipeTag(models.Model):
    '''Промежуточная таблица тэгов для модели "Recipe"'''
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепты'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тэги'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Таблица рецептов и тэгов'
        verbose_name_plural = 'Таблица рецептов и тэгов'

    def __str__(self):
        return f'Для "{self.recipe}", установлен тэг "{self.tag}"'


class RecipeIngredient(models.Model):
    '''Промежуточная таблица ингредиентов для модели "Recipe"'''
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепты'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиенты'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Таблица рецептов и ингредиентов'
        verbose_name_plural = 'Таблица рецептов и ингредиентов'


class Favorite(models.Model):
    '''Модель избранных рецептов'''
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe',
        verbose_name='Рецепт'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        # Ограничение на уникальность пары:
        # Пользователь - рецепт.
        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f'{self.user}, добавил в избранное "{self.recipe.name}"'


class ShoppingList(models.Model):
    '''Модель списка покупок'''
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='owner',
        unique=True,
        verbose_name='Пользователь'
    )
    recipe = models.ManyToManyField(
        Recipe,
        through='RecipeShoppingList',
        verbose_name='Рецепты'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return f'Список покупок пользователя: "{self.owner}"'


class RecipeShoppingList(models.Model):
    '''Промежуточная таблица рецептов для модели "ShoppingList"'''
    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        verbose_name='Список покупок'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Таблица списка покупок и рецептов'
        verbose_name_plural = 'Таблица списка покупок и рецептов'
        # Ограничение на уникальность пары:
        # Список покупок - рецепт.
        constraints = [
            UniqueConstraint(
                fields=['shopping_list', 'recipe'],
                name='unique_shopping_list'
            )
        ]

    def __str__(self):
        return f'"{self.shopping_list.owner}", добавил "{self.recipe}" в свой список покупок'
