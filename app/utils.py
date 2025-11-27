from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.http import  JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from .models import UserModel, Games, UserHistory
from playwright.async_api import async_playwright
from transformers import pipeline
from bs4 import BeautifulSoup
from shutil import copyfile
import urllib.parse
import os
import re
import time
from io import BytesIO
import requests
from PIL import Image
from functools import wraps


# As the name suggests, this function records user history. But what does it mean exactly? Each user has his own user
# history with the games he has visited. If the game which he visits when opening game detail page hasn't been recorded
# already in the database, it saves this pair of user id and game id. However, if the user already has the viewed game in his
# history then the "viewed_at" column is updated
def record_user_history(user, game, refresh_timestamp=True):
    # The user history is not being recorded if the user hasn't logged in
    if not user or not getattr(user, "is_authenticated", False):
        return

    try:
        # Just in case, this piece of code checks if the user and the game are the objects from the database. This was
        # used to handle one instance which appeared while developing the code, and it stayed since it doesn't disrupt
        # anything, however I'm not sure if its absence wouldn't
        if not isinstance(user, UserModel):
            user = UserModel.objects.filter(username=user.username).first()
        if not isinstance(game, Games):
            game = Games.objects.filter(id=game.id).first()

        if not user or not game:
            return

        # If the game exists in user's history then it just updates viewed_at attribute, if it doesn't, it creates a new
        # record in the database
        existing = UserHistory.objects.filter(user_id=user, game_id=game).first()
        if existing:
            if refresh_timestamp:
                existing.viewed_at = timezone.now()
                existing.save(update_fields=["viewed_at"])
        else:
            UserHistory.objects.create(user_id=user, game_id=game)

    except Exception as e:
        print(f"[record_user_history] Error: {e}")


