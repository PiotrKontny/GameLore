from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model, user_logged_in
from django.contrib.auth.hashers import make_password
from django.db.models import Avg, Count
from django.core.cache import cache
from django.http import FileResponse
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework import generics, status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from .serializers import (GamesSerializer, GamePlotsSerializer, UserHistorySerializer, UserSerializer,
                          ChatBotSerializer, UserRatingSerializer)
from .models import Games, GamePlots, UserModel, UserHistory, ChatBot, UserRatings

from .utils import (search_mobygames, scrape_game_info, record_user_history, jwt_required, get_jwt_user,
                    CookieJWTAuthentication)
from decimal import Decimal, InvalidOperation
import asyncio
import json
import re
import markdown
import uuid
import requests, os


def react_index(request):
    """Zwraca Reactowe index.html dla ścieżek /app/..."""

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )
    return FileResponse(open(index_path, "rb"))


@jwt_required
def api_user(request):
    user = request.user

    pfp = user.profile_picture

    # Jeśli to ImageField → wyciągamy .url
    if hasattr(pfp, "url"):
        pfp_url = request.build_absolute_uri(pfp.url)

    # Jeśli to zwykły string (np. "profile_pictures/admin_avatar.png")
    elif isinstance(pfp, str) and pfp:
        # upewniamy się, że zaczyna się od /media/
        if pfp.startswith("/media/"):
            pfp_url = request.build_absolute_uri(pfp)
        else:
            pfp_url = request.build_absolute_uri("/media/" + pfp)

    # Brak zdjęcia → domyślne
    else:
        pfp_url = request.build_absolute_uri("/media/profile_pictures/default_user.png")

    return JsonResponse({
        "username": user.username,
        "profile_picture": pfp_url,
    })



class LoginOrEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Pozwala logować się przez username lub email
        User = get_user_model()
        login_val = (
            self.initial_data.get("login")
            or self.initial_data.get("username")
            or self.initial_data.get("email")
        )

        if login_val:
            # znajdź użytkownika po username lub email
            user = (
                User.objects.filter(username__iexact=login_val).first()
                or User.objects.filter(email__iexact=login_val).first()
            )
            if not user:
                raise serializers.ValidationError("Nie znaleziono użytkownika.")

            if not user.check_password(attrs.get("password")):
                raise serializers.ValidationError("Nieprawidłowe hasło.")

            # ✅ tutaj generujemy parę tokenów ręcznie
            refresh = RefreshToken.for_user(user)
            data = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
            return data

        # fallback
        return super().validate(attrs)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """
        React version — zwraca index.html,
        a frontend sam obsłuży UI logowania.
        """
        from django.http import FileResponse
        import os
        from django.conf import settings

        index_path = os.path.join(
            settings.BASE_DIR,
            "frontend",
            "static",
            "frontend",
            "index.html"
        )

        return FileResponse(open(index_path, "rb"))

    def post(self, request, *args, **kwargs):
        """Obsługuje logowanie użytkownika i zapisuje tokeny w cookies."""
        serializer = LoginOrEmailTokenObtainPairSerializer(data=request.data)

        if not serializer.is_valid():
            print("[Login] Błąd logowania:", serializer.errors)

            # 🔥 React oczekuje JSON, nie HTML!
            return JsonResponse({
                "error": "Invalid username or password."
            }, status=401)

        data = serializer.validated_data
        access_token = data.get("access")
        refresh_token = data.get("refresh")

        print("ACCESS TOKEN:", str(access_token)[:50], "...")
        print("REFRESH TOKEN:", str(refresh_token)[:50], "...")

        response = HttpResponseRedirect("/")

        if access_token:
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                samesite=None,
                secure=False,
                max_age=60 * 60
            )

        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                samesite=None,
                secure=False,
                max_age=7 * 24 * 60 * 60
            )

        return response



