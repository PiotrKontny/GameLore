from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_view, name='ai_search'),                 # GET form / POST JSON lub form
    path('results/', views.results_view, name='ai_results'),              # HTML lista wyników
    path('details/', views.details_view, name='ai_details'),              # pobranie szczegółów dla wybranego URL
    path('save/', views.save_view, name='ai_save'),                       # zapis do DB
    path('games/<int:pk>/', views.game_detail_page, name='game_detail_page'),

]