# This function checks whether the request expects a JSON response rather than a standard HTML error page.
def _wants_json(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return True
    accept = request.headers.get("Accept", "")
    if "application/json" in accept:
        return True
    return False

# This is the function responsible for the main mechanism of authorization. It works as a decorator, so basically
# something that I put before the functions in views.py to make those pages require an authorization handled by this
# function.
def jwt_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        # This if statement is meant for the app's scalability as it ignores jwt_required decorator for the superusers
        # also known as Django session admins. This app currently does not use it but it might in the future.
        if getattr(request.user, "is_authenticated", False) and getattr(request.user, "is_superuser", False):
            print("[JWT] SKIPPING JWT CHECK FOR ADMIN (session auth)")
            return view_func(request, *args, **kwargs)

        wants_json = _wants_json(request)
        jwt_auth = JWTAuthentication()

        token = None

        # Checking the header Authorization Bearer (basically the access token given to each user after logging in)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            candidate = auth_header.split(" ", 1)[1].strip()
            if candidate and candidate.lower() not in ("null", "undefined"):
                token = candidate

        # If there is no token found in the previous if statement then the app checks cookies
        if not token:
            token = request.COOKIES.get("access_token")

        # No token means that the user is not logged in
        if not token:
            print("[JWT] There is no JSON Web Token (JWT)")

            if wants_json:
                return JsonResponse({"error": "There is no JWT"}, status=401)
            else:
                # Redirects to the already prepared error 401 page
                return redirect("/error/401")

        # JWTAuthentication requires Authorization Bearer token
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        try:
            # The attempt to authorize the token
            user_auth_tuple = jwt_auth.authenticate(request)

            # If the authenticate function returns None then the token is deemed as wrong or expired
            if not user_auth_tuple:
                print("[JWT] The token is wrong or expired (authenticate has returned None).")
                if wants_json:
                    return JsonResponse(
                        {"error": "Token JWT is wrong or it expired."},
                        status=403,
                    )
                else:
                    return redirect("/error/403")

            jwt_user, validated_token = user_auth_tuple

            # Checking if the user exists in the database
            mapped_user = (
                UserModel.objects.filter(pk=jwt_user.pk).first()
                or UserModel.objects.filter(username=jwt_user.username).first()
                or UserModel.objects.filter(email=jwt_user.email).first()
            )

            if not mapped_user:
                print("[JWT] The user from the token does not exist in the database.")
                if wants_json:
                    return JsonResponse({"error": "The user does not exist"}, status=403)
                else:
                    return redirect("/error/403")

            # The user is authenticated
            request.user = mapped_user
            print(f"[JWT] Authenticated user: {mapped_user.username}")

            return view_func(request, *args, **kwargs)

        # The authentication failed due to SimpleJWT
        except AuthenticationFailed as e:
            print(f"[JWT] AuthenticationFailed: {e}")
            if wants_json:
                return JsonResponse({"error": "Token JWT is wrong or it expired."}, status=403)
            else:
                return redirect("/error/403")

        # Any other unexpected errors
        except Exception as e:
            print(f"[JWT] Authentication failed (internal error): {e!r}")
            if wants_json:
                return JsonResponse({"error": "Error in JWT authentication."}, status=500)
            else:
                return redirect("/error/500")

    return _wrapped_view


# Requesting user without throwing errors like jwt_required. Used for simpler functions like saving the game to history
# or giving a rating. With its similarity to jwt_required, the explanation is not needed.
def get_jwt_user(request):
    jwt_auth = JWTAuthentication()

    if "HTTP_AUTHORIZATION" not in request.META:
        token = request.COOKIES.get("access_token")
        if token:
            request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    try:
        user_auth_tuple = jwt_auth.authenticate(request)
        if user_auth_tuple is not None:
            jwt_user, _ = user_auth_tuple
            mapped_user = (
                UserModel.objects.filter(username=jwt_user.username).first()
                or UserModel.objects.filter(email=jwt_user.email).first()
            )
            if mapped_user:
                return mapped_user
    except Exception as e:
        print(f"[get_jwt_user] Auth error: {e}")
    return None


# This class allows JWT authentication using the access_token cookie when the Authorization header is not provided.
class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # First tries the standard authorization header method
        header = self.get_header(request)
        if header:
            return super().authenticate(request)

        # If there is no header then it tries to get token from cookies
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        # Token validation
        validated_token = self.get_validated_token(raw_token)
        try:
            user = self.get_user(validated_token)
        except Exception:
            raise AuthenticationFailed("Invalid token in cookie", code="authentication_failed")

        return (user, validated_token)



# Model for summarization is used a couple of times in this file therefore it's declared at the beginning. It's also in
# case of future need to change the summarization model
summarizer = None
def get_summarizer():
    global summarizer
    if summarizer is None:
        summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    return summarizer


# Further into the code there is a moment where a cover image of the game scraped is being downloaded and this function
# is so that it can have a proper name when downloaded
def image_name(title: str) -> str:
    s = title.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s

# Function for extracting game plot from Wikipedia
def extract_plot_structure(soup: BeautifulSoup) -> dict:
    # Scans the page in search for something resembling plot header by searching this words:
    valid_sections = ["Plot", "Synopsis", "Premise", "Story", "Lore"]
    plot_heading = None
    plot_h2_title = None

    # mw-heading2 class is used for main headings on wikipedia and that's where one can find plot heading. This loop
    # searches for such heading and when it does find it then the div it's contained in is saved into a variable
    for div in soup.find_all("div", class_="mw-heading mw-heading2"):
        h2 = div.find("h2")
        if h2 and h2.get("id") in valid_sections:
            plot_heading = div
            plot_h2_title = h2.get_text(strip=True)
            break

    # In case of a situation where a game doesn't have any plot (e.g. Minecraft) the scraper goes back to Moby Games
    # website to scrap the game's description as the only "plot" description needed, however that functionality is in a
    # different part of the code. This one just returns an empty dictionary
    if not plot_heading:
        return {}

    # The plot section on Wikipedia might have its own headings (mw-heading3) and their headings might have headings of
    # their own (mw-heading4) and so Playwright is supposed to scrape the plot in a form of a dictionary where the first
    # heading type, mw-heading3, is the key and its content is the value. However, if the content contains another
    # heading, the mw-heading4, it opens a new dictionary for it which works the same way. To explain how it works on
    # the example let's bring up Elden Ring's wikipedia website. The synopsis there has two main headings (mw-heading3),
    # Premise and Plot. The Premise heading has only text in it, however Plot heading has two headings of its own with
    # separate plots for Elden Ring's main plot and its DLC called Shadow of the Erdtree. In order to not confuse the
    # summarizer model and make up for a better summarization, the contents of those two are separated and later the
    # summarizer makes a separate summary for both. Essentially the whole reason for this is so that every field of text
    # is treated as independent of each other.
    plot_data = {}
    current_h3 = None
    current_h4 = None

    # This loop is so that when Playwright encounters another heading that is the main heading on Wikipedia
    # (mw-heading2) it's supposed to stop scraping (basically when it leaves the plot area of Wikipedia), but also it's
    # used for any other heading to separate them in the dictionary
    for elem in plot_heading.find_next_siblings():
        if elem.name == "div" and "mw-heading2" in (elem.get("class") or []):
            break

        if elem.name == "div" and "mw-heading3" in (elem.get("class") or []):
            current_h3 = elem.find("h3").get_text(strip=True)
            current_h4 = None
            plot_data[current_h3] = ""
            continue

        if elem.name == "div" and "mw-heading4" in (elem.get("class") or []):
            current_h4 = elem.find("h4").get_text(strip=True)
            if isinstance(plot_data.get(current_h3), dict):
                plot_data[current_h3][current_h4] = ""
            else:
                plot_data[current_h3] = {current_h4: ""}
            continue

        # Html text tag on wikipedia
        if elem.name == "p":
            text = elem.get_text(" ", strip=True)
            if not text:
                continue
            if current_h4:
                plot_data[current_h3][current_h4] += " " + text
            elif current_h3:
                if isinstance(plot_data[current_h3], dict):
                    pass
                else:
                    plot_data[current_h3] += " " + text
            else:
                if plot_h2_title not in plot_data:
                    plot_data[plot_h2_title] = ""
                plot_data[plot_h2_title] += " " + text

    # Scraping html sometimes comes with having empty lines or in this case also empty values for some keys. This loop
    # fixes that issue and makes sure that the plot in the database isn't saved as "None"
    #
    #
    # NOT SURE IF THIS SHOULD STAY OR BE DELETED
    cleaned = {}
    for k, v in plot_data.items():
        if isinstance(v, dict):
            sub = {kk: vv.strip() for kk, vv in v.items() if vv.strip()}
            if sub:
                cleaned[k] = sub
        else:
            if v.strip():
                cleaned[k] = v.strip()
    return cleaned


# The website's game page uses markdown to mark headings. This entire function is used just for adding necessary "#"
# symbols so that markdown library can recognise those marked by # as a new heading
def build_markdown_with_headings(plot_tree: dict) -> str:
    lines = []
    for h3, content in plot_tree.items():
        lines.append(f"### {h3}")
        if isinstance(content, dict):
            for h4, text in content.items():
                lines.append(f"#### {h4}")
                lines.append(text.strip())
                lines.append("")
        else:
            lines.append(content.strip())
            lines.append("")
    return "\n".join(lines).strip()


# As previously mentioned, the summarizer doesn't just summarize a simple field of text scraped from the wikipedia, but
# it does so for every section (which are divided by mw-heading3 and mw-heading4) it scraped. Also, this function is
# using total_threshold as an argument, which is set to 200. What it means is that when the total number of words in the
# plot section on wikipedia doesn't exceed 200 words then the summary is not needed and therefore is neglected
def summarize_plot_sections(plot_tree: dict, total_threshold: int = 200) -> str | None:
    def word_count(t: str) -> int:
        return len((t or "").split())

    # Counts as the number of words in the scraped plot of the game
    total_words = 0
    for v in plot_tree.values():
        if isinstance(v, dict):
            total_words += sum(word_count(x) for x in v.values())
        else:
            total_words += word_count(v)

    # If the plot isn't even 200 words long then the summary is returned as None
    if total_words <= total_threshold:
        return None

    # Summarizer is declared as the one from the first function of the code
    summarizer = get_summarizer()
    # This variable serves for adding # so that markdown recognizes headings used
    out_lines = []

    # Makes a summary for every mw-heading3
    for h3, content in plot_tree.items():
        out_lines.append(f"### {h3}")

        # Checks if the value in the dictionary is a simple text or another dictionary (case of having mw-heading4)
        if isinstance(content, dict):
            for h4, text in content.items():
                if not text.strip():
                    continue
                out_lines.append(f"#### {h4}")
                wc = word_count(text)

                # There are separate cases for different world counts so that the summary doesn't have a fixed maximum
                # size for both 200-word and 500-word plots
                if wc < 80:
                    summary = text.strip()
                elif wc < 200:
                    res = summarizer(text, max_length=120, min_length=50, do_sample=False)
                    summary = res[0]["summary_text"]
                elif wc < 500:
                    res = summarizer(text, max_length=160, min_length=80, do_sample=False)
                    summary = res[0]["summary_text"]
                # The model that I'm using has a maximum of 3500 tokens (which comes out to roughly 600 to 700 words).
                # If that limit is exceeded then the summarizer refuses to comply and breaks. To prevent that, in case
                # of such long plots the text is divided into chunks with the maximum length of those 3500 tokens and
                # all those chunks are summarized separately. It's not a perfect solution, but it's also made for a rare
                # case. Either way when all the chunks are summarized they are then being reconnected with each other
                else:
                    chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]
                    partials = []
                    for ch in chunks:
                        res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                        partials.append(res[0]["summary_text"])
                    summary = " ".join(partials)
                out_lines.append(summary)
                out_lines.append("")

        # In case where the value of the key it's using is NOT a dictionary with another mw-heading4's text but a plain
        # text
        else:
            text = content.strip()
            wc = word_count(text)
            if wc < 80:
                summary = text
            elif wc < 200:
                res = summarizer(text, max_length=120, min_length=50, do_sample=False)
                summary = res[0]["summary_text"]
            elif wc < 500:
                res = summarizer(text, max_length=160, min_length=80, do_sample=False)
                summary = res[0]["summary_text"]
            else:
                chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]
                partials = []
                for ch in chunks:
                    res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                    partials.append(res[0]["summary_text"])
                summary = " ".join(partials)
            out_lines.append(summary)
            out_lines.append("")

    return "\n".join(out_lines).strip()