class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        React version — zwraca index.html, a frontend zajmuje się UI rejestracji.
        """
        from django.http import FileResponse
        import os
        from django.conf import settings

        index_path = os.path.join(
            settings.BASE_DIR,
            "frontend",
            "static",
            "frontend",
            "index.html"
        )
        return FileResponse(open(index_path, "rb"))

    def post(self, request):
        """Obsługuje rejestrację użytkownika (JSON IN → JSON OUT)."""

        data = request.data

        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        # --- WALIDACJA USERNAME ---
        if len(username) < 4:
            return JsonResponse({
                "error": "Username must be at least 4 characters long."
            }, status=400)

        if not re.match(r"^[A-Za-z0-9]+$", username):
            return JsonResponse({
                "error": "Username can only contain letters and digits (no spaces or special characters)."
            }, status=400)

        # --- WALIDACJA HASŁA ---
        if len(password) < 5:
            return JsonResponse({
                "error": "Password must be at least 5 characters long."
            }, status=400)

        # reszta jak było
        serializer = UserSerializer(data=data)

        if not serializer.is_valid():
            # 🔥 React oczekuje czystego JSON — NIE renderujemy HTML
            return JsonResponse({
                "error": "Please correct the errors below.",
                "details": serializer.errors,
            }, status=400)

        user = serializer.save()

        # upewniamy się, że hasło jest zahashowane
        if not user.password.startswith("pbkdf2_"):
            user.password = make_password(user.password)
            user.save(update_fields=["password"])

        return JsonResponse({
            "message": "Account created successfully."
        }, status=201)



# As the name suggests, it's a class for viewing games (GET operator)
class GamesViewSet(viewsets.ReadOnlyModelViewSet):
    # Allows all the users, even those not logged into the app, to view them
    permission_classes = [AllowAny]
    queryset = Games.objects.order_by('-id')
    serializer_class = GamesSerializer



# Same as GamesViewSet but with gameplots instead
class GamePlotsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GamePlots.objects.select_related('game').order_by('-id')
    serializer_class = GamePlotsSerializer


# The @api_view decorator turns this regular Django view into a Django REST Framework API endpoint. It ensures that the
# view only accepts GET requests and returns JSON responses instead of HTML.
def game_detail(request, pk: int):
    # Tries to retrieve game object using the primary key (pk), in this case being game_id. On the website, when opening
    # the game details the page url has the same pk number as the game_id it's based on
    game = get_object_or_404(Games, pk=pk)
    return Response(GamesSerializer(game).data)



# The usage of csrf decorator is so that the API endpoints can retrieve requests from external clients such as
# JavaScript that don’t include CSRF tokens. In the code below it's used to access MobyGames website for scraping
@jwt_required
@csrf_exempt
def search_view(request):
    # ============================
    # 1) GET → Zwracamy React index.html
    # ============================
    if request.method == "GET":
        from django.http import FileResponse
        import os
        from django.conf import settings

        index_path = os.path.join(
            settings.BASE_DIR,
            "frontend",
            "static",
            "frontend",
            "index.html"
        )
        return FileResponse(open(index_path, "rb"))

    # ============================
    # 2) POST → logika wyszukiwania
    # ============================
    game = None

    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8"))
            game = (payload.get("game") or "").strip()
        except:
            return HttpResponseBadRequest("Invalid JSON")
    else:
        game = (request.POST.get("game") or "").strip()

    if not game:
        return HttpResponseBadRequest('Missing "game"')

    # wykonaj scraping
    results = asyncio.run(search_mobygames(game))

    # jeśli API → zwróć JSON
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"query": game, "results": results})

    # zapis do sesji (dla /app/results/)
    request.session["ai_last_results"] = results
    request.session["ai_last_query"] = game

    return JsonResponse({"redirect": "/app/results/"})


# Displays the results of searching the game
@jwt_required
def results_view(request):
    results = request.session.get('ai_last_results') or []
    query = request.session.get('ai_last_query') or ''

    # Jeśli to React fetch – zwróć JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({
            "results": results,
            "query": query
        })

    # W przeciwnym wypadku – Reactowy index.html
    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )
    return FileResponse(open(index_path, "rb"))



# When the json is being passed to the database, the database cannot accept the results in decimal, dictionary or a list
# format and therefore must be changed into a format the database can read. This function is not that often used as it
# may seem, however it was in the original version of the ai implementation and I don't remember exactly how useful it
# is for the current needs of the code so it's been decided to let it stay just in case
def safe_json(obj):
    # When the result is in decimal format then return it as a float
    if isinstance(obj, Decimal):
        return float(obj)
    # When the result is in dictionary format it passes as for example k="title", v="Elden Ring", so the safe_json
    # is passed again so that the value returned could be just "Elden Ring"
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    # More or less the same happens in the case where the list is being passed through this function
    if isinstance(obj, list):
        return [safe_json(v) for v in obj]
    # And if the object isn't one of those cases, or it was already passed as one of those cases and is in a database
    # readable format, only then can it be returned to the database
    return obj



# This function is used for scraping the game plots and everything about the game from Mobygames
@jwt_required
def details_view(request):
    url = request.GET.get('url')
    if not url:
        return HttpResponseBadRequest('Missing url')

    title_guess = None
    for r in request.session.get('ai_last_results', []):
        if r.get('url') == url:
            first_line = (r.get('description') or '').splitlines()[0].strip()
            m = re.match(r'(.+?)\s*\((?:[^)]*)\)\s*', first_line)
            title_guess = (m.group(1) if m else first_line).strip()
            break

    if title_guess:
        existing = Games.objects.filter(title__iexact=title_guess).first()
        if existing:
            record_user_history(request.user, existing)
            return redirect('game_detail_page', pk=existing.id)

    # --- Tu nie zmieniamy scrapowania fabuły, ale usuwamy generowanie streszczenia ---
    data = asyncio.run(scrape_game_info(url, media_root=settings.MEDIA_ROOT, save_image=True))

    if not data:
        print(f"[ERROR] Scraper returned None for URL: {url}")
        return render(request, "frontend/error.html", {
            "message": "Nie udało się pobrać danych o grze. Spróbuj ponownie."
        })

    if data.get("is_compilation"):
        return redirect(f"/app/compilation/?url={url}")

    for key, val in list(data.items()):
        if isinstance(val, Decimal):
            data[key] = float(val)

    try:
        if data.get('score'):
            data['score'] = Decimal(str(data['score']))
        else:
            data['score'] = None
    except (InvalidOperation, TypeError, ValueError):
        data['score'] = None

    games = Games.objects.create(
        title=data.get('title') or 'Unknown',
        release_date=data.get('release_date'),
        genre=data.get('genre'),
        studio=data.get('studio'),
        score=data.get('score'),
        cover_image=data.get('cover_image'),
        mobygames_url=data.get('mobygames_url'),
        wikipedia_url=data.get('wikipedia_url'),
    )

    # --- tutaj zapisujemy zawsze tylko pełny plot, bez summary ---
    GamePlots.objects.create(
        game_id=games,
        full_plot=data.get('full_plot') or '',
        summary=data.get('summary') if "No Summary Available" in (data.get('summary') or "") else ''
    )

    record_user_history(request.user, games)
    return redirect('game_detail_page', pk=games.id)




# As explained couple lines before, this part of code handles displaying the scraped results for each game
@jwt_required
def game_detail_page(request, pk):
    """
    API + frontend dla Reacta.
    Jeśli request jest fetch → JSON
    Jeśli normalne wejście → index.html (React przejmie routing)
    """

    # 🔥 Jeśli fetch / React request – zwróć JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        game = get_object_or_404(Games, pk=pk)
        record_user_history(request.user, game)

        plot = GamePlots.objects.filter(game_id=game).first()
        full_plot_md = plot.full_plot if plot else ""
        summary_md = plot.summary if plot else ""

        import markdown
        full_plot_html = markdown.markdown(full_plot_md or "")
        summary_html = markdown.markdown(summary_md or "")

        # poprawne pobranie URL okładki
        cover_value = game.cover_image
        if not cover_value:
            cover_url = None
        else:
            if hasattr(cover_value, "url"):
                cover_url = cover_value.url
            else:
                cover_url = f"/media/{cover_value}"

        return JsonResponse({
            "id": game.id,
            "title": game.title,
            "release_date": str(game.release_date) if game.release_date else None,
            "genre": game.genre,
            "studio": game.studio,
            "score": float(game.score) if game.score is not None else None,

            "mobygames_url": game.mobygames_url,
            "wikipedia_url": game.wikipedia_url,
            "cover_image": cover_url,

            # to czego React wymaga
            "full_plot_html": full_plot_html,
            "summary_html": summary_html,
        })

    # 🔥 W innym przypadku → zwróć Reacta
    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )
    return FileResponse(open(index_path, "rb"))

@jwt_required
def api_game_detail(request, pk):
    game = get_object_or_404(Games, pk=pk)
    plot = GamePlots.objects.filter(game_id=game).first()

    import markdown
    full_plot_html = markdown.markdown(plot.full_plot if plot else "")
    summary_html = markdown.markdown(plot.summary if plot else "")

    cover = None
    if game.cover_image:
        if hasattr(game.cover_image, "url"):
            cover = game.cover_image.url
        else:
            cover = "/media/" + str(game.cover_image)

    try:
        score_value = float(game.score) if game.score is not None else None
    except:
        score_value = None

    return JsonResponse({
        "id": game.id,
        "title": game.title,
        "release_date": str(game.release_date) if game.release_date else None,
        "genre": game.genre,
        "studio": game.studio,
        "score": score_value,
        "cover_image": cover,
        "mobygames_url": game.mobygames_url,
        "wikipedia_url": game.wikipedia_url,
        "full_plot_html": full_plot_html,
        "summary_html": summary_html,
    })



# This function deals with that cursed game compilation situation I described multiple times in this project. But
# essentially the only thing it does is redirecting the user to the corresponding urls
@jwt_required
def compilation_view(request):
    url = request.GET.get("url")
    if not url:
        return JsonResponse({"error": "Missing URL"}, status=400)

    result = asyncio.run(scrape_game_info(url, settings.MEDIA_ROOT))

    if not result.get("is_compilation"):
        return JsonResponse({"error": "Not a compilation"}, status=400)

    # JSON dla React
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({
            "title": result.get("title"),
            "included_games": result.get("included_games", [])
        })

    # fallback do React index.html
    from django.http import FileResponse
    import os

    index_path = os.path.join(settings.BASE_DIR, "frontend", "static", "frontend", "index.html")
    return FileResponse(open(index_path, "rb"))


@jwt_required
def details_view(request):
    url = request.GET.get('url')
    if not url:
        return JsonResponse({"error": "Missing url"}, status=400)

    # jeśli to fetch → React oczekuje JSON
    is_json = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json"

    # próbujemy znaleźć tytuł gry w session
    title_guess = None
    for r in request.session.get('ai_last_results', []):
        if r.get('url') == url:
            first_line = (r.get('description') or '').splitlines()[0].strip()
            m = re.match(r'(.+?)\s*\((?:[^)]*)\)\s*', first_line)
            title_guess = (m.group(1) if m else first_line).strip()
            break

    # jeśli gra istnieje w bazie → zwróć JSON redirect target
    if title_guess:
        existing = Games.objects.filter(title__iexact=title_guess).first()
        if existing:
            record_user_history(request.user, existing)
            if is_json:
                return JsonResponse({"redirect_game_id": existing.id})
            return redirect('game_detail_page', pk=existing.id)

    # scrapowanie
    data = asyncio.run(scrape_game_info(url, media_root=settings.MEDIA_ROOT, save_image=True))

    if not data:
        return JsonResponse({"error": "Scraper failed"}, status=500) if is_json else render(...)

    # kompilacja
    if data.get("is_compilation"):
        if is_json:
            return JsonResponse({"redirect_compilation": True})
        return redirect(f"/app/compilation/?url={url}")

    # zapis gry
    for key, val in list(data.items()):
        if isinstance(val, Decimal):
            data[key] = float(val)

    game = Games.objects.create(
        title=data.get('title') or 'Unknown',
        release_date=data.get('release_date'),
        genre=data.get('genre'),
        studio=data.get('studio'),
        score=data.get('score'),
        cover_image=data.get('cover_image'),
        mobygames_url=data.get('mobygames_url'),
        wikipedia_url=data.get('wikipedia_url'),
    )

    GamePlots.objects.create(
        game_id=game,
        full_plot=data.get('full_plot') or '',
        summary=data.get('summary') or ''
    )

    record_user_history(request.user, game)

    if is_json:
        return JsonResponse({"new_game_id": game.id})

    return redirect('game_detail_page', pk=game.id)



@jwt_required
def my_library_view(request):
    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )
    return FileResponse(open(index_path, "rb"))


@jwt_required
def my_library_api(request):
    user = request.user

    query = (request.GET.get("q") or "").strip()
    sort_option = request.GET.get("sort", "newest")

    history = UserHistory.objects.filter(user_id=user)

    if query:
        history = history.filter(game_id__title__icontains=query)

    # sort
    if sort_option == "oldest":
        history = history.order_by("viewed_at")
    elif sort_option == "rating":
        rated = (
            UserRatings.objects.filter(user_id=user)
            .values("game_id")
            .annotate(r=Avg("rating"))
        )
        rmap = {r["game_id"]: r["r"] for r in rated}
        history = sorted(history, key=lambda h: rmap.get(h.game_id_id, 0), reverse=True)
    else:
        history = history.order_by("-viewed_at")

    output = []
    for h in history:
        game = h.game_id
        avg_rating = UserRatings.objects.filter(game_id=game).aggregate(
            Avg("rating")
        )["rating__avg"]

        user_rating = UserRatings.objects.filter(user_id=user, game_id=game).first()

        # cover URL
        cover = None
        if game.cover_image:
            if hasattr(game.cover_image, "url"):
                cover = game.cover_image.url
            else:
                cover = "/media/" + str(game.cover_image)

        output.append({
            "id": game.id,
            "title": game.title,
            "cover_image": cover,
            "user_rating": user_rating.rating if user_rating else None,
        })

    return JsonResponse({
        "games": output,
    })


@jwt_required
@csrf_exempt
def delete_history_entry(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        game_id = data.get("game_id")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not game_id:
        return JsonResponse({"error": "Missing game_id"}, status=400)

    user = None
    if isinstance(request.user, UserModel):
        user = request.user
    else:
        user = UserModel.objects.filter(username=request.user.username).first()

    if not user:
        return JsonResponse({"error": "User not found"}, status=403)

    game = Games.objects.filter(id=game_id).first()
    if not game:
        return JsonResponse({"error": "Game not found"}, status=404)

    deleted_history = UserHistory.objects.filter(user_id=user, game_id=game).delete()
    deleted_chat = ChatBot.objects.filter(user_id=user, game_id=game).delete()

    print(f"[delete_history_entry] Removed: {deleted_history[0]} from UserHistory, {deleted_chat[0]} from ChatBot.")

    return JsonResponse({"message": "Record deleted successfully."})


# View for the game explore page where the user can choose from any of the games already in the database. Of course once
# they click one of the links to the game detail page, that game is then saved into their library. This view is not
# require the user to log in, however when they want to view one of the games in detail, then they must log in
def explore_view(request):
    """
    React version of explore page:
    - If fetch/XHR → return JSON
    - Otherwise → return index.html (React handles UI)
    """
    from django.db.models import Avg
    from django.db.models.functions import Trim
    from django.http import FileResponse
    import os
    from django.conf import settings

    # Params
    sort_option = request.GET.get('sort', 'oldest')
    query = (request.GET.get('q') or '').strip()
    selected_genre = (request.GET.get('genre') or '').strip()

    # If React fetch → return JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":

        base_qs = Games.objects.all()

        if query:
            base_qs = base_qs.filter(title__icontains=query)
        if selected_genre:
            base_qs = base_qs.filter(genre__iexact=selected_genre)

        qs = base_qs
        if sort_option == 'newest':
            qs = qs.order_by('-id')
        elif sort_option == 'score':
            qs = qs.order_by('-score')
        elif sort_option == 'rating':
            qs = qs.annotate(avg_rating=Avg('game_ratings__rating')).order_by('-avg_rating')
        else:
            qs = qs.order_by('id')  # oldest

        genres = (
            Games.objects.exclude(genre__isnull=True).exclude(genre='')
            .annotate(genre_clean=Trim('genre'))
            .values_list('genre_clean', flat=True).distinct().order_by('genre_clean')
        )

        games_out = []
        for game in qs:
            avg_rating = UserRatings.objects.filter(game_id=game).aggregate(
                Avg("rating")
            )["rating__avg"]

            games_out.append({
                "id": game.id,
                "title": game.title,
                "cover_image": game.cover_image,
                "score": float(game.score) if game.score is not None else None,
                "rating": round(avg_rating, 2) if avg_rating else None,
            })

        return JsonResponse({
            "games": games_out,
            "genres": list(genres),
            "sort_option": sort_option,
            "query": query,
            "selected_genre": selected_genre,
        })

    # Otherwise → send React index.html
    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )

    return FileResponse(open(index_path, "rb"))


@csrf_exempt
@jwt_required
def profile_view(request):
    """
    React version:
    - GET → zwraca JSON z danymi użytkownika
    - POST → obsługuje akcje update (username, password, pfp, logout)
    """

    user = None
    if isinstance(request.user, UserModel):
        user = request.user
    else:
        user = UserModel.objects.filter(username=request.user.username).first()

    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    # ========== GET: zwróć dane użytkownika ==========
    if request.method == "GET":
        # zdjęcie profilowe — URL
        pfp = user.profile_picture
        if hasattr(pfp, "url"):
            pfp_url = request.build_absolute_uri(pfp.url)
        elif isinstance(pfp, str) and pfp:
            if pfp.startswith("/media/"):
                pfp_url = request.build_absolute_uri(pfp)
            else:
                pfp_url = request.build_absolute_uri("/media/" + pfp)
        else:
            pfp_url = request.build_absolute_uri("/media/profile_pictures/default_user.png")

        return JsonResponse({
            "username": user.username,
            "email": user.email,
            "profile_picture": pfp_url
        })

    # ========== POST: akcje profilu ==========
    action = request.POST.get("action")

    # ---- ZMIANA USERNAME ----
    if action == "change_username":
        new_username = request.POST.get("new_username", "").strip()

        if not new_username:
            return JsonResponse({"error": "Username cannot be empty."}, status=400)

        if new_username == user.username:
            return JsonResponse({"message": "Nothing changed."})

        if len(new_username) < 4:
            return JsonResponse({
                "error": "Username must be at least 4 characters long."
            }, status=400)

        if not re.match(r"^[A-Za-z0-9]+$", new_username):
            return JsonResponse({
                "error": "Username can only contain letters and digits (no spaces or special characters)."
            }, status=400)

        if UserModel.objects.filter(username=new_username).exists():
            return JsonResponse({"error": "This username already exists."}, status=400)

        user.username = new_username
        user.save()
        return JsonResponse({"message": "Username has been changed!"})

    # ---- ZMIANA HASŁA ----
    if action == "change_password":
        old_password = request.POST.get("old_password", "")
        new_password = request.POST.get("new_password", "")

        if not user.check_password(old_password):
            return JsonResponse({"error": "Incorrect old password."}, status=400)

        if not new_password:
            return JsonResponse({"error": "New password cannot be empty."}, status=400)

        if len(new_password) < 5:
            return JsonResponse({
                "error": "New password must be at least 5 characters long."
            }, status=400)

        user.set_password(new_password)
        user.save()
        return JsonResponse({"message": "Password has been changed!"})

    # ---- ZMIANA ZDJĘCIA PROFILOWEGO ----
    if action == "change_profile_picture":
        file = request.FILES.get("profile_picture")
        if not file:
            return JsonResponse({"error": "No file uploaded."}, status=400)

        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile

        filename = f"profile_pictures/{user.username}_{file.name}"
        file_path = default_storage.save(filename, ContentFile(file.read()))
        user.profile_picture = file_path
        user.save()

        return JsonResponse({"message": "Profile picture updated successfully!"})

    # ---- LOGOUT ----
    if action == "logout":
        response = JsonResponse({"message": "Logged out"})
        response.delete_cookie("access_token")
        return response

    return JsonResponse({"error": "Invalid action."}, status=400)






# The function for returning user's chatbot history for the corresponding game
@jwt_required
def chatbot_history(request):
    game_id = request.GET.get("game_id")
    if not game_id:
        return JsonResponse({"error": "Missing game_id"}, status=400)

    history = ChatBot.objects.filter(user_id=request.user, game_id=game_id).order_by("created_at")
    # The history returned is in the format of question and answer so that it can be easily displayed for the user
    data = [
        {"question": h.question, "answer": h.answer, "created_at": h.created_at.isoformat()}
        for h in history
    ]
    return JsonResponse(data, safe=False)


# This function handles the user's questions to the chatbot, which is then being sent to OpenRouter, a website which
# handles chatbot requests to an extensive library of different LLM models
@csrf_exempt
@jwt_required
def chatbot_ask(request):
    # Standard handling of such function - making sure the method is POST
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    # Making sure that the data is in the correct json format
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    question = data.get("question")
    game_id = data.get("game_id")

    # Making sure that the question and game_id exist
    if not question or not game_id:
        return JsonResponse({"error": "Missing question or game_id"}, status=400)

    # Making sure the game itself exists
    try:
        game = Games.objects.get(id=game_id)
    except Games.DoesNotExist:
        return JsonResponse({"error": "Game not found"}, status=404)

    # Standard request to OpenRouter
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            # The authorization of the request is passed through my own api key the website gave me
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            # The model used is Mistral 7B Instruct and as it's first command, it's supposed to answer only the
            # questions related to the game this chatbot belongs to
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"You are a helpful assistant that only talks about the video game '{game.title}'. "
                            "Always stay on-topic and answer concisely."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
            },
            timeout=30
        )
        # Handling the errors from OpenRouter
        response.raise_for_status()

        answer = response.json()["choices"][0]["message"]["content"]

        # The chatbot's answers often came with things like "[\s\]" or something at the beginning of the answer. All
        # those below are here to make sure it doesn't happen
        answer = re.sub(r'<\/?s>', '', answer)
        answer = re.sub(r'\[\/?s\]', '', answer)
        answer = re.sub(r'\[OUT\]|\[INST\]|\[\/?INSTR?\]', '', answer, flags=re.IGNORECASE)
        answer = answer.strip()

        # Sometimes the model returns a blank answer and therefore, to make sure the user doesn't get confused, the
        # following message is displayed so that he can ask again
        if not answer or len(answer.strip()) == 0:
            answer = ("I'm sorry, I couldn't generate an answer this time. Please try asking again. "
                      "(Sometimes it might take a couple of tries)")
    except Exception as e:
        return JsonResponse({"error": f"OpenRouter API error: {e}"}, status=500)

    # The questions and answers are then passed to the database
    ChatBot.objects.create(
        user_id=request.user,
        game_id=game,
        question=question,
        answer=answer,
    )

    return JsonResponse({"answer": answer})


@jwt_required
def chatbot_page(request):
    """
    React version:
    - jeśli fetch/XHR lub ?format=json → zwraca JSON (lista gier + domyślna gra)
    - inaczej → index.html (React przejmuje routing)
    """
    user = request.user

    # Jeśli to fetch / React → zwróć JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        # Wszystkie gry z historii użytkownika
        history = (
            UserHistory.objects.filter(user_id=user)
            .select_related("game_id")
            .order_by("-viewed_at")
        )

        games = []
        for h in history:
            g = h.game_id
            cover = None
            if g.cover_image:
                if hasattr(g.cover_image, "url"):
                    cover = g.cover_image.url
                else:
                    cover = "/media/" + str(g.cover_image)

            games.append({
                "id": g.id,
                "title": g.title,
                "cover_image": cover,
            })

        # Ostatnia gra z chatu
        last_chat = ChatBot.objects.filter(user_id=user).order_by("-created_at").first()
        default_game_id = last_chat.game_id.id if last_chat else None

        # Jeśli brak czatu, domyślnie ostatnio oglądana gra
        if not default_game_id and games:
            default_game_id = games[0]["id"]

        return JsonResponse({
            "games": games,
            "default_game_id": default_game_id,
        })

    # W innym przypadku → zwróć Reacta (index.html)
    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )
    return FileResponse(open(index_path, "rb"))


@jwt_required
@csrf_exempt
def delete_chat_history(request):
    """
    Usuwa całą historię chatu użytkownika dla konkretnej gry.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        game_id = data.get("game_id")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not game_id:
        return JsonResponse({"error": "Missing game_id"}, status=400)

    user = request.user

    deleted_count, _ = ChatBot.objects.filter(user_id=user, game_id=game_id).delete()
    print(f"[delete_chat_history] User {user.username} deleted {deleted_count} chat messages for game_id={game_id}")

    return JsonResponse({"message": "Chat history deleted successfully.", "deleted": deleted_count})



