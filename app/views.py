from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model, user_logged_in
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.decorators import api_view, permission_classes
from .serializers import (GamesSerializer, GamePlotsSerializer, UserHistorySerializer, UserSerializer,
                          ChatBotSerializer)
from .models import Games, GamePlots, UserModel, UserHistory, ChatBot
from .utils import search_mobygames, scrape_game_info, record_user_history, jwt_required
from decimal import Decimal, InvalidOperation
import asyncio
import json
import re
import markdown
import uuid
import requests, os


# Create your views here.
def main(request):
    return HttpResponse("Hello")

class UserView(generics.ListCreateAPIView):
    queryset = UserModel.objects.all()  # Zapytanie do SQL o wszystkich użytkowników
    serializer_class = UserSerializer  # Serializer do danych użytkownika
    permission_classes = [AllowAny]

class LoginOrEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        User = get_user_model()
        uname_field = User.USERNAME_FIELD  # "username" albo "email"
        if uname_field not in attrs:
            login_val = (
                self.initial_data.get("login")
                or self.initial_data.get("username")
                or self.initial_data.get("email")
            )
            if login_val:
                attrs[uname_field] = login_val
        return super().validate(attrs)

class LoginView(TokenObtainPairView):
    serializer_class = LoginOrEmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        data = response.data

        # zapis tokena do cookie
        response.set_cookie(
            key="access_token",
            value=data["access"],
            httponly=True,
            samesite="Lax"
        )
        return response

