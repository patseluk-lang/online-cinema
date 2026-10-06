from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, render

from interactions.models import rating_summary

from .models import Actor, Genre, Movie
from .recommendations import get_similar_movies, get_user_recommendations

MOVIES_PER_PAGE = 24

# Movies without a year or runtime go to the end of the list in every sort order.
SORT_OPTIONS = {
    "newest": ("Newest", [F("year").desc(nulls_last=True), "title"]),
    "oldest": ("Oldest", [F("year").asc(nulls_last=True), "title"]),
    "shortest": ("Shortest", [F("duration").asc(nulls_last=True), "title"]),
    "longest": ("Longest", [F("duration").desc(nulls_last=True), "title"]),
}


def movie_list(request):
    query = request.GET.get("q", "").strip()
    genre_id = request.GET.get("genre", "")
    sort = request.GET.get("sort", "")

    movies = Movie.objects.select_related("genre")
    if query:
        movies = movies.filter(title__icontains=query)
    if genre_id.isdigit():
        movies = movies.filter(genre_id=int(genre_id))
    if sort in SORT_OPTIONS:
        movies = movies.order_by(*SORT_OPTIONS[sort][1])
    else:
        sort = ""

    page = Paginator(movies, MOVIES_PER_PAGE).get_page(request.GET.get("page"))

    filters = request.GET.copy()
    filters.pop("page", None)

    # Personal picks only on the first page of the full catalogue, not above search results.
    recommendations = []
    if request.user.is_authenticated and page.number == 1 and not (query or genre_id or sort):
        recommendations = get_user_recommendations(request.user)

    return render(request, "movies/movie_list.html", {
        "page": page,
        "page_range": page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
        "recommendations": recommendations,
        "genres": Genre.objects.all(),
        "query": query,
        "genre_id": genre_id,
        "sort": sort,
        "sort_options": [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        "filters": filters.urlencode(),
    })


def movie_detail(request, pk):
    movie = get_object_or_404(
        Movie.objects.select_related("genre").prefetch_related("actors"), pk=pk
    )
    is_favorite = False
    user_rating = None
    if request.user.is_authenticated:
        is_favorite = movie.favorited_by.filter(user=request.user).exists()
        user_rating = movie.ratings.filter(user=request.user).first()

    return render(request, "movies/movie_detail.html", {
        "movie": movie,
        "is_favorite": is_favorite,
        "rating": rating_summary(movie),
        "user_rating": user_rating,
        "comments": movie.comments.filter(parent__isnull=True)
        .select_related("user").prefetch_related("replies__user"),
        "similar_movies": get_similar_movies(movie),
    })


def actor_detail(request, pk):
    actor = get_object_or_404(Actor, pk=pk)
    movies = actor.movies.select_related("genre")
    return render(request, "movies/actor_detail.html", {"actor": actor, "movies": movies})
