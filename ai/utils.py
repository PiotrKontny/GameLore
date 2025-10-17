import asyncio
import os
import re
import urllib.parse
from io import BytesIO
from decimal import Decimal

import requests
from bs4 import BeautifulSoup
from PIL import Image
from playwright.async_api import async_playwright

from transformers import pipeline

# ——— Lazy-inicjalizacja summarizera
_SUMMARIZER = None
def get_summarizer():
    global _SUMMARIZER
    if _SUMMARIZER is None:
        _SUMMARIZER = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    return _SUMMARIZER


# ——— Pomocnicze
def snakeify_title(title: str) -> str:
    s = title.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s


def parse_moby_score(raw: str):
    if not raw:
        return None
    txt = raw.strip().replace('%', '')
    try:
        val = float(txt)
        if val > 10:
            val = val / 10.0
        return Decimal(str(round(val, 1)))
    except:
        return None


# ——— Parsowanie fabuły z Wikipedii (z hierarchią)
def extract_plot_structure(soup: BeautifulSoup) -> dict:
    valid_sections = ["Plot", "Synopsis", "Premise", "Story"]
    plot_heading = None
    plot_h2_title = None

    for div in soup.find_all("div", class_="mw-heading mw-heading2"):
        h2 = div.find("h2")
        if h2 and h2.get("id") in valid_sections:
            plot_heading = div
            plot_h2_title = h2.get_text(strip=True)
            break

    if not plot_heading:
        return {}

    plot_data = {}
    current_h3 = None
    current_h4 = None

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


def build_markdown_with_headings(plot_tree: dict) -> str:
    """Buduje markdown z zachowaniem nagłówków."""
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


# ——— Summarizer per nagłówek
def summarize_plot_sections(plot_tree: dict, total_threshold: int = 200) -> str | None:
    """
    Streszcza każdą sekcję osobno, zachowując strukturę nagłówków.
    Wynik zwraca w formacie markdown (gotowym do renderowania na stronie).
    """
    def word_count(t: str) -> int:
        return len((t or "").split())

    # zlicz łączną długość
    total_words = 0
    for v in plot_tree.values():
        if isinstance(v, dict):
            total_words += sum(word_count(x) for x in v.values())
        else:
            total_words += word_count(v)

    if total_words <= total_threshold:
        # fabuła krótka, nie streszczamy
        return None

    summarizer = get_summarizer()
    out_lines = []

    for h3, content in plot_tree.items():
        out_lines.append(f"### {h3}")

        if isinstance(content, dict):
            for h4, text in content.items():
                if not text.strip():
                    continue
                out_lines.append(f"#### {h4}")
                wc = word_count(text)
                if wc < 80:
                    summary = text.strip()
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


