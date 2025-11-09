from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model, user_logged_in
from django.contrib.auth.hashers import make_password
from django.db.models import Avg, Count
from django.core.cache import cache
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
        """Renderuje stronę logowania HTML."""
        return render(request, "frontend/login.html")

    def post(self, request, *args, **kwargs):
        """Obsługuje logowanie użytkownika i zapisuje tokeny w cookies."""
        serializer = LoginOrEmailTokenObtainPairSerializer(data=request.data)

        if not serializer.is_valid():
            print("[Login] Błąd logowania:", serializer.errors)
            return render(request, "frontend/login.html", {"error": "Invalid username or password."}, status=401)

        data = serializer.validated_data
        access_token = data.get("access")
        refresh_token = data.get("refresh")

        print("ACCESS TOKEN:", str(access_token)[:50], "...")
        print("REFRESH TOKEN:", str(refresh_token)[:50], "...")

        # Utwórz nową odpowiedź Django
        response = HttpResponseRedirect("/")

        # Zapisz tokeny jako cookies
        if access_token:
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                samesite=None,  # ważne dla Chrome
                secure=False,
                max_age=60 * 60,  # 1 godzina
            )

        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                samesite=None,
                secure=False,
                max_age=7 * 24 * 60 * 60,  # 7 dni
            )

        return response


class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """Renderuje stronę rejestracji HTML."""
        return render(request, "frontend/register.html")

    def post(self, request):
        """Obsługuje rejestrację użytkownika."""
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # szyfrowanie hasła (na wszelki wypadek)
            if not user.password.startswith("pbkdf2_"):
                user.password = make_password(user.password)
                user.save(update_fields=["password"])

            # po poprawnej rejestracji przekierowanie na stronę logowania
            return HttpResponseRedirect("/app/login/")

        # w przypadku błędów renderuj formularz ponownie z komunikatem
        errors = serializer.errors
        error_message = "Please correct the errors below."
        return render(request, "frontend/register.html", {"errors": errors, "error_message": error_message})


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
    if request.method == 'GET':
        # Dodano: renderowanie estetycznej strony wyszukiwania
        # (korzysta z pliku templates/frontend/search_form.html)
        return render(request, 'frontend/search_form.html')

    game = None

    # Checks if the request content type is json
    if request.content_type and 'application/json' in request.content_type:
        try:
            # Decodes the json body in order to extract the game field
            payload = json.loads(request.body.decode('utf-8'))
            game = (payload.get('game') or '').strip()
        except:
            return HttpResponseBadRequest('Invalid JSON')
    else:
        # If it's not JSON, then it tries to get 'game' from standard POST form data
        game = (request.POST.get('game') or '').strip()

    # No game provided results in return HTTP 400 (Bad Request)
    if not game:
        return HttpResponseBadRequest('Missing "game"')

    # Use search_mobygames function from the utils.py file to scrape the first 10 results displayed when the game is
    # searched using MobyGames search engine
    results = asyncio.run(search_mobygames(game))

    # If the user requests json format it returns the search results in the json format (for example when using frontend
    # via Django REST framework to test out backend)
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'query': game, 'results': results})

    # Both of those requests below serve to temporarily remember the search results so that they can be displayed on the
    # results page
    request.session['ai_last_results'] = results
    request.session['ai_last_query'] = game

    # Redirects the user to the results page where the results will be displayed.
    return redirect(reverse('results'))


# Displays the results of searching the game
def results_view(request):
    # Returns the last results saved in the session from the previous function. It also returns an empty list to not
    # cause any errors. Pretty much same happens with query variable
    results = request.session.get('ai_last_results') or []
    query = request.session.get('ai_last_query') or ''

    # 🔑 Spróbuj odczytać użytkownika z JWT (ciasteczko access_token)
    jwt_user = get_jwt_user(request)

    # Dodane: przekazanie obiektu użytkownika do szablonu
    context = {
        'results': results,
        'query': query,
        'user': jwt_user if jwt_user else (request.user if request.user.is_authenticated else None),
    }

    # Self-explanatory but it renders the site using the correct html file and uses results and query variables as the
    # needed results of the query (pleonasm or "masło maślane", as one would call it but that's just how it works)
    return render(request, 'frontend/search_results.html', context)


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
    game = get_object_or_404(Games, pk=pk)

    # The game is recorded into the user history, so that the user can later view it from his library instead of
    # searching fot it again in the search function of the app
    record_user_history(request.user, game)

    plot = GamePlots.objects.filter(game_id=game).first()

    full_plot_html = ""
    summary_html = ""

    # Due to the unique nature of the saved plots being in markdown format, the following if statements deals with it
    # appropriately
    if plot:
        full_plot_html = markdown.markdown(plot.full_plot or "")
        summary_html = markdown.markdown(plot.summary or "")

    # The data is passed to game_detail.html file which takes the necessary arguments to build a unique page for each
    # game
    return render(request, 'frontend/game_detail.html', {
        'game': game,
        'plot': plot,
        'full_plot_html': full_plot_html,
        'summary_html': summary_html,
    })




