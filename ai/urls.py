from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# --- Router dla DRF ---
router = DefaultRouter()
router.register(r'games', views.GamesViewSet, basename='api_games')
router.register(r'gameplots', views.GamePlotsViewSet, basename='api_gameplots')

# --- Wszystkie ścieżki (HTML + API) ---
urlpatterns = [
    # --- Widoki HTML ---
    path('search/', views.search_view, name='ai_search'),
    path('results/', views.results_view, name='ai_results'),
    path('details/', views.details_view, name='ai_details'),
    path('games/<int:pk>/', views.game_detail_page, name='game_detail_page'),
    path('scrape_details/', views.scrape_details_view, name='scrape_details'),
    path('compilation/', views.compilation_view, name='compilation'),

    # --- Endpointy API ---
    path('api/', include(router.urls)),
    path('api/games/<int:pk>/', views.game_detail, name='api_game_detail'),
]