# ——— Główne scrapowanie
async def search_mobygames(game_name: str):
    encoded_name = urllib.parse.quote(game_name)
    search_url = f"https://www.mobygames.com/search/?q={encoded_name}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/140.0.0.0 Safari/537.36"
        })
        await page.goto(search_url, timeout=60000)
        await page.wait_for_load_state("networkidle")
        # --- Sprawdź, czy to kompilacja ("This Compilation Includes") ---
        compilation_games = []
        try:
            # Poczekaj chwilę aż Playwright załaduje cały DOM (bo MobyGames ładuje dynamicznie)
            await page.wait_for_timeout(1000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Szukamy konkretnego <div> z <b>This Compilation Includes</b>
            for div in soup.find_all("div", class_="border"):
                b = div.find("b")
                if b and "This Compilation Includes" in b.get_text(strip=True):
                    # W tym bloku mamy listę <li> z grami
                    for li in div.select("ul li"):
                        all_links = li.find_all("a", href=True)
                        if not all_links:
                            continue
                        # pierwszy <a> to miniaturka, drugi to tytuł gry
                        href = all_links[-1]["href"]
                        if href.startswith("/"):
                            href = f"https://www.mobygames.com{href}"
                        title = all_links[-1].get_text(strip=True)
                        year_tag = li.find("small", class_="text-muted")
                        year = year_tag.get_text(strip=True) if year_tag else None

                        compilation_games.append({
                            "title": title,
                            "url": href,
                            "year": year
                        })
                    break
        except Exception as e:
            print(f"[!] Compilation check failed: {e}")

        if compilation_games:
            page_title = None
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

        # pokaż adult content jeśli trzeba
        adult_toggle = page.locator("p:has-text('This search excludes games marked as Adult')")
        if await adult_toggle.count() > 0:
            click_here = adult_toggle.locator("a:has-text('Click here')")
            if await click_here.count() > 0:
                await click_here.first.click()
                await page.wait_for_load_state("networkidle")

        await page.wait_for_selector("table.table.mb tbody tr", timeout=20000)
        rows = await page.query_selector_all("table.table.mb tbody tr")

        results = []
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

            link_el = await td.query_selector("b a") or await td.query_selector("a")
            href = await link_el.get_attribute("href") if link_el else None
            full_url = f"https://www.mobygames.com{href}" if href and not href.startswith("http") else href

            results.append({"url": full_url, "description": clean_text})
            if len(results) >= 5:
                break

        await browser.close()
        return results

async def scrape_game_info(url: str, media_root: str, save_image: bool = True, is_base: bool = False):
    """
    Scrapuje informacje o grze z MobyGames i (jeśli to możliwe) fabułę z Wikipedii.
    Obsługuje przypadki:
    - Compilation / Bundle (This Compilation Includes)
    - Base Game / Edition (z ograniczonym przeskakiwaniem)
    """

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

        # ————————————————————————————————————————————————————————————————
        # 1) Pobierz tytuł jak najwcześniej (ważne dla sprawdzenia Base Game)
        title = None
        if await page.query_selector("h1.mb-0"):
            title = (await page.inner_text("h1.mb-0")).strip()

        # ————————————————————————————————————————————————————————————————
        # 2) Sprawdź, czy to kompilacja ("This Compilation Includes")
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

        # ————————————————————————————————————————————————————————————————
        # 3) Sprawdź "Base Game" (np. dla edycji, remasterów, GOTY itd.)
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

        # ——— tylko edycje / wersje wracają do podstawki
        if base_game_url and not is_base:
            if title and any(k in title.lower() for k in EDITION_KEYWORDS):
                print(f"→ Edition detected in title '{title}' → following base game: {base_game_url}")
                await browser.close()
                return await scrape_game_info(base_game_url, media_root, save_image, is_base=True)
            else:
                print(f"[INFO] 'Base Game' present, but '{title}' is not an edition → staying on this page.")

        # ————————————————————————————————————————————————————————————————
        # 4) Scrapowanie danych gry (normalny przypadek)
        released = None
        studio = []
        moby_score = None
        genre = []
        cover_image_url = None

        if await page.query_selector("div.info-release"):
            dt_tags = await page.query_selector_all("div.info-release dl.metadata dt")
            dd_tags = await page.query_selector_all("div.info-release dl.metadata dd")
            for dt, dd in zip(dt_tags, dd_tags):
                label = (await dt.inner_text()).strip()
                if label == "Released":
                    released = (await dd.inner_text()).strip()
                elif label == "Developers":
                    dev_links = await dd.query_selector_all("a")
                    studio = [(await link.inner_text()).strip() for link in dev_links]

        if await page.query_selector("div.info-genres"):
            dt_tags = await page.query_selector_all("div.info-genres dl.metadata dt")
            dd_tags = await page.query_selector_all("div.info-genres dl.metadata dd")
            for dt, dd in zip(dt_tags, dd_tags):
                label = (await dt.inner_text()).strip()
                if label == "Genre":
                    genre_links = await dd.query_selector_all("a")
                    genre = [(await link.inner_text()).strip() for link in genre_links]
                    break

        if await page.query_selector("div.info-score div.mobyscore"):
            moby_score = (await page.inner_text("div.info-score div.mobyscore")).strip()

        if await page.query_selector("div.info-box img.img-box"):
            cover_image_url = await page.get_attribute("div.info-box img.img-box", "src")

        # ————————————————————————————————————————————————————————————————
        # 5) Zapisanie okładki lokalnie
        local_image_relpath = None
        if save_image and cover_image_url and title:
            try:
                resp = requests.get(cover_image_url, timeout=10)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                filename = f"{snakeify_title(title)}_icon.jpg"
                out_dir = os.path.join(media_root, "game_icons")
                os.makedirs(out_dir, exist_ok=True)
                path = os.path.join(out_dir, filename)
                img.save(path, "JPEG", quality=90)
                local_image_relpath = f"game_icons/{filename}"
                print(f"[DEBUG] Saved icon OK: {path}")
            except Exception as e:
                print(f"[ERROR] Could not save image: {e}")

        # ————————————————————————————————————————————————————————————————
        # 6) Wikipedia — fabuła i streszczenie
        full_plot_md = None
        summary_md = None
        structured_plot = {}

        wiki_url = None
        if title:
            wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            print(f"[DEBUG] Wikipedia lookup: {wiki_url}")  # <<<<<< tu nowy debug
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
            except Exception as e:
                print(f"[!] Wikipedia scrape failed: {e}")

        # --- Fallback: opis z MobyGames ---
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
                        full_plot_md = moby_description
                        words = len(moby_description.split())
                        if words > 200:
                            summarizer = get_summarizer()
                            if words < 500:
                                res = summarizer(moby_description, max_length=160, min_length=80, do_sample=False)
                                summary_md = res[0]["summary_text"]
                            else:
                                chunks = [moby_description[i:i + 3500] for i in range(0, len(moby_description), 3500)]
                                partials = []
                                for ch in chunks:
                                    res = summarizer(ch, max_length=180, min_length=80, do_sample=False)
                                    partials.append(res[0]["summary_text"])
                                summary_md = " ".join(partials)
                        else:
                            summary_md = moby_description
            except Exception as e:
                print(f"[!] Fallback Moby description error: {e}")

        # --- Ostateczny fallback (żeby NIGDY nie zwrócić None) ---
        if not full_plot_md:
            full_plot_md = "No plot available"
        if not summary_md:
            summary_md = "No summary available"

        await browser.close()

        return {
            "title": title or "Unknown",
            "release_date": released,
            "studio": ", ".join(studio) if studio else None,
            "genre": ", ".join(genre) if genre else None,
            "score_raw": moby_score,
            "score": parse_moby_score(moby_score),
            "cover_image_url": cover_image_url,
            "cover_image_relpath": local_image_relpath,
            "full_plot": full_plot_md,
            "summary": summary_md,
            "is_compilation": False  # <<< nowy bezpiecznik
        }
