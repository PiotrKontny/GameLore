from operator import index
from django.urls import path
from . import views

urlpatterns = [
    path('', views.main),
    path('gameplots', views.GamePlotsView.as_view()),
    #path("login/", views.LoginOrEmailTokenObtainPairSerializer.as_view(), name="login"),
    path('register/', views.RegisterUser.as_view(), name='register'),
]
