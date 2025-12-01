from database import MovieModel
from database.models.movies import MovieStatusEnum


async def is_movie_available(movie: MovieModel) -> bool:
    return movie.is_active and movie.status == MovieStatusEnum.RELEASED
