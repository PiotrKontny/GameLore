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

class GamesViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Games.objects.order_by('-id')
    serializer_class = GameSerializer

class GamePlotsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GamePlot.objects.select_related('game').order_by('-id')
    serializer_class = GamePlotSerializer

@api_view(['GET'])
def game_detail(request, pk: int):
    game = get_object_or_404(Games, pk=pk)
    return Response(GameSerializer(game).data)


# ——— 1) Wejście: wpisanie gry (HTML form albo JSON POST {"game": "Cyberpunk 2077"})
@csrf_exempt
def search_view(request):
    if request.method == 'GET':
        return render(request, 'ai/search_form.html')
    # POST: JSON albo form-urlencoded
    game = None
    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body.decode('utf-8'))
            game = (payload.get('game') or '').strip()
        except:
            return HttpResponseBadRequest('Invalid JSON')
    else:
        game = (request.POST.get('game') or '').strip()

    if not game:
        return HttpResponseBadRequest('Missing "game"')

    results = asyncio.run(search_mobygames(game))
    # jeśli klient prosi o JSON (np. fetch), oddaj JSON
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'query': game, 'results': results})

    # HTML – pokaż listę
    request.session['ai_last_results'] = results  # sesja na jedno przejście
    request.session['ai_last_query'] = game
    return redirect(reverse('ai_results'))


# ——— 2) Lista wyników do wyboru
def results_view(request):
    results = request.session.get('ai_last_results') or []
    query = request.session.get('ai_last_query') or ''
    return render(request, 'ai/search_results.html', {'results': results, 'query': query})

def make_json_safe(obj):
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    return obj

# ——— 3) Szczegóły wybranego wyniku (scrape + podsumowanie), wyświetl i pozwól zapisać
def details_view(request):
    from .models import Games
    url = request.GET.get('url')
    if not url:
        return HttpResponseBadRequest('Missing url')

    # 1) Spróbuj wyciągnąć tytuł z wyników zapisanych w sesji
    title_guess = None
    for r in request.session.get('ai_last_results', []):
        if r.get('url') == url:
            first_line = (r.get('description') or '').splitlines()[0].strip()
            m = re.match(r'(.+?)\s*\((?:[^)]*)\)\s*', first_line)
            title_guess = (m.group(1) if m else first_line).strip()
            break

    # 2) Jeśli gra już istnieje w bazie → przekierowanie
    if title_guess:
        existing = Games.objects.filter(title__iexact=title_guess).first()
        if existing:
            return redirect('game_detail_page', pk=existing.id)

    # 3) Scrapowanie danych
    data = asyncio.run(scrape_game_info(url, media_root=settings.MEDIA_ROOT, save_image=True))

    if not data:
        print(f"[ERROR] Scraper returned None for URL: {url}")
        return render(request, "ai/error.html", {
            "message": "Nie udało się pobrać danych o grze. Spróbuj ponownie."
        })

    if data.get("is_compilation"):
        return redirect(f"/ai/compilation/?url={url}")

    # --- reszta bez zmian ---
    from decimal import Decimal
    for key, val in list(data.items()):
        if isinstance(val, Decimal):
            data[key] = float(val)

    from .models import Games, GamePlot

    games = Games.objects.create(
        title=data.get('title') or 'Unknown',
        release_date=data.get('release_date'),
        genre=data.get('genre'),
        studio=data.get('studio'),
        score=data.get('score'),
        cover_image=data.get('cover_image_relpath'),
    )
    GamePlot.objects.create(
        game=games,
        full_plot=data.get('full_plot') or '',
        summary=data.get('summary') or '',
    )

    return redirect('game_detail_page', pk=games.id)


    # przekierowanie do JSON-a z API
    return redirect('game_detail_page', pk=games.id)

def game_detail_page(request, pk):
    game = get_object_or_404(Games, pk=pk)
    plot = GamePlot.objects.filter(game=game).first()

    full_plot_html = ""
    summary_html = ""

    if plot:
        # Konwersja Markdown → HTML (### → <h3>, #### → <h4>, itd.)
        full_plot_html = markdown.markdown(plot.full_plot or "")
        summary_html = markdown.markdown(plot.summary or "")

    return render(request, 'frontend/game_detail.html', {
        'game': game,
        'plot': plot,
        'full_plot_html': full_plot_html,
        'summary_html': summary_html,
    })




