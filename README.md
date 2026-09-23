# Online Cinema

A Django catalogue of movies currently in theaters. An async scraper collects movies, genres and cast from Rotten Tomatoes, a management command loads them into SQLite or PostgreSQL, and the site lets you browse, search, filter and sort the catalogue.

**Live demo:** http://16.170.202.127/ (AWS EC2, Docker)

## Features

- Movie catalogue with title search, genre filter, sorting (newest, oldest, shortest, longest) and pagination
- Movie pages with description, runtime and cast
- Actor pages listing every movie of that actor in the catalogue
- Idempotent import: re-running it updates existing records instead of duplicating them
- Actors and movies are matched by their source URL, so namesakes stay separate
- Django admin with poster previews, movie and actor counts, search (including by actor name) and filters
- Test suite for the importer, all views and the admin

## Tech stack

Python 3.14, Django 6.1, SQLite / PostgreSQL, aiohttp, BeautifulSoup, WhiteNoise, Gunicorn, Docker.

## Data flow

```
Rotten Tomatoes -> collector (aiohttp + BeautifulSoup) -> data/movies.json
    -> import_movies command -> SQLite or PostgreSQL -> Django views and templates
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

## Deployment

The live demo runs on AWS EC2 (t3.micro, Ubuntu 24.04, region eu-north-1) with Docker Compose:

```bash
git clone https://github.com/patseluk-lang/online-cinema.git
cd online-cinema
cp .env.example .env
# set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS and DJANGO_CSRF_TRUSTED_ORIGINS for the server address
sudo docker compose up -d --build
```

The EC2 security group allows HTTP from anywhere and SSH only from the owner's IP address.

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
| `POSTGRES_DB` | empty | Database name; when set, PostgreSQL is used instead of SQLite |
| `POSTGRES_USER`, `POSTGRES_PASSWORD` | empty | PostgreSQL credentials |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `localhost`, `5432` | PostgreSQL server address |

For local runs the variables can be put in a `.env` file in the repository root; it is loaded automatically. In production run `python manage.py collectstatic`; static files are served by WhiteNoise.

## Data notice

Movie data and posters belong to Rotten Tomatoes and their owners. This is a non-commercial educational project.
