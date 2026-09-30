from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from interactions.models import Favorite
from movies.models import Genre, Movie

PASSWORD = "Str0ng-pass-2026"


class RegisterTests(TestCase):
    def register(self, **overrides):
        data = {"username": "bob", "email": "bob@example.com",
                "password": PASSWORD, "password_confirm": PASSWORD}
        data.update(overrides)
        return self.client.post(reverse("register"), data)

    def test_register_creates_user_with_hashed_password(self):
        response = self.register()
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="bob")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)

    def test_passwords_must_match(self):
        response = self.register(password_confirm="Other-pass-2026")
        self.assertContains(response, "Паролі не збігаються.")
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self):
        response = self.register(password="12345", password_confirm="12345")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user("bob", password=PASSWORD)
        response = self.register()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)


class LoginLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("bob", "bob@example.com", PASSWORD)

    def test_login_redirects_to_catalogue(self):
        response = self.client.post(reverse("login"), {"username": "bob", "password": PASSWORD})
        self.assertRedirects(response, reverse("movie_list"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_returns_to_next_page(self):
        response = self.client.post(reverse("login"), {
            "username": "bob", "password": PASSWORD, "next": "/movies/1/"})
        self.assertRedirects(response, "/movies/1/", fetch_redirect_response=False)

    def test_login_ignores_external_next(self):
        response = self.client.post(reverse("login"), {
            "username": "bob", "password": PASSWORD, "next": "https://evil.example.com/"})
        self.assertRedirects(response, reverse("movie_list"))

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse("login"), {"username": "bob", "password": "wrong"})
        self.assertContains(response, "Неправильний логін або пароль.")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("movie_list"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_header_shows_username_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("movie_list"))
        self.assertContains(response, "👤 bob")
        self.assertContains(response, "Вийти")


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("bob", "bob@example.com", PASSWORD)
        genre = Genre.objects.create(name="Drama")
        cls.movie = Movie.objects.create(title="Quiet Harbor", year=2025, genre=genre)
        Movie.objects.create(title="Not Liked", year=2025, genre=genre)
        Favorite.objects.create(user=cls.user, movie=cls.movie)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertRedirects(response, reverse("login") + "?next=" + reverse("profile"))

    def test_profile_lists_only_own_favorites(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "Вітаємо, bob")
        self.assertContains(response, "Quiet Harbor")
        self.assertNotContains(response, "Not Liked")

    def test_empty_profile_message(self):
        other = User.objects.create_user("ann", password=PASSWORD)
        self.client.force_login(other)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "Ви ще не додали жодного фільму в обране")