# ——— 4) Zapis do DB (Games + GamePlots) i przekierowanie do JSON podglądu
def save_view(request):
    data = request.session.get('ai_pending_data')
    if not data:
        return HttpResponseBadRequest('Nothing to save')

    game = Games.objects.create(
        title=data.get('title') or 'Unknown',
        release_date=data.get('release_date'),
        genre=data.get('genre'),
        studio=data.get('studio'),
        score=data.get('score'),
        cover_image=data.get('cover_image_relpath')
    )
    GamePlot.objects.create(
        game=game,
        full_plot=data.get('full_plot') or '',
        summary=data.get('summary') or ''
    )

    request.session.pop('ai_pending_data', None)

    return HttpResponseRedirect(reverse('api_game_detail', args=[game.id]))


def scrape_details_view(request):
    """Scrapuje dane gry i zapisuje ją do bazy, o ile nie istnieje już taki tytuł."""
    url = request.GET.get("url")
    if not url:
        return render(request, "ai/error.html", {"message": "Brak adresu URL"})

    from .models import Games, GamePlot
    import re

    # ——— 1️⃣ Wyciągnięcie tytułu z URL-a
    title_guess = None
    m = re.search(r'/game/\d+/(.+?)/?$', url)
    if m:
        title_guess = m.group(1).replace('-', ' ').replace('_', ' ').strip().title()

    # ——— 2️⃣ Szybkie sprawdzenie po "podobieństwie" (nie idealnym dopasowaniu)
    if title_guess:
        normalized_guess = re.sub(r'[^a-z0-9]', '', title_guess.lower())

        existing_game = None
        for g in Games.objects.all():
            normalized_db = re.sub(r'[^a-z0-9]', '', g.title.lower())
            if normalized_guess in normalized_db or normalized_db in normalized_guess:
                existing_game = g
                break

        if existing_game:
            print(f"[FAST REDIRECT] Matched existing title: {existing_game.title} ←→ {title_guess}")
            return redirect("game_detail_page", pk=existing_game.id)

    # ——— 3️⃣ Dopiero wtedy scrapujemy
    result = asyncio.run(scrape_game_info(url, settings.MEDIA_ROOT))

    # ——— 4️⃣ Jeśli to kompilacja → przekieruj do wyboru
    if result.get("is_compilation"):
        return redirect(f"/ai/compilation/?url={url}")

    # ——— 5️⃣ Ostateczne sprawdzenie po dokładnym tytule
    existing = Games.objects.filter(title__iexact=result.get("title", "")).first()
    if existing:
        print(f"[INFO] Skipping save — already exists: {existing.title}")
        return redirect("game_detail_page", pk=existing.id)

    # ——— 6️⃣ Zapis nowej gry
    from decimal import Decimal
    for k, v in list(result.items()):
        if isinstance(v, Decimal):
            result[k] = float(v)

    game = Games.objects.create(
        title=result.get("title") or "Unknown",
        release_date=result.get("release_date"),
        genre=result.get("genre"),
        studio=result.get("studio"),
        score=result.get("score"),
        cover_image=result.get("cover_image_relpath"),
    )
    GamePlot.objects.create(
        game=game,
        full_plot=result.get("full_plot") or "",
        summary=result.get("summary") or "",
    )

    print(f"[SCRAPE COMPLETE] Saved new game: {game.title}")
    return redirect("game_detail_page", pk=game.id)






def compilation_view(request):
    """Wyświetla stronę z wyborem gier z bundla (kompilacji)."""
    url = request.GET.get("url")
    if not url:
        return render(request, "ai/error.html", {"message": "Brak adresu URL"})

    result = asyncio.run(scrape_game_info(url, settings.MEDIA_ROOT))

    if not result.get("is_compilation"):
        return render(request, "ai/error.html", {"message": "To nie jest kompilacja gier."})

    return render(request, "ai/compilation.html", {"data": result})