@csrf_exempt
@jwt_required
def generate_summary_view(request, pk):
    """
    Generuje streszczenie fabuły gry po kliknięciu przycisku "Generate Summary".
    Działa na podstawie istniejącego full_plot z bazy (markdown).
    Nie scrapuje Wikipedii — działa lokalnie.
    """
    import markdown
    from .utils import summarize_plot_from_markdown

    game = get_object_or_404(Games, pk=pk)
    plot = GamePlots.objects.filter(game_id=game).first()

    if not plot:
        return JsonResponse({"error": "No plot to summarize."}, status=400)

    # ✅ Jeśli streszczenie już istnieje — zwróć je bez generowania
    if plot.summary and "No Summary Available" not in plot.summary:
        return JsonResponse({"summary": markdown.markdown(plot.summary)})

    # ❌ Brak fabuły lub placeholder
    if not plot.full_plot or "No Plot Found" in plot.full_plot:
        return JsonResponse({"error": "No plot to summarize."}, status=400)

    try:
        print(f"[SUMMARY] Uruchamiam streszczenie z markdownu dla gry '{game.title}'")
        summary_md = summarize_plot_from_markdown(plot.full_plot)

        if not summary_md:
            return JsonResponse({
                "summary": "<p>The plot is too short to require a summary.</p>"
            })

        # 📝 Zapis do bazy
        plot.summary = summary_md
        plot.save(update_fields=["summary"])

        summary_html = markdown.markdown(summary_md)
        print(f"[SUMMARY] Zakończono streszczenie gry '{game.title}'")
        return JsonResponse({"summary": summary_html})

    except Exception as e:
        print(f"[SUMMARY ERROR] {e}")
        return JsonResponse({"error": f"Błąd podczas generowania streszczenia: {e}"}, status=500)