class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = UserModel.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        print(request.data)
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # [PL] Sprawdzamy, czy hasło nie jest zapisane w postaci czystego tekstu
            from django.contrib.auth.hashers import make_password
            if not user.password.startswith("pbkdf2_"):
                user.password = make_password(user.password)
                user.save(update_fields=["password"])

            return Response(
                {"message": "User created successfully!", "user_id": user.id},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    # Self-explanatory but it renders the site using the correct html file and uses results and query variables as the
    # needed results of the query (pleonasm or "masło maślane", as one would call it but that's just how it works)
    return render(request, 'frontend/search_results.html', {'results': results, 'query': query})



# When the json is being passed to the database, the database cannot accept the results in decimal, dictionary or a list
# format and therefore must be changed into a format the database can read. This function is not that often used as it
# may seem, however it was in the original version of the ai implementation and I don't remember exactly how useful it
# is for the current needs of the code so it's been decided to let it stay just in case
def safe_json(obj):
    from decimal import Decimal
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
    # Url to the MobyGames page for the chosen game
    url = request.GET.get('url')
    if not url:
        return HttpResponseBadRequest('Missing url')

    # This tries to extract the title from the previously saved search results in the session
    title_guess = None
    for r in request.session.get('ai_last_results', []):
        # If one of the stored search results matches the current URL
        if r.get('url') == url:
            # Generally the way it works is that it extracts the first line from the game description shown in search
            # results. After it finds it, it uses regex to try to extract the game's title so it can later check if that
            # record is already stored in the database so that it doesn't have to scrape everything again
            first_line = (r.get('description') or '').splitlines()[0].strip()
            m = re.match(r'(.+?)\s*\((?:[^)]*)\)\s*', first_line)
            title_guess = (m.group(1) if m else first_line).strip()
            break

    # If the game is indeed found in the database, then this piece of code redirects the user to that page
    if title_guess:
        existing = Games.objects.filter(title__iexact=title_guess).first()
        if existing:
            # If the game is in the database already then it saves this record into the user history
            record_user_history(request.user, existing)
            return redirect('game_detail_page', pk=existing.id)

    # Scraping the data using scrape_game_info function from utils.py
    data = asyncio.run(scrape_game_info(url, media_root=settings.MEDIA_ROOT, save_image=True))

    # If something generally goes wrong the site redirects to error.html so that it doesn't display the confusing django
    # error message to the user
    if not data:
        print(f"[ERROR] Scraper returned None for URL: {url}")
        return render(request, "frontend/error.html", {
            "message": "Nie udało się pobrać danych o grze. Spróbuj ponownie."
        })

    # Previously I explained in utils.py about game results that are compilations of games rather than single games
    # themselves and this if statement handles that case by redirecting the user to the corresponding site
    if data.get("is_compilation"):
        return redirect(f"/app/compilation/?url={url}")

    # Once again this piece of code converts the decimal values into float ones so that the data passed is database
    # friendly. One might argue that this is already handled by safe_json function, and it might as well be, however at
    # this point I have no idea if that's true and in case it isn't, both of those stay in this code. Some would call it
    # laziness, but I call it insurance
    for key, val in list(data.items()):
        if isinstance(val, Decimal):
            data[key] = float(val)

    # Some games on MobyGames do not have their score, which is done by the MobyGames moderators (for example the niche
    # games like R.E.P.O). To ensure that the app doesn't collapse on itself cause of that one value, this try statement
    # handles score attribute to set it to None once such score is not present
    try:
        if data.get('score'):
            data['score'] = Decimal(str(data['score']))
        else:
            data['score'] = None
    except (InvalidOperation, TypeError, ValueError):
        data['score'] = None

    # Creates a new record in the database with the following values
    games = Games.objects.create(
        title=data.get('title') or 'Unknown',
        release_date=data.get('release_date'),
        genre=data.get('genre'),
        studio=data.get('studio'),
        score=data.get('score'),
        cover_image=data.get('cover_image'),
    )
    GamePlots.objects.create(
        game_id=games,
        full_plot=data.get('full_plot') or '',
        summary=data.get('summary') or '',
    )

    # The game is recorded into user history after being scraped
    record_user_history(request.user, games)

    # Redirects the user to the game_detail_page after scraping all the necessary data, in which everything is displayed
    # in user-friendly format
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
    from .models import UserModel, Games, UserHistory

    user = None
    # [PL] Upewniamy się, że mamy rzeczywisty obiekt z tabeli Users
    if isinstance(request.user, UserModel):
        user = request.user
    else:
        user = UserModel.objects.filter(username=request.user.username).first()

    if not user:
        print(f"[my_library] Brak dopasowania użytkownika: {request.user}")
        return HttpResponseForbidden("Nie znaleziono użytkownika w bazie danych.")

    # [PL] Pobieramy historię użytkownika (ostatnio oglądane gry)
    try:
        user_history = UserHistory.objects.filter(user_id=user.id).order_by('-viewed_at')
        print(f"[my_library] Historia użytkownika {user.username}: {user_history.count()} rekordów")
    except Exception as e:
        print(f"[my_library] Błąd przy pobieraniu historii: {e}")
        return HttpResponseForbidden("Błąd przy pobieraniu historii użytkownika.")

    # [PL] Tworzymy dane do wyświetlenia (tytuł, id i cover)
    history_data = []
    for entry in user_history:
        game = Games.objects.filter(id=entry.game_id_id).first()
        if game:
            history_data.append({
                "id": game.id,
                "title": game.title,
                "cover_image": game.cover_image,  # <-- dodane
                "viewed_at": entry.viewed_at,
            })

    paginator = Paginator(history_data, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    return render(request, "frontend/my_library.html", {"page_obj": page_obj})


@jwt_required
@csrf_exempt
def delete_history_entry(request):
    # [PL] Funkcja do usuwania historii gry użytkownika
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        game_id = data.get("game_id")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not game_id:
        return JsonResponse({"error": "Missing game_id"}, status=400)

    from .models import UserHistory, ChatBot, Games, UserModel

    # [PL] Upewniamy się, że użytkownik istnieje
    user = None
    if isinstance(request.user, UserModel):
        user = request.user
    else:
        user = UserModel.objects.filter(username=request.user.username).first()

    if not user:
        return JsonResponse({"error": "User not found"}, status=403)

    # [PL] Sprawdzenie, czy gra istnieje
    game = Games.objects.filter(id=game_id).first()
    if not game:
        return JsonResponse({"error": "Game not found"}, status=404)

    # [PL] Usuwamy historię użytkownika i powiązane wpisy chatu
    deleted_history = UserHistory.objects.filter(user_id=user, game_id=game).delete()
    deleted_chat = ChatBot.objects.filter(user_id=user, game_id=game).delete()

    print(f"[delete_history_entry] Removed: {deleted_history[0]} from UserHistory, {deleted_chat[0]} from ChatBot.")

    return JsonResponse({"message": "Record deleted successfully."})


# View for the game explore page where the user can choose from any of the games already in the database. Of course once
# they click one of the links to the game detail page, that game is then saved into their library. This view is not
# require the user to log in, however when they want to view one of the games in detail, then they must log in
def explore_view(request):
    games = Games.objects.all().order_by("id")
    return render(request, "frontend/explore.html", {"games": games})


@jwt_required
def profile_view(request):
    from .models import UserModel
    from django.contrib.auth.hashers import make_password

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

        # Wylogowanie (czyli usunięcie JWT z sesji)
        elif action == "logout":
            response = redirect("/app/login/")  # lub inna Twoja strona logowania
            response.delete_cookie("access_token")  # usunięcie JWT
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




