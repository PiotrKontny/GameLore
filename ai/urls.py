from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

"""
router = DefaultRouter()
router.register(r'games', views.GamesViewSet)
router.register(r'gameplots', views.GamePlotsViewSet)
"""


urlpatterns = [
    # path('', include(router.urls)),
    path('search/', views.search_view, name='ai_search'),
    path('results/', views.results_view, name='ai_results'),
    path('details/', views.details_view, name='ai_details'),
    path('games/<int:pk>/', views.game_detail_page, name='game_detail_page'),
    path('compilation/', views.compilation_view, name='compilation'),
]

