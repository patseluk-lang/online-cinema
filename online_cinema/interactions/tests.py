from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from movies.models import Genre, Movie

from .models import Comment, Favorite, Rating, WatchHistory


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


class WatchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("bob", password="Str0ng-pass-2026")
        genre = Genre.objects.create(name="Drama")
        cls.movie = Movie.objects.create(title="Quiet Harbor", year=2025, genre=genre, duration=97)
        cls.no_runtime = Movie.objects.create(title="No Runtime", year=2025, genre=genre)

    def setUp(self):
        self.client.force_login(self.user)

    def test_watch_returns_demo_seconds(self):
        response = self.client.get(reverse("watch_movie", args=[self.movie.pk]))
        self.assertEqual(response.json()["watch_seconds"], 10)

    def test_movie_without_runtime_does_not_crash(self):
        response = self.client.get(reverse("watch_movie", args=[self.no_runtime.pk]))
        self.assertEqual(response.json()["watch_seconds"], 1)

    def test_complete_watch_adds_history(self):
        url = reverse("complete_watch", args=[self.movie.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertTrue(response.json()["success"])
        item = WatchHistory.objects.get()
        self.assertEqual((item.user, item.movie, item.watch_duration), (self.user, self.movie, 10))

    def test_guest_cannot_watch(self):
        self.client.logout()
        response = self.client.post(reverse("complete_watch", args=[self.movie.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(WatchHistory.objects.exists())

    def test_profile_shows_history(self):
        WatchHistory.objects.create(user=self.user, movie=self.movie, watch_duration=10)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "Переглянуто: 10 сек.")


class RatingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user("bob", password="Str0ng-pass-2026")
        cls.ann = User.objects.create_user("ann", password="Str0ng-pass-2026")
        genre = Genre.objects.create(name="Drama")
        cls.movie = Movie.objects.create(title="Quiet Harbor", year=2025, genre=genre)
        cls.url = reverse("rate_movie", args=[cls.movie.pk])

    def rate(self, user, value):
        self.client.force_login(user)
        return self.client.post(self.url, {"rating": value})

    def test_rating_is_saved_and_updated(self):
        self.assertTrue(self.rate(self.bob, "4").json()["created"])
        data = self.rate(self.bob, "2").json()
        self.assertFalse(data["created"])
        self.assertEqual(Rating.objects.get().value, 2)
        self.assertEqual((data["average"], data["count"]), (2, 1))

    def test_average_over_users(self):
        self.rate(self.bob, "4")
        data = self.rate(self.ann, "3").json()
        self.assertEqual((data["average"], data["count"]), (3.5, 2))
        response = self.client.get(self.movie.get_absolute_url())
        self.assertContains(response, "⭐ 3.5")

    def test_invalid_values_are_rejected(self):
        for value in ("0", "6", "abc", ""):
            response = self.rate(self.bob, value)
            self.assertEqual(response.status_code, 400, value)
        self.assertFalse(Rating.objects.exists())

    def test_guest_cannot_rate(self):
        response = self.client.post(self.url, {"rating": "5"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Rating.objects.exists())

    def test_detail_marks_users_stars(self):
        self.rate(self.bob, "3")
        response = self.client.get(self.movie.get_absolute_url())
        self.assertContains(response, "3/5")
        self.assertEqual(response.content.decode().count("rating-button active"), 3)

    def test_movie_without_ratings(self):
        response = self.client.get(self.movie.get_absolute_url())
        self.assertContains(response, "Немає оцінок")
        self.assertContains(response, "Увійдіть, щоб оцінити фільм")

    def test_admin_changelists_open(self):
        admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.rate(self.bob, "5")
        WatchHistory.objects.create(user=self.bob, movie=self.movie, watch_duration=1)
        self.client.force_login(admin)
        for model in ("rating", "watchhistory"):
            response = self.client.get(reverse(f"admin:interactions_{model}_changelist"))
            self.assertContains(response, "Quiet Harbor")


class CommentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user("bob", password="Str0ng-pass-2026")
        cls.ann = User.objects.create_user("ann", password="Str0ng-pass-2026")
        genre = Genre.objects.create(name="Drama")
        cls.movie = Movie.objects.create(title="Quiet Harbor", year=2025, genre=genre)
        cls.other_movie = Movie.objects.create(title="Loud Neighbors", year=2025, genre=genre)

    def comment(self, user=None, text="Great film", parent=None):
        return Comment.objects.create(user=user or self.bob, movie=self.movie, text=text, parent=parent)

    def test_add_comment(self):
        self.client.force_login(self.bob)
        response = self.client.post(reverse("add_comment", args=[self.movie.pk]), {"text": "Great film"})
        self.assertRedirects(response, self.movie.get_absolute_url() + "#comments")
        self.assertEqual(Comment.objects.get().user, self.bob)

    def test_empty_comment_is_ignored(self):
        self.client.force_login(self.bob)
        self.client.post(reverse("add_comment", args=[self.movie.pk]), {"text": "   "})
        self.assertFalse(Comment.objects.exists())

    def test_guest_cannot_comment(self):
        response = self.client.post(reverse("add_comment", args=[self.movie.pk]), {"text": "Hi"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.exists())

    def test_reply_to_reply_stays_one_level_deep(self):
        top = self.comment()
        self.client.force_login(self.ann)
        url = reverse("add_reply", args=[self.movie.pk, top.pk])
        self.assertTrue(self.client.post(url, {"text": "Agree"}).json()["success"])
        reply = Comment.objects.get(text="Agree")
        self.assertEqual(reply.parent, top)

        url = reverse("add_reply", args=[self.movie.pk, reply.pk])
        self.client.post(url, {"text": "Me too"})
        self.assertEqual(Comment.objects.get(text="Me too").parent, top)

    def test_reply_to_comment_of_other_movie_is_404(self):
        top = self.comment()
        self.client.force_login(self.ann)
        response = self.client.post(reverse("add_reply", args=[self.other_movie.pk, top.pk]), {"text": "x"})
        self.assertEqual(response.status_code, 404)

    def test_owner_can_edit_and_delete(self):
        comment = self.comment()
        self.client.force_login(self.bob)
        data = self.client.post(reverse("edit_comment", args=[comment.pk]), {"text": "Changed"}).json()
        self.assertEqual(data["text"], "Changed")
        self.assertEqual(Comment.objects.get().text, "Changed")
        self.assertTrue(self.client.post(reverse("delete_comment", args=[comment.pk])).json()["success"])
        self.assertFalse(Comment.objects.exists())

    def test_other_user_cannot_edit_or_delete(self):
        comment = self.comment()
        self.client.force_login(self.ann)
        self.assertEqual(self.client.post(reverse("edit_comment", args=[comment.pk]), {"text": "x"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("delete_comment", args=[comment.pk])).status_code, 403)
        self.assertEqual(Comment.objects.get().text, "Great film")

    def test_edit_to_empty_text_is_rejected(self):
        comment = self.comment()
        self.client.force_login(self.bob)
        response = self.client.post(reverse("edit_comment", args=[comment.pk]), {"text": ""})
        self.assertEqual(response.status_code, 400)

    def test_deleting_comment_removes_replies(self):
        top = self.comment()
        self.comment(user=self.ann, text="Reply", parent=top)
        self.client.force_login(self.bob)
        self.client.post(reverse("delete_comment", args=[top.pk]))
        self.assertFalse(Comment.objects.exists())

    def test_detail_page_shows_comments_and_buttons(self):
        top = self.comment(text="<b>bold</b>")
        self.comment(user=self.ann, text="Reply text", parent=top)
        self.client.force_login(self.ann)
        response = self.client.get(self.movie.get_absolute_url())
        self.assertContains(response, "&lt;b&gt;bold&lt;/b&gt;")
        self.assertContains(response, "Reply text")
        self.assertContains(response, 'class="edit-button"', count=1)

    def test_detail_page_empty_and_guest(self):
        response = self.client.get(self.movie.get_absolute_url())
        self.assertContains(response, "Коментарів поки немає")
        self.assertContains(response, "щоб залишити коментар")
        self.assertNotContains(response, "reply-button")

    def test_admin_changelist_opens(self):
        admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.comment(text="Admin sees this")
        self.client.force_login(admin)
        response = self.client.get(reverse("admin:interactions_comment_changelist"))
        self.assertContains(response, "Admin sees this")