@csrf_exempt
@jwt_required
def game_rating_view(request, pk):
    """
    GET – pobiera średnią ocenę, liczbę głosów i ocenę użytkownika
    POST/PUT – zapisuje lub aktualizuje ocenę użytkownika
    """
    user = request.user
    game = get_object_or_404(Games, pk=pk)

    if request.method == "GET":
        avg_votes = UserRatings.objects.filter(game_id=game).aggregate(
            avg=Avg('rating'), votes=Count('id')
        )
        user_rating = UserRatings.objects.filter(user_id=user, game_id=game).first()
        return JsonResponse({
            "avg": round(avg_votes['avg'] or 0, 2),
            "votes": avg_votes['votes'] or 0,
            "user_rating": user_rating.rating if user_rating else None
        })

    elif request.method in ["POST", "PUT"]:
        try:
            data = json.loads(request.body)
            rating_value = int(data.get("rating"))
            if rating_value < 1 or rating_value > 10:
                return JsonResponse({"error": "Rating must be between 1 and 10."}, status=400)
        except Exception:
            return JsonResponse({"error": "Invalid JSON or rating."}, status=400)

        obj, created = UserRatings.objects.update_or_create(
            user_id=user, game_id=game, defaults={"rating": rating_value}
        )

        avg_votes = UserRatings.objects.filter(game_id=game).aggregate(
            avg=Avg('rating'), votes=Count('id')
        )
        return JsonResponse({
            "avg": round(avg_votes['avg'] or 0, 2),
            "votes": avg_votes['votes'] or 0,
            "user_rating": rating_value
        })

    return JsonResponse({"error": "Method not allowed"}, status=405)