# === 🔽 NOWA FUNKCJA DODANA NA KOŃCU PLIKU ===
# Działa podobnie jak summarize_plot_sections(), ale opiera się na gotowym markdownie z bazy (full_plot)
# Nie wymaga ponownego scrapowania Wikipedii. Zachowuje nagłówki i streszcza sekcje osobno.
def summarize_plot_from_markdown(full_plot_md: str, total_threshold: int = 200) -> str | None:
    """
    Streszcza fabułę na podstawie istniejącego markdownu z bazy (###, ####, ##).
    Zachowuje strukturę nagłówków i streszcza każdą sekcję osobno, z obsługą hierarchii.
    """

    def word_count(t: str) -> int:
        return len((t or "").split())

    if not full_plot_md or "No Plot Found" in full_plot_md:
        return None

    start_time = time.time()
    summarizer = get_summarizer()
    lines = full_plot_md.splitlines()

    sections = {}
    current_h3 = None
    current_h4 = None
    buffer = []

    # --- Parsowanie markdownu ---
    for line in lines:
        heading_match = re.match(r'^(#+)\s+(.*)', line.strip())
        if heading_match:
            hashes, title = heading_match.groups()
            level = len(hashes)

            # Zapisz poprzedni bufor zanim przejdziesz dalej
            if buffer:
                if current_h3:
                    if current_h4:
                        sections[current_h3][current_h4] = "\n".join(buffer).strip()
                    else:
                        # Jeśli h4 się skończyło, zapisujemy tekst bezpośrednio pod h3
                        if isinstance(sections[current_h3], str):
                            sections[current_h3] += "\n" + "\n".join(buffer).strip()
                        else:
                            sections[current_h3]["__main__"] = "\n".join(buffer).strip()
                buffer = []

            # Rozpoznaj poziom nagłówka
            if level == 3:  # ### — poziom główny
                current_h3 = title.strip()
                current_h4 = None
                sections[current_h3] = {}
            elif level == 4 and current_h3:  # #### — podrzędny do aktualnego ###
                current_h4 = title.strip()
                sections[current_h3][current_h4] = ""
            else:
                # Inne poziomy (np. ##) ignorujemy lub traktujemy jak główny
                current_h3 = title.strip()
                current_h4 = None
                sections[current_h3] = {}

        else:
            buffer.append(line.strip())

    # Zapisz końcowy bufor
    if buffer and current_h3:
        if current_h4:
            sections[current_h3][current_h4] = "\n".join(buffer).strip()
        else:
            sections[current_h3]["__main__"] = "\n".join(buffer).strip()

    if not sections:
        return None

    # --- Oblicz łączną liczbę słów ---
    total_words = 0
    for v in sections.values():
        if isinstance(v, dict):
            total_words += sum(word_count(x) for x in v.values())
        else:
            total_words += word_count(v)

    if total_words <= total_threshold:
        return None

    out_lines = []
    print(f"[SUMMARY] Rozpoczynam streszczanie fabuły ({len(sections)} sekcji, ~{total_words} słów).")

    # --- Generowanie streszczeń ---
    for h3, content in sections.items():
        out_lines.append(f"### {h3}")

        if isinstance(content, dict):
            for h4, text in content.items():
                if not text.strip():
                    continue
                out_lines.append(f"#### {h4}" if h4 != "__main__" else "")
                wc = word_count(text)
                print(f"[SUMMARY] Sekcja: {h3} -> {h4} ({wc} słów)" if h4 != "__main__" else f"[SUMMARY] Sekcja: {h3} ({wc} słów)")

                if wc < 80:
                    summary = text.strip()
                elif wc < 200:
                    res = summarizer(text, max_length=120, min_length=50, do_sample=False)
                    summary = res[0]["summary_text"]
                elif wc < 500:
                    res = summarizer(text, max_length=160, min_length=80, do_sample=False)
                    summary = res[0]["summary_text"]
                else:
                    chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
                    partials = []
                    for i, ch in enumerate(chunks, 1):
                        print(f"[SUMMARY]  → część {i}/{len(chunks)} ({len(ch)} znaków)")
                        res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                        partials.append(res[0]["summary_text"])
                    summary = " ".join(partials)

                out_lines.append(summary.strip())
                out_lines.append("")

        else:
            text = content.strip()
            wc = word_count(text)
            if wc < 80:
                summary = text
            elif wc < 200:
                res = summarizer(text, max_length=120, min_length=50, do_sample=False)
                summary = res[0]["summary_text"]
            elif wc < 500:
                res = summarizer(text, max_length=160, min_length=80, do_sample=False)
                summary = res[0]["summary_text"]
            else:
                chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
                partials = []
                for i, ch in enumerate(chunks, 1):
                    print(f"[SUMMARY]  → część {i}/{len(chunks)} ({len(ch)} znaków)")
                    res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                    partials.append(res[0]["summary_text"])
                summary = " ".join(partials)
            out_lines.append(summary.strip())
            out_lines.append("")

    elapsed = time.time() - start_time
    print(f"[SUMMARY] Generowanie streszczenia zakończone w {elapsed:.1f}s.")
    return "\n".join(out_lines).strip()


