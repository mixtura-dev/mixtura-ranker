"""
Основные фикстуры для тестов.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from src.domain.models.rating import (
    HiddenRating,
    PlayerRating,
    RatingSystemConfig,
)
from src.infra.postgre.engine import Base
from src.infra.postgre.repo import HiddenRatingRepository


@pytest_asyncio.fixture(scope="session")
async def postgres_container() -> AsyncGenerator[str, None]:
    with PostgresContainer("postgres:15") as container:
        container.start()
        sync_url = container.get_connection_url()
        sync_url = "postgresql://" + sync_url.split("://")[1]
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")

        yield async_url


@pytest_asyncio.fixture(scope="session")
async def async_engine(postgres_container):
    engine = create_async_engine(
        postgres_container,
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def async_session(async_engine):
    async with async_engine.connect() as connection:
        async with connection.begin() as transaction:
            session_factory = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
            )
            async with session_factory() as session:
                yield session

            await transaction.rollback()



@dataclass
class TestPlayerRole:
    """Тестовая роль игрока."""
    priority: int
    open_rating: int


@dataclass
class TestPlayer:
    """Тестовый игрок."""
    member_id: uuid.UUID
    roles: dict[uuid.UUID, TestPlayerRole] = field(default_factory=dict)


@dataclass
class TestMatchTeam:
    """Тестовая команда в матче."""
    team_id: uuid.UUID
    player_ids: list[uuid.UUID]


@dataclass
class TestMatchPlayer:
    """Тестовый участник матча."""
    member_id: uuid.UUID
    role_id: uuid.UUID
    open_rating: float


class Factory:
    """
    Фабрика для создания тестовых данных.
    
    Создаёт различные сущности для тестирования без зависимости от БД.
    """

    @staticmethod
    def create_uuid() -> uuid.UUID:
        """Создать новый UUID."""
        return uuid.uuid4()

    @staticmethod
    def create_hidden_rating(
        mu: float = 0.0,
        sigma: float = 25.0
    ) -> HiddenRating:
        """Создать скрытый рейтинг."""
        return HiddenRating(mu=mu, sigma=sigma)

    @staticmethod
    def create_rating_config(
        r_min: float = 0.0,
        r_max: float = 5000.0,
        r_avg: float = 2400.0,
        g: float = 0.5,
        sigma_init: float = 25.0,
        d: float = 4.0
    ) -> RatingSystemConfig:
        """Создать конфигурацию рейтинговой системы."""
        return RatingSystemConfig(
            r_min=r_min,
            r_max=r_max,
            r_avg=r_avg,
            g=g,
            sigma_init=sigma_init,
            d=d
        )

    @staticmethod
    def create_player_rating(
        member_id: Optional[uuid.UUID] = None,
        role_id: Optional[uuid.UUID] = None,
        open_rating: float = 2400.0,
        mu: float = 0.0,
        sigma: float = 25.0
    ) -> PlayerRating:
        """Создать полный рейтинг игрока."""
        return PlayerRating(
            member_id=member_id or uuid.uuid4(),
            role_id=role_id or uuid.uuid4(),
            open_rating=open_rating,
            hidden_rating=HiddenRating(mu=mu, sigma=sigma)
        )

    @staticmethod
    def create_player(
        member_id: Optional[uuid.UUID] = None,
        roles: Optional[dict[uuid.UUID, TestPlayerRole]] = None
    ) -> TestPlayer:
        """Создать тестового игрока."""
        if roles is None:
            member_id = member_id or uuid.uuid4()
            role_id = uuid.uuid4()
            roles = {role_id: TestPlayerRole(priority=0, open_rating=2400)}
        
        return TestPlayer(
            member_id=member_id or uuid.uuid4(),
            roles=roles
        )

    @staticmethod
    def create_match_team(
        team_id: Optional[uuid.UUID] = None,
        player_ids: Optional[list[uuid.UUID]] = None
    ) -> TestMatchTeam:
        """Создать тестовую команду."""
        return TestMatchTeam(
            team_id=team_id or uuid.uuid4(),
            player_ids=player_ids or [uuid.uuid4()]
        )

    @staticmethod
    def create_match_player(
        member_id: Optional[uuid.UUID] = None,
        role_id: Optional[uuid.UUID] = None,
        open_rating: float = 2400.0
    ) -> TestMatchPlayer:
        """Создать тестового участника матча."""
        return TestMatchPlayer(
            member_id=member_id or uuid.uuid4(),
            role_id=role_id or uuid.uuid4(),
            open_rating=open_rating
        )


class Helpers:
    """Хелперы для тестов."""

    @staticmethod
    def perm_mask(*perms: str) -> int:
        """Создание битовой маски разрешений."""
        mask = 0
        perm_map = {
            "READ": 1,
            "WRITE": 2,
            "DELETE": 4,
            "ADMIN": 8,
        }
        for perm in perms:
            mask |= perm_map.get(perm, 0)
        return mask

    @staticmethod
    def restr_mask(*restrs: str) -> int:
        """Создание битовой маски ограничений."""
        mask = 0
        restr_map = {
            "BANNED": 1,
            "MUTED": 2,
            "RESTRICTED": 4,
        }
        for restr in restrs:
            mask |= restr_map.get(restr, 0)
        return mask


@pytest.fixture
def factory() -> type[Factory]:
    """Фикстура фабрики для создания тестовых данных."""
    return Factory


@pytest.fixture
def helpers() -> type[Helpers]:
    """Фикстура хелперов для тестов."""
    return Helpers


@pytest.fixture
def rating_config() -> RatingSystemConfig:
    """Фикстура конфигурации рейтинговой системы по умолчанию."""
    return Factory.create_rating_config()


@pytest.fixture
def hidden_rating() -> HiddenRating:
    """Фикстура скрытого рейтинга по умолчанию."""
    return Factory.create_hidden_rating()


@pytest.fixture
def mock_session() -> AsyncMock:
    """Фикстура мока сессии БД."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_hidden_rating_repo() -> AsyncMock:
    """Фикстура мока репозитория скрытого рейтинга."""
    repo = AsyncMock(spec=HiddenRatingRepository)
    repo.get_latest = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    return repo