@jwt_required
def admin_panel(request):
    """
    Główny panel administratora – wersja React.
    Zwraca index.html, a React zajmuje się resztą.
    """
    # tylko admin
    if not getattr(request.user, "is_admin", False):
        return HttpResponseForbidden("Brak uprawnień do panelu administratora")

    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )

    return FileResponse(open(index_path, "rb"))



@csrf_exempt
@jwt_required
@require_http_methods(["POST"])
def admin_delete_user(request, user_id):
    print("[ADMIN] admin_delete_user wywołany")
    if not getattr(request.user, "is_admin", False):
        return JsonResponse({"error": "Brak uprawnień"}, status=403)
    user = UserModel.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "Użytkownik nie istnieje"}, status=404)
    user.delete()
    return JsonResponse({"message": "Użytkownik został usunięty"})


@csrf_exempt
@jwt_required
@require_http_methods(["POST"])
def admin_delete_game(request, game_id):
    print("[ADMIN] admin_delete_game wywołany")
    if not getattr(request.user, "is_admin", False):
        return JsonResponse({"error": "Brak uprawnień"}, status=403)
    game = Games.objects.filter(id=game_id).first()
    if not game:
        return JsonResponse({"error": "Gra nie istnieje"}, status=404)
    game.delete()
    return JsonResponse({"message": "Gra została usunięta"})


