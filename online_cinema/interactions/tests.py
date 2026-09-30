from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from movies.models import Genre, Movie

from .models import Favorite


class ToggleFavoriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("bob", password="Str0ng-pass-2026")
        genre = Genre.objects.create(name="Drama")
        cls.movie = Movie.objects.create(title="Quiet Harbor", year=2025, genre=genre)
        cls.url = reverse("toggle_favorite", args=[cls.movie.pk])

    def test_guest_is_sent_to_login(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("login") + "?next=" + self.url,
                             fetch_redirect_response=False)
        self.assertFalse(Favorite.objects.exists())

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_toggle_adds_then_removes(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url)
        self.assertRedirects(response, self.movie.get_absolute_url())
        self.assertTrue(Favorite.objects.filter(user=self.user, movie=self.movie).exists())

        detail = self.client.get(self.movie.get_absolute_url())
        self.assertContains(detail, "В обраному")

        self.client.post(self.url)
        self.assertFalse(Favorite.objects.exists())

        detail = self.client.get(self.movie.get_absolute_url())
        self.assertContains(detail, "Додати в обране")

    def test_missing_movie_returns_404(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("toggle_favorite", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_same_movie_cannot_be_saved_twice(self):
        Favorite.objects.create(user=self.user, movie=self.movie)
        with self.assertRaises(IntegrityError):
            Favorite.objects.create(user=self.user, movie=self.movie)

    def test_admin_changelist_opens(self):
        admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        Favorite.objects.create(user=self.user, movie=self.movie)
        self.client.force_login(admin)
        response = self.client.get(reverse("admin:interactions_favorite_changelist"))
        self.assertContains(response, "Quiet Harbor")
