from django.db import models
from django.urls import reverse


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Actor(models.Model):
    name = models.CharField(max_length=200)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    url = models.URLField(max_length=500, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("actor_detail", args=[self.pk])


class Movie(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=500, unique=True, null=True, blank=True)
    img_link = models.URLField(max_length=1000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="movies")
    actors = models.ManyToManyField(Actor, related_name="movies", blank=True)

    class Meta:
        ordering = ["-year", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("movie_detail", args=[self.pk])

    @property
    def duration_display(self):
        if not self.duration:
            return ""
        hours, minutes = divmod(self.duration, 60)
        return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"
