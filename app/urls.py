from operator import index
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter


"""
router = DefaultRouter()
router.register(r'games', views.GamesViewSet)
router.register(r'gameplots', views.GamePlotsViewSet)
"""

urlpatterns = [
    path('', views.main),
    #path("login/", views.LoginOrEmailTokenObtainPairSerializer.as_view(), name="login"),
    path('register/', views.RegisterUser.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    # path('', include(router.urls)),
    path('search/', views.search_view, name='search'),
    path('results/', views.results_view, name='results'),
    path('details/', views.details_view, name='details'),
    path('games/<int:pk>/', views.game_detail_page, name='game_detail_page'),
    path('compilation/', views.compilation_view, name='compilation'),
    path("my_library/", views.my_library_view, name="my_library"),
    path("explore/", views.explore_view, name="explore"),
    path("profile/", views.profile_view, name="profile"),

    # Json Response urls
    path("chatbot/ask/", views.chatbot_ask, name="chatbot_ask"),
    path("chatbot/history/", views.chatbot_history, name="chatbot_history"),
    path("delete_history/", views.delete_history_entry, name="delete_history_entry"),
]
