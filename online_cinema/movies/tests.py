import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import Actor, Genre, Movie

SAMPLE = {
    "movie1": {
        "url": "https://www.rottentomatoes.com/m/first",
        "title": "First Movie",
        "img_link": "https://example.com/first.jpg",
        "description": "A test movie.",
        "duration": 95,
        "genre": "Drama",
        "year": 2025,
        "actors": [
            {"name": "Jane Doe", "birth_year": 1980, "url": "https://www.rottentomatoes.com/celebrity/jane_doe_1"},
            {"name": "Jane Doe", "birth_year": 1995, "url": "https://www.rottentomatoes.com/celebrity/jane_doe_2"},
        ],
    },
    "movie2": {
        "title": "Old Format Movie",
        "img_link": None,
        "description": None,
        "duration": None,
        "genre": None,
        "year": 2024,
        "actors": [["John Smith", 1970]],
    },
}


class ImportMoviesTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "movies.json"
        self.path.write_text(json.dumps(SAMPLE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_import(self):
        call_command("import_movies", str(self.path), stdout=StringIO())

    def test_import_creates_records(self):
        self.run_import()
        self.assertEqual(Movie.objects.count(), 2)
        self.assertEqual(Genre.objects.count(), 2)
        self.assertTrue(Genre.objects.filter(name="Unknown").exists())

    def test_import_is_idempotent(self):
        self.run_import()
        self.run_import()
        self.assertEqual(Movie.objects.count(), 2)
        self.assertEqual(Actor.objects.count(), 3)

    def test_namesakes_with_different_urls_stay_separate(self):
        self.run_import()
        self.assertEqual(Actor.objects.filter(name="Jane Doe").count(), 2)

    def test_reimport_updates_existing_movie(self):
        self.run_import()
        SAMPLE_CHANGED = json.loads(json.dumps(SAMPLE))
        SAMPLE_CHANGED["movie1"]["duration"] = 100
        self.path.write_text(json.dumps(SAMPLE_CHANGED), encoding="utf-8")
        self.run_import()
        self.assertEqual(Movie.objects.get(title="First Movie").duration, 100)

    def test_new_file_with_urls_matches_old_records(self):
        old_format = {"movie1": {"title": "First Movie", "year": 2025, "genre": "Drama",
                                 "actors": [["Jane Doe", 1980]]}}
        self.path.write_text(json.dumps(old_format), encoding="utf-8")
        self.run_import()
        self.path.write_text(json.dumps({"movie1": SAMPLE["movie1"]}), encoding="utf-8")
        self.run_import()
        self.assertEqual(Movie.objects.count(), 1)
        self.assertEqual(Movie.objects.get().url, SAMPLE["movie1"]["url"])

    def test_missing_file_raises_error(self):
        with self.assertRaises(CommandError):
            call_command("import_movies", "no_such_file.json", stdout=StringIO())


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        drama = Genre.objects.create(name="Drama")
        comedy = Genre.objects.create(name="Comedy")
        cls.actor = Actor.objects.create(name="Jane Doe", birth_year=1980)
        cls.drama_movie = Movie.objects.create(title="Quiet Harbor", year=2025, genre=drama, duration=125)
        cls.comedy_movie = Movie.objects.create(title="Loud Neighbors", year=2025, genre=comedy)
        cls.drama_movie.actors.add(cls.actor)

    def test_list_shows_all_movies(self):
        response = self.client.get(reverse("movie_list"))
        self.assertContains(response, "Quiet Harbor")
        self.assertContains(response, "Loud Neighbors")

    def test_search_by_title(self):
        response = self.client.get(reverse("movie_list"), {"q": "harbor"})
        self.assertContains(response, "Quiet Harbor")
        self.assertNotContains(response, "Loud Neighbors")

    def test_filter_by_genre(self):
        genre = Genre.objects.get(name="Comedy")
        response = self.client.get(reverse("movie_list"), {"genre": genre.pk})
        self.assertContains(response, "Loud Neighbors")
        self.assertNotContains(response, "Quiet Harbor")

    def test_invalid_genre_is_ignored(self):
        response = self.client.get(reverse("movie_list"), {"genre": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_pagination(self):
        genre = Genre.objects.get(name="Drama")
        Movie.objects.bulk_create(Movie(title=f"Filler {i}", genre=genre) for i in range(30))
        response = self.client.get(reverse("movie_list"), {"page": 2})
        self.assertEqual(response.context["page"].number, 2)

    def test_movie_detail(self):
        response = self.client.get(self.drama_movie.get_absolute_url())
        self.assertContains(response, "Quiet Harbor")
        self.assertContains(response, "2h 05m")
        self.assertContains(response, self.actor.get_absolute_url())

    def test_actor_detail_lists_movies(self):
        response = self.client.get(self.actor.get_absolute_url())
        self.assertContains(response, "Quiet Harbor")
        self.assertNotContains(response, "Loud Neighbors")

    def test_missing_movie_returns_404(self):
        response = self.client.get(reverse("movie_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)