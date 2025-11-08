from django.shortcuts import render
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.shortcuts import render
from app.utils import get_jwt_user  # <--- import nowej funkcji

def home(request):
    """
    Strona główna — pokazuje odpowiedni template w zależności od zalogowania.
    """
    user = get_jwt_user(request)

    if user:
        return render(request, "frontend/home_logged_in.html", {"user": user})
    return render(request, "frontend/home_logged_out.html")



