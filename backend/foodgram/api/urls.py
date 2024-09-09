from django.urls import include, path
from rest_framework import routers

from api.views import (
    IngredientViewSet, login_user, logout_user, RecipeViewSet,
    subscribe, TagViewSet, UserViewSet,
)

app_name = 'api'

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'ingredients', IngredientViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/login/', login_user, name='login'),
    path('auth/token/logout/', logout_user, name='logout'),
    path('users/<int:user_id>/subscribe/', subscribe, name='subscribe'),
]