@csrf_exempt
@jwt_required
@require_http_methods(["POST"])
def admin_edit_game_score(request, game_id):
    print("[ADMIN] admin_edit_game_score wywołany")
    if not getattr(request.user, "is_admin", False):
        return JsonResponse({"error": "Brak uprawnień"}, status=403)

    try:
        data = json.loads(request.body)
        new_score = Decimal(str(data.get("score")))
    except Exception as e:
        return JsonResponse({"error": f"Błąd danych: {e}"}, status=400)

    game = Games.objects.filter(id=game_id).first()
    if not game:
        return JsonResponse({"error": "Gra nie istnieje"}, status=404)

    game.score = new_score
    game.save(update_fields=["score"])
    return JsonResponse({"message": f"Score gry '{game.title}' zmieniono na {new_score}"})


@jwt_required
def admin_users_view(request):

    # ❗ 1. Uprawnienia
    if not request.user.is_admin:
        return JsonResponse({"error": "Access denied"}, status=403)

    # ❗ 2. Parametry z URL
    sort_option = request.GET.get("sort", "oldest")
    query = (request.GET.get("q") or "").strip()

    # ❗ 3. Jeśli React fetch → zwróć JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":

        users = UserModel.objects.all()

        # 🔍 Filtrowanie
        if query:
            users = users.filter(username__icontains=query)

        # 🔽 Sortowanie
        if sort_option == "newest":
            users = users.order_by("-date_joined")
        else:
            users = users.order_by("date_joined")

        data = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "date_joined": u.date_joined.strftime("%Y-%m-%d %H:%M"),
            }
            for u in users
        ]

        return JsonResponse({"users": data})

    # ❗ 4. Jeśli to nie JSON → zwróć index.html Reacta
    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )

    return FileResponse(open(index_path, "rb"))




