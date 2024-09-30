from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api.filters import RecipeFilter, IngredientFilter
from api.permissions import IsAuthor
from api.services import create_ingredients_pdf
from api.serializers import (
    IngredientSerializer, LoginSerializer, RecipeSerializer,
    SetPasswordSerializer, ShortRecipeSerializer, SubscriptionsSerializer,
    TagSerializer, UserSerializer
)
from recipes.models import (
    Favorite, Ingredient, Recipe,
    ShoppingList, RecipeIngredient,
    RecipeShoppingList, Tag
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    '''Представление для эндпоинта users.'''
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post']

    def get_permissions(self):
        if self.action == 'create':
            return (permissions.AllowAny(),)
        return super().get_permissions()

    @action(
        methods=['GET'],
        detail=False,
        url_path='me',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def user_me(self, request: Request):
        '''
        View-функция для эндпоинта users/me/.
        Получает данные текущего пользователя.
        '''
        user = request.user
        serializer = self.get_serializer(user)
        return Response(data=serializer.data)

    @action(
        methods=['POST'],
        detail=False,
        url_path='set_password',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def set_password(self, request: Request):
        '''
        View-функция для эндпоинта users/set_password/.
        Меняет текущий пароль пользователя, на новый.
        '''
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        current_password = serializer.validated_data.get('current_password')
        new_password = serializer.validated_data.get('new_password')
        if user.check_password(current_password):
            user.auth_token.delete()
            user.set_password(new_password)
            user.save(update_fields=['password'])
            return Response(
                data={'message': 'Пароль успешно изменен.'},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        methods=['GET'],
        detail=False,
        url_path='subscriptions',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def user_subscriptions(self, request: Request):
        '''
        View-функция для эндпоинта users/subscriptions/.
        Получает список пользователей на которых
        подписан текущий пользователь.
        '''
        user = request.user
        subscriptions = user.following.all()
        page = self.paginate_queryset(subscriptions)
        serializer = SubscriptionsSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def subscribe(request: Request, user_id: int):
    '''
    View-функция для эндпоинта users/{id}/subscribe/.
    Подписывает/отписывает пользователя на/от другого ползователя.
    '''
    user = request.user
    user_to_follow = get_object_or_404(User, pk=user_id)
    serializer = SubscriptionsSerializer(
        user_to_follow,
        context={'request': request}
    )
    if request.method == 'POST':
        user.subscribe(user_to_follow)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
    if not user.is_subscribed(user_to_follow):
        return Response(
            data={'error': 'Вы не были подписаны на этого пользователя.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    user.unsubscribe(user_to_follow)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request: Request):
    '''
    Представление для авторизации пользователя.
    (Получение токена авторизации).
    '''
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data.get('email')
    password = serializer.validated_data.get('password')
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            data={'error': 'Проверьте корректность веденных данных'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if user.check_password(password):
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            data={'auth_token': token.key},
            status=status.HTTP_200_OK
        )
    return Response(
        data={'error': 'Проверьте корректность веденных данных'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request: Request):
    '''Представление для завершения сессии пользователя.'''
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    '''Представление для эндпоинта tags.'''
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    '''Представление для эндпоинта recipes.'''
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsAuthor)
    http_method_names = ['get', 'post', 'delete', 'patch']
    filter_backends = (DjangoFilterBackend,)
    filter_class = RecipeFilter

    def get_permissions(self):
        if self.action == 'retrieve':
            return (permissions.IsAuthenticatedOrReadOnly(),)
        return super().get_permissions()

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request: Request, pk):
        '''
        View-функция для эндпоинта recipe/{id}/favorite/.
        Добавляет/удаляет рецепт из избранного.
        '''
        user = request.user
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=pk)
            except Recipe.DoesNotExist:
                return Response(
                    data={'error': 'Рецепт не найден'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = ShortRecipeSerializer(
                recipe,
                context={'request': request}
            )
            Favorite.objects.create(user=user, recipe=recipe)
            return Response(
                data=serializer.data,
                status=status.HTTP_201_CREATED
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShortRecipeSerializer(
            recipe,
            context={'request': request}
        )
        try:
            Favorite.objects.get(user=user, recipe=recipe).delete()
        except Favorite.DoesNotExist:
            return Response(
                data={'error': 'Данный рецепт отсутствует в вашем списке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request: Request, pk):
        '''
        View-функция для эндпоинта recipe/{id}/shopping_cart/.
        Добавляет/удаляет рецепт из списка покупок.
        '''
        user = request.user
        shopping_list_obj, _ = ShoppingList.objects.get_or_create(
            owner=user
        )
        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(pk=pk)
            except Recipe.DoesNotExist:
                return Response(
                    data={'error': 'Рецепт не найден'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = ShortRecipeSerializer(
                recipe,
                context={'request': request}
            )
            RecipeShoppingList.objects.create(
                shopping_list=shopping_list_obj,
                recipe=recipe
            )
            return Response(
                data=serializer.data,
                status=status.HTTP_201_CREATED
            )
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShortRecipeSerializer(
            recipe,
            context={'request': request}
        )
        try:
            RecipeShoppingList.objects.get(
                shopping_list=shopping_list_obj,
                recipe=recipe
            ).delete()
        except RecipeShoppingList.DoesNotExist:
            return Response(
                data={'error': 'Данный рецепт отсутствует в вашем списке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['GET'],
        detail=False,
        url_path='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request: Request):
        '''
        View-функция для эндпоинта recipe/{id}/download_shopping_cart/.
        Выдает PDF-файл для скачивания.
        '''
        shopping_list = get_object_or_404(
            ShoppingList,
            owner=request.user
        )
        recipe_shopping_list = RecipeShoppingList.objects.filter(
            shopping_list=shopping_list
        )
        ingredients: dict[str, str | int] = {}
        for rsl in recipe_shopping_list:
            recipe_ingredients = RecipeIngredient.objects.filter(
                recipe=rsl.recipe
            )
            for ri in recipe_ingredients:
                ingredient_name = ri.ingredient.name
                ingredient_unit = ri.ingredient.measurement_unit
                if (ingredient_name, ingredient_unit) in ingredients:
                    ingredients[(ingredient_name, ingredient_unit)] += ri.amount
                else:
                    ingredients[(ingredient_name, ingredient_unit)] = ri.amount
        return create_ingredients_pdf(ingredients)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    '''Представление для эндпоинта ingredients.'''
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)
