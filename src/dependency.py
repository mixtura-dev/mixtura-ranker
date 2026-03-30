"""
Dependency injection для сервиса рейтингов.
"""

from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from faststream import Context, Depends

from src.infra.postgre.engine import DatabaseSessionManager
from src.infra.postgre.repo import HiddenRatingRepository
from src.domain.service.rating_service import RatingService


async def get_db_session(
    session_manager: Annotated[DatabaseSessionManager, Context()]
):
    """Получение сессии БД."""
    async with session_manager.session() as session:
        yield session


async def get_hidden_rating_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> HiddenRatingRepository:
    """Получение репозитория скрытого рейтинга."""
    return HiddenRatingRepository(session)


HiddenRatingRepositoryDependency = Annotated[HiddenRatingRepository, Depends(get_hidden_rating_repo)]


async def get_rating_service(
    hidden_rating_repo: HiddenRatingRepositoryDependency,
) -> RatingService:
    """Factory для создания сервиса рейтингов."""
    return RatingService(hidden_rating_repo=hidden_rating_repo)


RatingServiceDependency = Annotated[RatingService, Depends(get_rating_service)]