# When the user searches a game on the website, the scraper is activated, and it scrapes whatever MobyGames shows as a
# result of searching the same game. This is the fist instance of using PlayWright in this code. Async function needed
# for Playwright's asynchronous nature of "await" which, as the name implies, waits for the attributes to be scrapped
async def search_mobygames(game_name: str):
    # Search link on MobyGames is encoded in a way that turns non-alphabetic symbols as something else like a simple
    # space is replaced with "%20" and ":" sign is replaced with "%3A"
    encoded_name = urllib.parse.quote(game_name)
    search_url = f"https://www.mobygames.com/search/?q={encoded_name}"

    # 🧹 --- Wyczyść stare miniatury na samym początku ---
    try:
        media_root = "media/results"
        os.makedirs(media_root, exist_ok=True)
        for old in os.listdir(media_root):
            if old.startswith("result_") and old.endswith(".png"):
                os.remove(os.path.join(media_root, old))
        print("[CLEANUP] Folder 'media/results' wyczyszczony przed nowym wyszukiwaniem.")
    except Exception as e:
        print(f"[!] Błąd przy czyszczeniu folderu results: {e}")

    async with async_playwright() as p:
        # Playwright opens chromium browser to scrap info but # doesn't show browser window (because of headless=True)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # User agent needed, so it doesn't consider Playwright as a bot.
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/140.0.0.0 Safari/537.36"
        })

        # Go to the website
        await page.goto(search_url, timeout=60000)
        await page.wait_for_load_state("networkidle")

        # Czasem miniatury ładują się chwilę po wczytaniu treści strony,
        # więc czekamy dodatkową sekundę, żeby były pewne źródła obrazków
        await page.wait_for_timeout(1500)

        # Case where there are no results
        try:
            html = await page.content()
            if "No results found for that query" in html:
                print("[INFO] No results found on MobyGames for this query.")
                await browser.close()
                return []
        except Exception as e:
            print(f"[!] Error while checking for 'No results found': {e}")

        # When searching a game on MobyGames there is a field of text at the top of the page which informs you that this
        # page either excludes or includes games marked as Adult.
        adult_toggle = page.locator("p:has-text('This search excludes games marked as Adult')")
        if await adult_toggle.count() > 0:
            click_here = adult_toggle.locator("a:has-text('Click here')")
            if await click_here.count() > 0:
                await click_here.first.click()
                await page.wait_for_load_state("networkidle")

        # Wait for everything to load
        await page.wait_for_selector("table.table.mb tbody tr", timeout=20000)
        rows = await page.query_selector_all("table.table.mb tbody tr")

        # 📂 --- Folder już wyczyszczony powyżej, więc tutaj tylko definicja ---
        media_root = "media/results"
        results = []
        index = 0  # licznik do numerowania plików result_1.png itd.

        for row in rows[:10]:
            td = await row.query_selector("td:nth-child(2)")
            if not td:
                continue
            text = (await td.inner_text()).strip()
            if not (text.startswith("GAME:") or text.startswith("ADULT GAME:")):
                continue

            clean_text = re.sub(r'^(ADULT\s+)?GAME:\s*', '', text, flags=re.IGNORECASE).strip()
            lines = [ln.strip() for ln in clean_text.splitlines() if ln.strip()]
            filtered = [ln for ln in lines if "mature content" not in ln.lower() and ln != "View Content"]
            clean_text = "\n".join(filtered)

            # Pobiera link do gry
            link_el = await td.query_selector("b a") or await td.query_selector("a")
            href = await link_el.get_attribute("href") if link_el else None
            full_url = f"https://www.mobygames.com{href}" if href and not href.startswith("http") else href

            # 📸 --- Zapis okładki wyniku ---
            try:
                img_td = await row.query_selector("td:nth-child(1) img")
                index += 1
                if img_td:
                    src = await img_td.get_attribute("src")
                    if src and src.startswith("http"):
                        resp = requests.get(src, timeout=10)
                        if resp.status_code == 200:
                            out_path = os.path.join(media_root, f"result_{index}.png")
                            with open(out_path, "wb") as f:
                                f.write(resp.content)
                        else:
                            default_icon = os.path.join(media_root, "default_icon.png")
                            out_path = os.path.join(media_root, f"result_{index}.png")
                            if os.path.exists(default_icon):
                                copyfile(default_icon, out_path)
                    else:
                        default_icon = os.path.join(media_root, "default_icon.png")
                        out_path = os.path.join(media_root, f"result_{index}.png")
                        if os.path.exists(default_icon):
                            copyfile(default_icon, out_path)
                else:
                    default_icon = os.path.join(media_root, "default_icon.png")
                    out_path = os.path.join(media_root, f"result_{index}.png")
                    if os.path.exists(default_icon):
                        copyfile(default_icon, out_path)
            except Exception as e:
                print(f"[!] Błąd przy zapisie miniatury result_{index}: {e}")

            results.append({"url": full_url, "description": clean_text})

            if len(results) >= 5:
                break

        if len(results) == 0:
            print("[INFO] No valid game results found in search results.")
            await browser.close()
            return []
        elif len(results) < 5:
            print(f"[INFO] Only {len(results)} valid game results found (less than expected).")

        await browser.close()
        return results