@jwt_required
def admin_games_view(request):

    # ⛔ 1. Sprawdzenie czy user to admin
    if not request.user.is_admin:
        return JsonResponse({"error": "Access denied"}, status=403)

    # ⛔ 2. Jeśli to request AJAX → zwróć JSON (dla React fetch)
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":

        sort_option = request.GET.get("sort", "oldest")
        query = (request.GET.get("q") or "").strip()

        games = Games.objects.all()

        if query:
            games = games.filter(title__icontains=query)

        if sort_option == "newest":
            games = games.order_by("-id")
        elif sort_option == "score":
            games = games.order_by("-score")
        else:
            games = games.order_by("id")

        data = [
            {
                "id": g.id,
                "title": g.title,
                "score": g.score,
            }
            for g in games
        ]
        return JsonResponse({"games": data})

    # ⛔ 3. Jeśli nie jest to fetch → zwróć index.html Reacta
    from django.http import FileResponse
    import os
    from django.conf import settings

    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )

    return FileResponse(open(index_path, "rb"))






@csrf_exempt
@jwt_required
@require_http_methods(["POST"])
def admin_reload_game(request, game_id):
    """
    Przeładowuje (scrapuje ponownie) wybraną grę i aktualizuje jej fabułę + streszczenie.
    """
    if not getattr(request.user, "is_admin", False):
        return JsonResponse({"error": "Brak uprawnień"}, status=403)

    from .models import Games, GamePlots
    from .utils import scrape_game_info_admin

    game = Games.objects.filter(id=game_id).first()
    if not game:
        return JsonResponse({"error": "Gra nie istnieje"}, status=404)

    if not game.mobygames_url:
        return JsonResponse({"error": "Brak adresu URL MobyGames dla tej gry."}, status=400)

    try:
        print(f"[ADMIN RELOAD] Uruchamiam ponowne scrapowanie dla gry: {game.title}")
        data = asyncio.run(scrape_game_info_admin(game.mobygames_url, settings.MEDIA_ROOT))

        plot = GamePlots.objects.filter(game_id=game).first()
        if not plot:
            plot = GamePlots.objects.create(game_id=game)

        plot.full_plot = data.get("full_plot") or "## No Plot Found"
        plot.summary = data.get("summary") or "## No Summary Available"
        plot.save(update_fields=["full_plot", "summary"])

        game.wikipedia_url = data.get("wikipedia_url")
        game.save(update_fields=["wikipedia_url"])

        print(f"[ADMIN RELOAD] Gra '{game.title}' została przeładowana.")
        return JsonResponse({"message": f"Gra '{game.title}' została ponownie załadowana i zaktualizowana."})
    except Exception as e:
        print(f"[ADMIN RELOAD ERROR] {e}")
        return JsonResponse({"error": f"Błąd podczas ponownego ładowania gry: {e}"}, status=500)


def information_view(request):
    """
    Serves the React InformationPage.
    """
    index_path = os.path.join(
        settings.BASE_DIR,
        "frontend",
        "static",
        "frontend",
        "index.html"
    )
    return FileResponse(open(index_path, "rb"))


#def home(request):
#    return react_index(request)

