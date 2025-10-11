from django.urls import path
from .views import index

urlpatterns = [
    path('', index),
    path('explore', index),
    path('library', index),
]