# This is a function for scraping the game's attributes such as genre or when it was released as well as its plot from
# wikipedia. But to fully understand how it works one must dwell deeper as it is complicated. First of all not all games
# presented in the game search are strictly games but also game editions such as compilations of a game and its dlc or a
# collector's edition version. As for how the first one is handled, for every game page to be scraped it firsts looks
# for the tag "This Compilation Includes" which indicates that the game is not a single game but rather a compilation of
# different games or game and its dlc as previously mentioned. If that is the case then what is scraped instead are the
# games it's compiled of and then the app shows you options to choose to show the plot of one of those games. If that is
# not the case then it does the regular process of scraping the game which I explain further into the code. As for the
# second option of the game being a game's edition rather than the original, this time it searches for "Base Game" tag,
# which it saves in case there is no wikipedia page on that version of the game. If there, in fact, isn't a page on
# wikipedia for that version then what happens is that it goes to the base game and starts the entire scraping process
# again for that version. Those are not the only cases though, because a game might not have neither "Base Game" nor
# "This Compilation Includes" but also no wikipedia page. For that case what is scraped as plot is the description of
# the game on MobyGames where the scraper got its attributes from. More about how it all works is in the code bellow
async def scrape_game_info(url: str, media_root: str, save_image: bool = True, is_base: bool = False):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/140.0.0.0 Safari/537.36"
        })

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle")

        # Scrape the title as the first thing it does
        title = None
        if await page.query_selector("h1.mb-0"):
            title = (await page.inner_text("h1.mb-0")).strip()

        # Checks for that "This Compilation Includes" tag
        compilation_games = []
        try:
            await page.wait_for_timeout(1000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            for div in soup.find_all("div", class_="border"):
                b = div.find("b")
                if b and "This Compilation Includes" in b.get_text(strip=True):
                    for li in div.select("ul li"):
                        links = li.find_all("a", href=True)
                        if not links:
                            continue
                        href = links[-1]["href"]
                        if href.startswith("/"):
                            href = f"https://www.mobygames.com{href}"
                        title_ = links[-1].get_text(strip=True)
                        year_tag = li.find("small", class_="text-muted")
                        year = year_tag.get_text(strip=True) if year_tag else None

                        compilation_games.append({
                            "title": title_,
                            "url": href,
                            "year": year
                        })
                    break
        except Exception as e:
            print(f"[!] Compilation check failed: {e}")

        # If it does find this tag then it scrapes the links to the games this compilation includes
        if compilation_games:
            try:
                page_title = (await page.inner_text("h1.mb-0")).strip()
            except:
                page_title = "Unknown Compilation"

            await browser.close()
            print(f"[DEBUG] Compilation detected: {page_title} ({len(compilation_games)} games)")
            for g in compilation_games:
                print(f"  - {g['title']} ({g['year']}) -> {g['url']}")
            return {
                "is_compilation": True,
                "title": page_title,
                "included_games": compilation_games
            }

        # Just in case the scraper looks for the words bellow to decide whether the base game does indeed take the user
        # to the base version of the game (probably not needed but made just in case in the initial version)
        EDITION_KEYWORDS = [
            "edition", "remaster", "definitive", "goty", "game of the year",
            "complete", "ultimate", "director's cut", "hd", "collection"
        ]

        base_game_url = None
        if not is_base:
            try:
                await page.wait_for_timeout(1000)
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                for div in soup.find_all("div", class_="border"):
                    b = div.find("b")
                    if b and "Base Game" in b.get_text(strip=True):
                        link = div.find("ul")
                        if link and link.find("a", href=True):
                            hrefs = [a["href"] for a in link.find_all("a", href=True) if "game" in a["href"]]
                            if hrefs:
                                href = hrefs[-1]
                                if href.startswith("/"):
                                    href = f"https://www.mobygames.com{href}"
                                base_game_url = href
                                break
            except Exception as e:
                print(f"[!] Base Game check failed: {e}")

        # Only the original game editions return the website to the base game
        if base_game_url and not is_base:
            if title and any(k in title.lower() for k in EDITION_KEYWORDS):
                print(f"→ Edition detected in title '{title}' → following base game: {base_game_url}")
                await browser.close()
                return await scrape_game_info(base_game_url, media_root, save_image, is_base=True)
            else:
                print(f"[INFO] 'Base Game' present, but '{title}' is not an edition → staying on this page.")

        # The regular case of scraping the game. The variables bellow are the attributes Playwright tries to scrape from
        # MobyGames page for the chosen game
        released = None
        studio = []
        moby_score = None
        genre = []
        cover_image_url = None

        # Both released and studio (visible on MobyGames as "Developers") are in the same div, therefore they are
        # scraped together here
        if await page.query_selector("div.info-release"):
            # Names of the values (such as "Released")
            dt_tags = await page.query_selector_all("div.info-release dl.metadata dt")
            # The values themselves (Such as "January 1st 2025")
            dd_tags = await page.query_selector_all("div.info-release dl.metadata dd")
            for dt, dd in zip(dt_tags, dd_tags):
                label = (await dt.inner_text()).strip()
                # if Playwright finds the searched values then it will scrape its information
                if label == "Released":
                    released = (await dd.inner_text()).strip()
                elif label == "Developers":
                    # Made into a list in case of multiple studios working on the game
                    dev_links = await dd.query_selector_all("a")
                    studio = [(await link.inner_text()).strip() for link in dev_links]

        # Get info about game's genre
        if await page.query_selector("div.info-genres"):
            dt_tags = await page.query_selector_all("div.info-genres dl.metadata dt")
            dd_tags = await page.query_selector_all("div.info-genres dl.metadata dd")
            for dt, dd in zip(dt_tags, dd_tags):
                label = (await dt.inner_text()).strip()
                if label == "Genre":
                    genre_links = await dd.query_selector_all("a")
                    genre = [(await link.inner_text()).strip() for link in genre_links]
                    break

        # Get info about game's Mobyscore, a score given by MobyGames official reviewers (it has a different structure
        # from the rest of the searched values)
        if await page.query_selector("div.info-score div.mobyscore"):
            moby_score = (await page.inner_text("div.info-score div.mobyscore")).strip()

        if await page.query_selector("div.info-box img.img-box"):
            cover_image_url = await page.get_attribute("div.info-box img.img-box", "src")

        # Get the game's cover image url and download it into the media/game_icons folder in a jpg format. Additionally
        # thanks to the image_name function discussed earlier the image's name is made easier to search it
        local_image_relpath = None
        if save_image and cover_image_url and title:
            try:
                resp = requests.get(cover_image_url, timeout=10)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                filename = f"{image_name(title)}_icon.jpg"
                out_dir = os.path.join(media_root, "game_icons")
                os.makedirs(out_dir, exist_ok=True)
                path = os.path.join(out_dir, filename)
                img.save(path, "JPEG", quality=90)
                local_image_relpath = f"game_icons/{filename}"
                print(f"[DEBUG] Saved icon OK: {path}")
            except Exception as e:
                print(f"[ERROR] Could not save image: {e}")

        # The entire process of scraping plot from Wikipedia
        full_plot_md = None
        summary_md = None
        structured_plot = {}
        wiki_url = None
        if title:
            # Wikipedia urls are usually simple enough to use this simple solution:
            wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            print(f"[DEBUG] Wikipedia lookup: {wiki_url}")
            try:
                await page.goto(wiki_url, timeout=30000)
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                # Removes the "[ edit ]", "See also" and references when scraping Wikipedia text
                for e in soup.select("span.mw-editsection, div.hatnote, sup.reference"):
                    e.decompose()
                # Uses extract_plot_structure described earlier to scrape the plot
                structured_plot = extract_plot_structure(soup)
                if structured_plot:
                    # Made solely for markdown library which differentiates different headings
                    full_plot_md = build_markdown_with_headings(structured_plot)
                    #summary_md = summarize_plot_sections(structured_plot)
            except Exception as e:
                print(f"[!] Wikipedia scrape failed: {e}")

        # There has to be a separate function that scrapes the game's plot when Wikipedia page is non-existent. The code
        # bellow deals with that issue by scraping the description of MobyGames page of that game in a similar way to
        # the Wikipedia scraper
        if not full_plot_md:
            try:
                if page.url != url:
                    await page.goto(url, timeout=30000)
                for sel in ["[data-target='#description-text']", "a[href='#description-text']"]:
                    if await page.query_selector(sel):
                        await page.click(sel)
                        await page.wait_for_timeout(500)
                        break

                html_desc = None
                for selector in ["#description-text", "#description-text .text-content",
                                 "div#description", "div.description-content"]:
                    if await page.query_selector(selector):
                        html_desc = await page.inner_html(selector)
                        if html_desc:
                            break

                if html_desc:
                    soup_desc = BeautifulSoup(html_desc, "html.parser")
                    paragraphs = [p.get_text(" ", strip=True) for p in soup_desc.find_all("p")]
                    if not paragraphs:
                        raw_text = soup_desc.get_text(" ", strip=True)
                        paragraphs = [raw_text] if raw_text else []
                    moby_description = "\n".join(paragraphs).strip()
                    if moby_description:
                        # --- Dodaj nagłówek markdown "## Description" ---
                        full_plot_md = f"## Description\n\n{moby_description}"

                        # --- Generuj krótkie podsumowanie ---
                        words = len(moby_description.split())
                        if words > 200:
                            summarizer = get_summarizer()
                            if words < 500:
                                res = summarizer(moby_description, max_length=160, min_length=80, do_sample=False)
                                summary_text = res[0]["summary_text"]
                            else:
                                chunks = [moby_description[i:i + 3500] for i in range(0, len(moby_description), 3500)]
                                partials = []
                                for ch in chunks:
                                    res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                                    partials.append(res[0]["summary_text"])
                                summary_text = " ".join(partials)
                        else:
                            summary_text = moby_description

                        # --- Summary też w markdownie z nagłówkiem ---
                        summary_md = (
                            f"## Description\n\n{summary_text}\n\n"
                            "*This summary is based on the game's description from MobyGames. "
                            "For a detailed storyline, try asking the chatbot below.*"
                        )

                        # --- Dodaj komunikat, że to nie fabuła ---
                        full_plot_md += (
                            "\n\n*Note: This section is based on the game's description from MobyGames "
                            "and may not represent the actual storyline. You can use the chatbot to learn more about the plot.*"
                        )


            except Exception as e:
                print(f"[!] Fallback Moby description error: {e}")

        # When the game has absolutely no plot available anywhere then the app returns this as a final measure instead
        # of just having None in the database
        if not full_plot_md:
            full_plot_md = (
                "## No Plot Found\n\n"
                "No plot was found for this game. "
                "It might be a gameplay-focused title without a defined storyline.\n\n"
                "*Tip: You can ask the chatbot to learn more about the game's background or lore.*"
            )

        if not summary_md:
            summary_md = (
                "## No Summary Available\n\n"
                "No summary was found for this game. "
                "You can use the chatbot to learn more about its background, lore, or general storyline."
            )

        await browser.close()

        # What this entire file returns at the end of the day
        await browser.close()

        # What this entire file returns at the end of the day
        return {
            "title": title or "Unknown",
            "release_date": released,
            "studio": ", ".join(studio) if studio else None,
            "genre": ", ".join(genre) if genre else None,
            "score": moby_score,
            "cover_image": local_image_relpath,
            "full_plot": full_plot_md,
            "summary": summary_md,
            "is_compilation": False,
            "mobygames_url": url,  # <<< nowa linia
            "wikipedia_url": wiki_url  # <<< nowa linia
        }




# === 🔁 SCRAPE_GAME_INFO_ADMIN ===
# Wersja scrape_game_info() używana w panelu administratora.
# Różni się tym, że automatycznie generuje streszczenie (summary_md)
# przy użyciu summarize_plot_sections() oraz nadpisuje stare dane gry.
async def scrape_game_info_admin(url: str, media_root: str, save_image: bool = True):

    print(f"[ADMIN RELOAD] Rozpoczynam pełne przeładowanie gry z URL: {url}")
    start_time = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/140.0.0.0 Safari/537.36"
        })

        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle")

        # --- SCRAPE PODSTAWOWYCH INFORMACJI ---
        title = None
        if await page.query_selector("h1.mb-0"):
            title = (await page.inner_text("h1.mb-0")).strip()

        # --- WIKI SCRAPE ---
        full_plot_md = None
        summary_md = None
        wiki_url = None

        if title:
            wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            print(f"[ADMIN RELOAD] Wikipedia lookup: {wiki_url}")

            try:
                await page.goto(wiki_url, timeout=30000)
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                for e in soup.select("span.mw-editsection, div.hatnote, sup.reference"):
                    e.decompose()

                structured_plot = extract_plot_structure(soup)
                if structured_plot:
                    full_plot_md = build_markdown_with_headings(structured_plot)
                    summary_md = summarize_plot_sections(structured_plot)
                    print("[ADMIN RELOAD] Streszczenie wygenerowane pomyślnie.")
            except Exception as e:
                print(f"[ADMIN RELOAD] Wikipedia scrape failed: {e}")

        # --- WERYFIKACJA ---
        if not full_plot_md:
            full_plot_md = "## No Plot Found\n\nNo plot could be scraped for this game."
        if not summary_md:
            summary_md = "## No Summary Available\n\nNo summary could be generated."

        await browser.close()
        elapsed = time.time() - start_time
        print(f"[ADMIN RELOAD] Zakończono w {elapsed:.1f}s")

        return {
            "title": title or "Unknown",
            "full_plot": full_plot_md,
            "summary": summary_md,
            "wikipedia_url": wiki_url,
        }

