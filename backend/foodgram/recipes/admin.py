from django.contrib import admin
from recipes.models import (
    Favorite, Ingredient, Recipe,
    RecipeIngredient, RecipeShoppingList,
    ShoppingList, Tag
)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Избранное" в админке.'''
    search_fields = ('user__username',)
    list_display = ('__str__', 'user', 'recipe')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Ингредиенты" в админке.'''
    list_display = ('name', 'measurement_unit')
    search_fields = ('name', )


class RecipeIngredientInline(admin.TabularInline):
    '''
    Вставка промежуточной модели "Рецепты-ингредиенты"
    для модели "Рецепты" в админке.
    '''
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    '''
    Поиск, дополнительные промежуточные модели, фильтры, и отображение
    для модели "Рецепты" в админке.
    '''
    inlines = [RecipeIngredientInline,]
    list_display = ('name', 'author', 'get_favorite_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags', )

    def get_favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    get_favorite_count.short_description = 'Вайки'


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    '''
    Поиск и отображение для промежуточной модели
    "Рецепты-ингредиенты" в админке.
    '''
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(RecipeShoppingList)
class RecipeShoppingListAdmin(admin.ModelAdmin):
    '''
    Поиск и отображение для промежуточной модели
    "Рецепты-список покупок" в админке.
    '''
    search_fields = ('shopping_list__owner__username',)
    list_display = ('__str__', 'shopping_list', 'recipe')


class ShoppingListInline(admin.TabularInline):
    '''
    Вставка промежуточной модели "Рецепты-список покупок"
    для модели "Рецепты" в админке.
    '''
    model = RecipeShoppingList
    extra = 1


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    '''
    Поиск и дополнительная промежуточная модель,
    для модели "Список покупок" в админке.
    '''
    inlines = [ShoppingListInline]
    search_fields = ('owner__username',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Тэги" в админке.'''
    list_display = ('name', 'color', 'slug')
    search_fields = ('name',)
