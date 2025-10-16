from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GamesViewSet, GamePlotsViewSet, game_detail

router = DefaultRouter()
router.register(r'games', GamesViewSet, basename='api_games')
router.register(r'gameplots', GamePlotsViewSet, basename='api_gameplots')

urlpatterns = [
    path('', include(router.urls)),
    path('games/<int:pk>/', game_detail, name='api_game_detail'),
]
