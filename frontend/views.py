from django.shortcuts import render
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.shortcuts import render
from app.utils import get_jwt_user, CookieJWTAuthentication

def home(request):
    """
    Główna strona – rozdziela widok na zalogowanego i niezalogowanego użytkownika.
    """
    user = None
    try:
        result = CookieJWTAuthentication().authenticate(request)
        if result:
            user, _ = result
    except Exception:
        pass

    if user and user.is_authenticated:
        # jeśli użytkownik to admin → strona główna admina
        if getattr(user, "is_admin", False):
            return render(request, "frontend/admin_home.html", {"user": user})
        # zwykły użytkownik
        return render(request, "frontend/home_logged_in.html", {"user": user})
    else:
        return render(request, "frontend/home_logged_out.html")




