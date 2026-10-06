"""Movie recommendations.

Two movies are similar when they share the genre (+5), actors (+3 for each
common actor) and release time (+2 for the same year, +1 within 3 years).
"""
from collections import Counter

from .models import Movie

RECOMMENDATIONS_LIMIT = 5


def candidates(exclude_ids):
    """Load the catalogue once, with genres and actors, to avoid a query per movie."""
    movies = (
        Movie.objects.exclude(pk__in=exclude_ids)
        .select_related("genre")
        .prefetch_related("actors")
    )
    return [with_actor_ids(movie) for movie in movies]


def with_actor_ids(movie):
    movie.actor_ids = {actor.pk for actor in movie.actors.all()}
    return movie


def similarity(movie, candidate):
    score = 0
    if movie.genre_id == candidate.genre_id:
        score += 5
    score += 3 * len(movie.actor_ids & candidate.actor_ids)
    if movie.year and candidate.year:
        gap = abs(movie.year - candidate.year)
        if gap == 0:
            score += 2
        elif gap <= 3:
            score += 1
    return score


def top(scored, limit):
    """Best scores first; movies with zero score are not recommended."""
    scored = [(score, movie) for score, movie in scored if score > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [movie for _, movie in scored[:limit]]


def get_similar_movies(movie, limit=RECOMMENDATIONS_LIMIT):
    """Movies similar to the one the user is looking at."""
    with_actor_ids(movie)
    return top(
        ((similarity(movie, candidate), candidate) for candidate in candidates([movie.pk])),
        limit,
    )


def get_user_recommendations(user, limit=RECOMMENDATIONS_LIMIT):
    """Movies the user has not watched yet, similar to the ones they have watched.

    Every view counts, so a movie watched twice weighs twice as much.
    """
    watched = [
        with_actor_ids(item.movie)
        for item in user.watch_history.select_related("movie").prefetch_related("movie__actors")
    ]
    if not watched:
        return []

    genre_views = Counter(movie.genre_id for movie in watched)
    scored = (
        (
            genre_views[candidate.genre_id]
            + sum(similarity(movie, candidate) for movie in watched),
            candidate,
        )
        for candidate in candidates({movie.pk for movie in watched})
    )
    return top(scored, limit)
