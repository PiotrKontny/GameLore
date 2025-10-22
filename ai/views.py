import asyncio
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import GameSerializer, GamePlotSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from .utils import search_mobygames, scrape_game_info
from .models import Games, GamePlot
import re
import markdown
from decimal import Decimal, InvalidOperation


# As the name suggests, it's a class for viewing games (GET operator)
class GamesViewSet(viewsets.ReadOnlyModelViewSet):
    # Allows all the users, even those not logged into the app, to view them
    permission_classes = [AllowAny]
    queryset = Games.objects.order_by('-id')
    serializer_class = GameSerializer



# Same as GamesViewSet but with gameplots instead
class GamePlotsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GamePlot.objects.select_related('game').order_by('-id')
    serializer_class = GamePlotSerializer


# The @api_view decorator turns this regular Django view into a Django REST Framework API endpoint. It ensures that the
# view only accepts GET requests and returns JSON responses instead of HTML.
@api_view(['GET'])
def game_detail(request, pk: int):
    # Tries to retrieve game object using the primary key (pk), in this case being game_id. On the website, when opening
    # the game details the page url has the same pk number as the game_id it's based on
    game = get_object_or_404(Games, pk=pk)
    return Response(GameSerializer(game).data)



# The usage of csrf decorator is so that the API endpoints can retrieve requests from external clients such as
# JavaScript that don’t include CSRF tokens. In the code below it's used to access MobyGames website for scraping
@csrf_exempt
def search_view(request):
    if request.method == 'GET':
        return render(request, 'ai/search_form.html')
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
    return redirect(reverse('ai_results'))


# Displays the results of searching the game
def results_view(request):
    # Returns the last results saved in the session from the previous function. It also returns an empty list to not
    # cause any errors. Pretty much same happens with query variable
    results = request.session.get('ai_last_results') or []
    query = request.session.get('ai_last_query') or ''
    # Self-explanatory but it renders the site using the correct html file and uses results and query variables as the
    # needed results of the query (pleonasm or "masło maślane", as one would call it but that's just how it works)
    return render(request, 'ai/search_results.html', {'results': results, 'query': query})



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
def details_view(request):
    from .models import Games

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
            return redirect('game_detail_page', pk=existing.id)

    # Scraping the data using scrape_game_info function from utils.py
    data = asyncio.run(scrape_game_info(url, media_root=settings.MEDIA_ROOT, save_image=True))

    # If something generally goes wrong the site redirects to error.html so that it doesn't display the confusing django
    # error message to the user
    if not data:
        print(f"[ERROR] Scraper returned None for URL: {url}")
        return render(request, "ai/error.html", {
            "message": "Nie udało się pobrać danych o grze. Spróbuj ponownie."
        })

    # Previously I explained in utils.py about game results that are compilations of games rather than single games
    # themselves and this if statement handles that case by redirecting the user to the corresponding site
    if data.get("is_compilation"):
        return redirect(f"/ai/compilation/?url={url}")

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
    GamePlot.objects.create(
        game=games,
        full_plot=data.get('full_plot') or '',
        summary=data.get('summary') or '',
    )

    # Redirects the user to the game_detail_page after scraping all the necessary data, in which everything is displayed
    # in user-friendly format
    return redirect('game_detail_page', pk=games.id)



# As explained couple lines before, this part of code handles displaying the scraped results for each game
def game_detail_page(request, pk):
    game = get_object_or_404(Games, pk=pk)
    plot = GamePlot.objects.filter(game=game).first()

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
        return render(request, "ai/error.html", {"message": "Brak adresu URL"})

    result = asyncio.run(scrape_game_info(url, settings.MEDIA_ROOT))

    if not result.get("is_compilation"):
        return render(request, "ai/error.html", {"message": "To nie jest kompilacja gier."})

    return render(request, "ai/compilation.html", {"data": result})


