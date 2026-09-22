# Online Cinema

A Django catalogue of movies currently in theaters. An async scraper collects movies, genres and cast from Rotten Tomatoes, a management command loads them into SQLite, and the site lets you browse, search and filter the catalogue.

## Features

- Movie catalogue with title search, genre filter and pagination
- Movie pages with description, runtime and cast
- Actor pages listing every movie of that actor in the catalogue
- Idempotent import: re-running it updates existing records instead of duplicating them
- Actors and movies are matched by their source URL, so namesakes stay separate
- Django admin with search and filters
- Test suite for the importer and all views

## Tech stack

Python 3.14, Django 6.1, SQLite, aiohttp, BeautifulSoup, WhiteNoise, Gunicorn, Docker.

## Data flow

```
Rotten Tomatoes -> collector (aiohttp + BeautifulSoup) -> data/movies.json
    -> import_movies command -> SQLite -> Django views and templates
```

## Project structure

```
collector/collect_movies.py   async scraper, writes data/movies.json
docker/entrypoint.sh          container start: migrate, import, run Gunicorn
data/movies.json              collected data
online_cinema/config/         Django settings and root URLs
online_cinema/movies/         models, views, templates, import command, tests
```

## Run locally

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cd online_cinema
python manage.py migrate
python manage.py import_movies
python manage.py runserver
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd online_cinema
python manage.py migrate
python manage.py import_movies
python manage.py runserver
```

Open http://127.0.0.1:8000/. By default `import_movies` reads `data/movies.json`; pass another path as an argument if needed.

## Run with Docker

```bash
cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY and DJANGO_ALLOWED_HOSTS
docker compose up -d --build
```

The site is served by Gunicorn on port 80. On start the container applies migrations and imports `data/movies.json`; the SQLite database is kept in the `db-data` volume.

## Run tests

```bash
cd online_cinema
python manage.py test
```

## Refresh the data

From the project root:

```bash
python collector/collect_movies.py
cd online_cinema
python manage.py import_movies
```

The collector saves progress after every movie, so an interrupted run keeps what it has already collected. It depends on the HTML structure of Rotten Tomatoes; if the site changes its markup, the CSS selectors need updating.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `1` | Set to `0` in production |
| `DJANGO_SECRET_KEY` | dev key | Required when `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated host names |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins, e.g. `http://203.0.113.10`, needed for admin login |
| `DJANGO_DB_PATH` | `online_cinema/db.sqlite3` | SQLite file location |

In production run `python manage.py collectstatic`; static files are served by WhiteNoise.

## Data notice

Movie data and posters belong to Rotten Tomatoes and their owners. This is a non-commercial educational project.