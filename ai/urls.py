from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_view, name='ai_search'),                 # GET form / POST JSON lub form
    path('results/', views.results_view, name='ai_results'),              # HTML lista wyników
    path('details/', views.details_view, name='ai_details'),              # pobranie szczegółów dla wybranego URL
    path('games/<int:pk>/', views.game_detail_page, name='game_detail_page'),
    path("scrape_details/", views.scrape_details_view, name="scrape_details"),
    path("compilation/", views.compilation_view, name="compilation"),
]