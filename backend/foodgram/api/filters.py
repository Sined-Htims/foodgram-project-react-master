import django_filters
from django.db.models import QuerySet
from rest_framework.filters import SearchFilter

from recipes.models import Recipe, Tag


class RecipeFilter(django_filters.FilterSet):
    '''
    Фильтры для viewset'а RecipeViewSet, для полей:
    author, tags, is_in_shopping_cart, is_favorited.
    '''
    author = django_filters.CharFilter(field_name='author_id')
    tags = django_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug'
    )
    is_in_shopping_cart = django_filters.NumberFilter(
        field_name='is_in_shopping_cart',
        method='filter_cart_and_favorite'
    )
    is_favorited = django_filters.NumberFilter(
        field_name='is_favorited',
        method='filter_cart_and_favorite'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')

    def filter_cart_and_favorite(
        self, queryset: QuerySet, name: str, value: int,
    ) -> QuerySet:
        user = self.request.user
        if user.is_authenticated:
            if name == 'is_in_shopping_cart' and value == 1:
                return queryset.filter(shoppinglist__owner=user)
            if name == 'is_in_shopping_cart' and value == 0:
                return queryset.exclude(shoppinglist__owner=user)
            if name == 'is_favorited' and value == 1:
                return queryset.filter(favorite_recipes__user=user)
            if name == 'is_favorited' and value == 0:
                return queryset.exclude(favorite_recipes__user=user)
        return queryset


class IngredientFilter(SearchFilter):
    search_param = 'name'
