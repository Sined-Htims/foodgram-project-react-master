from django.contrib import admin
from recipes.models import (
    Favorite, Ingredient, Recipe,
    RecipeIngredient, RecipeShoppingList, RecipeTag,
    ShoppingList, Tag,
)


class FavoriteAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Избранное" в админке'''
    search_fields = ('user__username',)
    list_display = ('__str__', 'user', 'recipe')


admin.site.register(Favorite, FavoriteAdmin)


class IngredientAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Ингредиенты" в админке'''
    list_display = ('name', 'measurement_unit')
    search_fields = ('name', )


admin.site.register(Ingredient, IngredientAdmin)


class RecipeIngredientInline(admin.TabularInline):
    '''
    Вставка промежуточной модели "Рецепты-ингредиенты"
    для модели "Рецепты" в админке
    '''
    model = RecipeIngredient
    extra = 1


class RecipeTagInline(admin.TabularInline):
    '''
    Вставка промежуточной модели "Рецепты-тэги"
    для модели "Рецепты" в админке
    '''
    model = RecipeTag
    extra = 1


class RecipeAdmin(admin.ModelAdmin):
    '''
    Поиск, дополнительные промежуточные модели, фильтры, и отображение
    для модели "Рецепты" в админке
    '''
    inlines = [RecipeIngredientInline, RecipeTagInline]
    list_display = ('name', 'author', 'get_favorite_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags', )

    def get_favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    get_favorite_count.short_description = 'Вайки'


admin.site.register(Recipe, RecipeAdmin)


class RecipeIngredientAdmin(admin.ModelAdmin):
    '''
    Поиск и отображение для промежуточной модели
    "Рецепты-ингредиенты" в админке
    '''
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


admin.site.register(RecipeIngredient, RecipeIngredientAdmin)


class RecipeShoppingListAdmin(admin.ModelAdmin):
    '''
    Поиск и отображение для промежуточной модели
    "Рецепты-список покупок" в админке
    '''
    search_fields = ('shopping_list__owner__username',)
    list_display = ('__str__', 'shopping_list', 'recipe')


admin.site.register(RecipeShoppingList, RecipeShoppingListAdmin)


class RecipeTagAdmin(admin.ModelAdmin):
    '''
    Фильтры и отображение для промежуточной модели
    "Рецепты-тэги" в админке
    '''
    list_filter = ('tag',)
    list_display = ('__str__', 'recipe', 'tag')


admin.site.register(RecipeTag, RecipeTagAdmin)


class ShoppingListInline(admin.TabularInline):
    '''
    Вставка промежуточной модели "Рецепты-список покупок"
    для модели "Рецепты" в админке
    '''
    model = RecipeShoppingList
    extra = 1


class ShoppingListAdmin(admin.ModelAdmin):
    '''
    Поиск и дополнительная промежуточная модель,
    для модели "Список покупок" в админке
    '''
    inlines = [ShoppingListInline]
    search_fields = ('owner__username',)


admin.site.register(ShoppingList, ShoppingListAdmin)


class TagAdmin(admin.ModelAdmin):
    '''Поиск и отображение для модели "Тэги" в админке'''
    list_display = ('name', 'color', 'slug')
    search_fields = ('name',)


admin.site.register(Tag, TagAdmin)
