import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from movies.models import Actor, Genre, Movie

DEFAULT_PATH = Path(settings.BASE_DIR).parent / "data" / "movies.json"


def normalize_actor(actor_data):
    """Accept both formats: [name, birth_year] and {"name", "birth_year", "url"}."""
    if isinstance(actor_data, dict):
        return actor_data.get("name"), actor_data.get("birth_year"), actor_data.get("url")
    name, birth_year = actor_data
    return name, birth_year, None


class Command(BaseCommand):
    help = "Import movies from a collector JSON file"

    def add_arguments(self, parser):
        parser.add_argument("file_path", nargs="?", default=str(DEFAULT_PATH))

    def handle(self, *args, **options):
        path = Path(options["file_path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}") from exc

        stats = {"movies": 0, "actors": 0, "genres": 0}
        with transaction.atomic():
            for movie_data in data.values():
                self.import_movie(movie_data, stats)

        self.stdout.write(self.style.SUCCESS(
            f"Movies created: {stats['movies']}; "
            f"Actors created: {stats['actors']}; "
            f"Genres created: {stats['genres']}"
        ))

    def import_movie(self, movie_data, stats):
        genre, created = Genre.objects.get_or_create(name=movie_data.get("genre") or "Unknown")
        stats["genres"] += int(created)

        fields = {
            "title": movie_data.get("title") or "Untitled",
            "year": movie_data.get("year"),
            "img_link": movie_data.get("img_link"),
            "description": movie_data.get("description"),
            "duration": movie_data.get("duration"),
            "genre": genre,
        }
        url = movie_data.get("url")
        movie = Movie.objects.filter(url=url).first() if url else None
        if movie is None:
            # Records imported from older files have no URL: match them by title and year.
            movie = Movie.objects.filter(url=None, title=fields["title"], year=fields["year"]).first()
        created = movie is None
        if created:
            movie = Movie(url=url)
        for name, value in fields.items():
            setattr(movie, name, value)
        if url:
            movie.url = url
        movie.save()
        stats["movies"] += int(created)

        actors = []
        for actor_data in movie_data.get("actors", []):
            name, birth_year, url = normalize_actor(actor_data)
            if not name:
                continue
            actor = Actor.objects.filter(url=url).first() if url else None
            if actor is None:
                # Actors from older files have no URL: match them by name.
                actor = Actor.objects.filter(url=None, name=name).first()
            created = actor is None
            if created:
                actor = Actor(name=name)
            if url:
                actor.url = url
            if actor.birth_year is None and birth_year is not None:
                actor.birth_year = birth_year
            actor.save()
            stats["actors"] += int(created)
            actors.append(actor)
        movie.actors.set(actors)