# This function deals with that cursed game compilation situation I described multiple times in this project. But
# essentially the only thing it does is redirecting the user to the corresponding urls
def compilation_view(request):
    url = request.GET.get("url")
    if not url:
        return render(request, "frontend/error.html", {"message": "Brak adresu URL"})

    result = asyncio.run(scrape_game_info(url, settings.MEDIA_ROOT))

    if not result.get("is_compilation"):
        return render(request, "frontend/error.html", {"message": "To nie jest kompilacja gier."})

    return render(request, "frontend/compilation.html", {"data": result})

@jwt_required
def my_library_view(request):
    user = None
    if isinstance(request.user, UserModel):
        user = request.user
    else:
        user = UserModel.objects.filter(username=request.user.username).first()

    if not user:
        print(f"[my_library] Brak dopasowania użytkownika: {request.user}")
        return HttpResponseForbidden("Nie znaleziono użytkownika w bazie danych.")

    try:
        user_history = UserHistory.objects.filter(user_id=user.id).order_by('-viewed_at')
        print(f"[my_library] Historia użytkownika {user.username}: {user_history.count()} rekordów")
    except Exception as e:
        print(f"[my_library] Błąd przy pobieraniu historii: {e}")
        return HttpResponseForbidden("Błąd przy pobieraniu historii użytkownika.")

    history_data = []
    for entry in user_history:
        game = Games.objects.filter(id=entry.game_id_id).first()
        if game:
            history_data.append({
                "id": game.id,
                "title": game.title,
                "cover_image": game.cover_image,
                "viewed_at": entry.viewed_at,
            })

    paginator = Paginator(history_data, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    return render(request, "frontend/my_library.html", {"page_obj": page_obj})


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
    from django.db.models import Avg
    from django.db.models.functions import Trim

    sort_option = request.GET.get('sort', 'oldest')
    query = (request.GET.get('q') or '').strip()
    selected_genre = (request.GET.get('genre') or '').strip()

    # bazowe zapytanie + filtr tytułu i gatunku
    base_qs = Games.objects.all()
    if query:
        base_qs = base_qs.filter(title__icontains=query)
    if selected_genre:
        base_qs = base_qs.filter(genre__iexact=selected_genre)

    # sortowanie
    qs = base_qs
    if sort_option == 'newest':
        qs = qs.order_by('-id')
    elif sort_option == 'score':
        qs = qs.order_by('-score')
    elif sort_option == 'rating':
        qs = qs.annotate(avg_rating=Avg('game_ratings__rating')).order_by('-avg_rating')
    else:
        qs = qs.order_by('id')  # oldest

    # unikalne gatunki do panelu (posortowane alfabetycznie)
    genres = (
        Games.objects.exclude(genre__isnull=True).exclude(genre='')
        .annotate(genre_clean=Trim('genre'))
        .values_list('genre_clean', flat=True).distinct().order_by('genre_clean')
    )

    # dane do widoku
    games_with_ratings = []
    for game in qs:
        avg_rating = UserRatings.objects.filter(game_id=game).aggregate(Avg('rating'))['rating__avg']
        games_with_ratings.append({
            "id": game.id,
            "title": game.title,
            "cover_image": game.cover_image,
            "score": game.score,
            "rating": round(avg_rating, 2) if avg_rating else None,
        })

    return render(request, "frontend/explore.html", {
        "games": games_with_ratings,
        "sort_option": sort_option,
        "query": query,
        "genres": genres,
        "selected_genre": selected_genre,
    })


@jwt_required
def profile_view(request):
    user = None
    if isinstance(request.user, UserModel):
        user = request.user
    else:
        user = UserModel.objects.filter(username=request.user.username).first()

    if not user:
        return HttpResponseForbidden("Could not find the user")

    message = None

    if request.method == "POST":
        action = request.POST.get("action")

        # Zmiana nazwy użytkownika
        if action == "change_username":
            new_username = request.POST.get("new_username", "").strip()
            if new_username and new_username != user.username:
                if not UserModel.objects.filter(username=new_username).exists():
                    user.username = new_username
                    user.save()
                    message = "Username has been changed!"
                else:
                    message = "This username already exists!"

        # Zmiana hasła
        elif action == "change_password":
            new_password = request.POST.get("new_password", "").strip()
            if new_password:
                user.password = make_password(new_password)
                user.save()
                message = "The password has been changed!"

        # Zmiana zdjęcia profilowego
        elif action == "change_profile_picture":
            if "profile_picture" in request.FILES:
                uploaded_file = request.FILES["profile_picture"]
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile

                filename = f"profile_pictures/{user.username}_{uploaded_file.name}"
                file_path = default_storage.save(filename, ContentFile(uploaded_file.read()))
                user.profile_picture = file_path
                user.save()
                message = "Profile picture updated successfully!"
            else:
                message = "No file uploaded!"

        # Wylogowanie
        elif action == "logout":
            response = redirect("/app/login/")
            response.delete_cookie("access_token")
            return response

    return render(request, "frontend/profile.html", {"user": user, "message": message})



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
            answer = "I'm sorry, I couldn't generate an answer this time. Please try asking again."
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


@csrf_exempt
@jwt_required
def generate_summary_view(request, pk):
    """
    Generuje streszczenie fabuły gry po kliknięciu przycisku "Generate Summary".
    Działa identycznie jak proces scrapowania, używając extract_plot_structure, build_markdown_with_headings i summarize_plot_sections.
    """
    import markdown
    from bs4 import BeautifulSoup
    from .utils import summarize_plot_sections, build_markdown_with_headings, extract_plot_structure

    game = get_object_or_404(Games, pk=pk)
    plot = GamePlots.objects.filter(game_id=game).first()

    if not plot:
        return JsonResponse({"error": "Brak fabuły do streszczenia."}, status=400)

    # Jeśli już istnieje streszczenie, nie generujemy ponownie
    if plot.summary and "No Summary Available" not in plot.summary:
        return JsonResponse({"summary": markdown.markdown(plot.summary)})

    # Jeśli nie ma pełnej fabuły lub zawiera komunikat "No Plot Found"
    if not plot.full_plot or "No Plot Found" in plot.full_plot:
        return JsonResponse({"error": "Brak fabuły do streszczenia."}, status=400)

    try:
        # --- Zdekoduj markdown fabuły i odtwórz strukturę z nagłówkami ---
        soup = BeautifulSoup(plot.full_plot, "html.parser")
        text_content = soup.get_text()
        if not text_content.strip():
            return JsonResponse({"error": "Nie można odczytać treści fabuły."}, status=400)

        # --- Próba ponownego wydobycia struktury sekcji ---
        plot_tree = extract_plot_structure(soup)
        if not plot_tree:
            # Jeśli nie uda się odtworzyć struktury — streść cały tekst, ale z chunkami
            from .utils import get_summarizer
            summarizer = get_summarizer()
            text = text_content.strip()
            words = len(text.split())
            if words < 80:
                summary_text = text
            elif words < 200:
                res = summarizer(text, max_length=120, min_length=50, do_sample=False)
                summary_text = res[0]["summary_text"]
            elif words < 500:
                res = summarizer(text, max_length=160, min_length=80, do_sample=False)
                summary_text = res[0]["summary_text"]
            else:
                chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]
                partials = []
                for ch in chunks:
                    res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                    partials.append(res[0]["summary_text"])
                summary_text = " ".join(partials)
            summary_md = summary_text
        else:
            # --- Użyj Twojej funkcji do streszczania sekcji ---
            summary_md = summarize_plot_sections(plot_tree)
            if not summary_md:
                return JsonResponse({"summary": "<p>Fabuła jest zbyt krótka, by wymagała streszczenia.</p>"})

        # Zbuduj markdown z nagłówkami (żeby zachować format)
        final_md = build_markdown_with_headings(plot_tree)
        plot.summary = summary_md
        plot.save(update_fields=["summary"])

        return JsonResponse({"summary": markdown.markdown(summary_md)})

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
    Główny panel administratora – wyświetla listę użytkowników i gier
    """
    # tylko admin (np. username == 'admin')
    if not getattr(request.user, "is_admin", False):
        return HttpResponseForbidden("Brak uprawnień do panelu administratora")

    users = UserModel.objects.all().order_by("id")
    games = Games.objects.all().order_by("id")

    return render(request, "frontend/admin_panel.html", {
        "users": users,
        "games": games
    })


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
    if not request.user.is_admin:
        return JsonResponse({"error": "Access denied"}, status=403)

    users = UserModel.objects.all().order_by("id")
    return render(request, "frontend/admin_users.html", {"users": users})


@jwt_required
def admin_games_view(request):
    if not request.user.is_admin:
        return JsonResponse({"error": "Access denied"}, status=403)

    games = Games.objects.all().order_by("id")
    return render(request, "frontend/admin_games.html", {"games": games})
