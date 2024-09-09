from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api.functions import create_ingredients_pdf
from api.permissions import IsAuthor
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


# Users
class UserViewSet(viewsets.ModelViewSet):
    '''Представление для эндпоинта users'''
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
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
            user.save()
            return Response(
                data={'message': 'Пароль успешно изменен'},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            data=serializer.errors,  # Месседж о неправильном пароле
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
            context={'request': request}  # For work 65 строки в serializers.py
        )
        return self.get_paginated_response(serializer.data)

# БЫЛО:
# # keyword переделать в остальных
#     @action(
#         methods=['POST', 'DELETE'],
#         detail=False,
#         url_path='subscribe',
#         # permission_classes=(,)
#     )
#     def subscribe(self, request: Request, pk=None):
#         user = request.user
#         another_user_page_id = self.kwargs.get('pk')
#         another_user_page = get_object_or_404(User, pk=another_user_page_id)
#         serializer = SubscriptionsSerializer(
#            another_user_page,
#            context={'request': request}  # For work 65 строки в serializers
#         )
#         if request.method == 'POST':
#             if user == another_user_page:
#                 return Response(
#                     {'error': 'Невозможно подписаться на себя.'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             try:
#                 user.subscribe(another_user_page)
#             except IntegrityError:
#                 return Response(
#                     data={'error': 'Нельзя подписаться на пользователя два'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             return Response(data=serializer.data, status=status.HTTP_201_CREATED)
#         if not user.is_subscribed(another_user_page):
#             return Response(
#                 'Вы не были подписаны на этого пользователя',
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         user.unsubscribe(another_user_page)
#         # Будут ли другие статусы отображаться? Нужна и 400 (не был подписан)
#         return Response(status=status.HTTP_204_NO_CONTENT)


# СТАЛО:
@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def subscribe(request: Request, user_id: int):
    '''
    View-функция для эндпоинта users/{id}/subscribe/.
    Подписывает/отписывает пользователя на/от другого ползователя
    '''
    user = request.user
    another_user_page = get_object_or_404(User, pk=user_id)
    serializer = SubscriptionsSerializer(
        another_user_page,
        context={'request': request}  # For work 65 строки в serializers.py
    )
    if request.method == 'POST':
        if user == another_user_page:
            return Response(
                data={'error': 'Невозможно подписаться на себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user.subscribe(another_user_page)
        except IntegrityError:
            return Response(
                data={'error': 'Нельзя подписаться на пользователя дважды.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)
    if not user.is_subscribed(another_user_page):
        return Response(
            data={'error': 'Вы не были подписаны на этого пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )
    user.unsubscribe(another_user_page)
    # Будут ли другие статусы отображаться? Нужна и 400 (не был подписан)
    return Response(status=status.HTTP_204_NO_CONTENT)


# Статусы не верные
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request: Request):
    '''
    Представление для авторизации пользователя
    (Получение токена авторизации)
    '''
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data.get('email')
    password = serializer.validated_data.get('password')
    user = get_object_or_404(User, email=email)
    if user.check_password(password):
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            data={'auth_token': token.key},
            status=status.HTTP_201_CREATED
        )
    return Response(
        data=serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )  # Месседж о неправильном пароле или мыле


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request: Request):
    '''Представление для завершения сессии пользователя'''
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# Tag
class TagViewSet(viewsets.ModelViewSet):
    '''Представление для эндпоинта tags'''
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ['get']


# Recipes
class RecipeViewSet(viewsets.ModelViewSet):
    '''Представление для эндпоинта recipes'''
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsAuthor)
    http_method_names = ['get', 'post', 'delete', 'put']
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('tags',)

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
    def favorite(self, request: Request, pk=None):
        '''
        View-функция для эндпоинта recipe/{id}/favorite/.
        Добавляет/удаляет рецепт из избранного.
        '''
        user = request.user
        recipe_id = self.kwargs.get('pk')
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        serializer = ShortRecipeSerializer(
            recipe,
            context={'request': request}  # For work 65 строки в serializers.py
        )
        if request.method == 'POST':
            try:
                Favorite.objects.create(user=user, recipe=recipe)
            except IntegrityError:
                return Response(
                    data={'error': 'Вы уже добавили этот рецепт в избранное.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                data=serializer.data,
                status=status.HTTP_201_CREATED
            )
        #  Альтернатива для try
        # if not Favorite.objects.get(user=user, recipe=recipe).exists():
        #     return Response(
        #         'Данный рецепт не был в вашем списке избранного',
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # Favorite.objects.get(user=user, recipe=recipe).delete()
        # return Response(status=status.HTTP_204_NO_CONTENT)
        # Чем это
        try:
            Favorite.objects.get(user=user, recipe=recipe).delete()
        except ObjectDoesNotExist:  # из-за этого альтернатива
            return Response(
                data={'error': 'Данный рецепт отсутствует в вашем списке'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Будут ли другие статусы отображаться? Нужна и 400 (не был подписан)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request: Request, pk=None):
        '''
        View-функция для эндпоинта recipe/{id}/shopping_cart/.
        Добавляет/удаляет рецепт из списка покупок.
        '''
        user = request.user
        recipe_id = self.kwargs.get('pk')
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        serializer = ShortRecipeSerializer(
            recipe,
            context={'request': request}  # for work 65 строки в serializers.py
        )
        shopping_list_obj, _ = ShoppingList.objects.get_or_create(
                owner=user
            )
        if request.method == 'POST':
            try:
                RecipeShoppingList.objects.create(
                    shopping_list=shopping_list_obj,
                    recipe=recipe
                )
            except IntegrityError:
                return Response(
                    data={'error': 'Рецепт уже находится в вашем списке'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                data=serializer.data,
                status=status.HTTP_201_CREATED
            )
        #  Альтернатива для try
        # if not RecipeShoppingList.objects.get(
        #     shopping_list=shopping_list_obj, recipe=recipe
        # ).exists():
        #     return Response(
        #         'Данный рецепт не был в вашем списке покупок',
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # RecipeShoppingList.objects.get(
        #     shopping_list=shopping_list_obj, recipe=recipe
        # ).delete()
        # return Response(status=status.HTTP_204_NO_CONTENT)
        try:
            RecipeShoppingList.objects.get(
                shopping_list=shopping_list_obj,
                recipe=recipe
            ).delete()
        except ObjectDoesNotExist:  # из-за этого альтернатива
            return Response(
                data={'error': 'Данный рецепт отсутствует в вашем списке'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Будут ли другие статусы отображаться? Нужна и 400 (не был подписан)
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
        ingredients = {}
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


# Ingredient
class IngredientViewSet(viewsets.ModelViewSet):
    '''Представление для эндпоинта ingredients'''
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name', 'name')
    http_method_names = ['get']
