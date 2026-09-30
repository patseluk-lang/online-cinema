from django.contrib.auth.models import User
from django.db import models

from movies.models import Movie


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "movie"], name="unique_user_movie_favorite")
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.movie.title}"
