import asyncio
import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

BASE_URL = "https://www.rottentomatoes.com"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "movies.json"
START_URL = f"{BASE_URL}/browse/movies_in_theaters/sort:newest"
MAX_PAGE = 5
MAX_CONCURRENCY = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def parse_year(text: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return int(match.group(0)) if match else None


def parse_runtime(text: str) -> int | None:
    hours = re.search(r"(\d+)\s*h", text, re.I)
    minutes = re.search(r"(\d+)\s*m", text, re.I)
    if not hours and not minutes:
        return None
    return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)


def parse_title(soup: BeautifulSoup) -> str | None:
    heading = soup.find("h1", id="media-hero-label")
    if heading and heading.get_text(strip=True):
        return heading.get_text(" ", strip=True)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].removesuffix(" | Rotten Tomatoes").strip() or None
    return None


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logging.warning("Could not fetch %s: %s", url, exc)
        return None


async def parse_page_links(session: aiohttp.ClientSession, page: int) -> list[str]:
    url = f"{START_URL}?page={page}"
    html = await fetch_html(session, url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", class_="discovery-tiles__wrap")
    if not container:
        logging.warning("Movie container not found on %s", url)
        return []

    links = []
    for tile in container.find_all("div", class_="flex-container"):
        link = tile.find("a", class_="js-tile-link", href=True)
        if link:
            links.append(urljoin(BASE_URL, link["href"]))
    return list(dict.fromkeys(links))


async def get_movie_links(session: aiohttp.ClientSession) -> list[str]:
    pages = await asyncio.gather(*(parse_page_links(session, page) for page in range(1, MAX_PAGE + 1)))
    return list(dict.fromkeys(link for page in pages for link in page))


async def parse_actor(session: aiohttp.ClientSession, actor_url: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        html = await fetch_html(session, actor_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1", class_="celebrity-bio__h1")
    if not heading:
        return None

    name = heading.get_text(strip=True)
    birth_year = None
    info = soup.find("div", class_="celebrity-bio__info")
    if info:
        for item in info.find_all("p", class_="celebrity-bio__item"):
            if "Birthday" in item.get_text(" ", strip=True):
                birth_year = parse_year(item.get_text(" ", strip=True))
                break
    return {"name": name, "birth_year": birth_year, "url": actor_url}


async def parse_cast(session, movie_url: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        html = await fetch_html(session, f"{movie_url}/cast-and-crew")
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("section", class_="cast-and-crew")
    if not section:
        return []

    cast = []
    seen = set()
    for card in section.find_all("cast-and-crew-card"):
        # Cast members have "cast" in data-role ("all,cast"); crew members have "all,crew".
        if "cast" not in card.get("data-role", "").split(","):
            continue
        name_tag = card.find("rt-text", slot="title")
        name = name_tag.get_text(" ", strip=True) if name_tag else None
        media_url = card.get("media-url")
        # People without their own page get "/celebrity/undefined" instead of a real link.
        url = None
        if media_url and not media_url.rstrip("/").endswith("/undefined"):
            url = urljoin(BASE_URL, media_url)
        key = url or name
        if not name or key in seen:
            continue
        seen.add(key)
        cast.append((name, url))

    async def load(name: str, url: str | None) -> dict:
        actor = await parse_actor(session, url, semaphore) if url else None
        # Fall back to the name from the card if the actor has no page or it failed to load.
        return actor or {"name": name, "birth_year": None, "url": url}

    return await asyncio.gather(*(load(name, url) for name, url in cast))


async def parse_movie(session, movie_url: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        html = await fetch_html(session, movie_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    title = parse_title(soup)
    main_wrap = soup.find("div", id="main-wrap")
    if not title or not main_wrap:
        logging.warning("Title or main content not found on %s", movie_url)
        return None

    poster = main_wrap.find("rt-img", slot="poster-image")
    media_info = main_wrap.find("section", class_="media-info")

    result = {
        "url": movie_url,
        "title": title,
        "img_link": poster.get("src") if poster else None,
        "description": None,
        "duration": None,
        "genre": None,
        "year": None,
        "actors": [],
    }

    if media_info:
        synopsis = media_info.find("rt-text", attrs={"data-qa": "synopsis-value"})
        result["description"] = synopsis.get_text(" ", strip=True) if synopsis else None

        release_years = []
        dl = media_info.find("dl")
        if dl:
            for item in dl.find_all("div", class_="category-wrap"):
                label = item.find("dt", class_="key")
                value = item.find("dd", attrs={"data-qa": "item-value-group"})
                if not label or not value:
                    continue
                label_text = label.get_text(" ", strip=True)
                value_text = value.get_text(" ", strip=True)
                if label_text.startswith("Release Date"):
                    year = parse_year(value_text)
                    if year:
                        release_years.append(year)
                elif label_text.startswith("Runtime"):
                    result["duration"] = parse_runtime(value_text)
                elif label_text.startswith("Genre"):
                    genre_tag = value.find("rt-link", attrs={"data-qa": "item-value"})
                    result["genre"] = genre_tag.get_text(strip=True) if genre_tag else None
        result["year"] = min(release_years) if release_years else None

    result["actors"] = await parse_cast(session, movie_url, semaphore)
    return result


def save(result: dict) -> None:
    tmp_path = OUTPUT_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(OUTPUT_PATH)


async def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StudentMovieCollector/1.0)"}
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        movie_links = await get_movie_links(session)
        logging.info("Found %d movie links", len(movie_links))
        result = {}
        tasks = [parse_movie(session, url, semaphore) for url in movie_links]
        for task in asyncio.as_completed(tasks):
            movie = await task
            if not movie:
                continue
            result[f"movie{len(result) + 1}"] = movie
            save(result)  # save after every movie so a crash does not lose collected data

    logging.info("Saved %d movies to %s", len(result), OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())