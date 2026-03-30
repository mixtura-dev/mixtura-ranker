"""
Тесты для HiddenRatingRepository с использованием testcontainers.
"""

import uuid
from datetime import datetime

import pytest

from src.infra.postgre.models import PlayerRoleHiddenRating
from src.infra.postgre.repo.hidden_rating import HiddenRatingRepository


@pytest.mark.asyncio(loop_scope="session")
class TestHiddenRatingRepositoryCreate:
    """Тесты создания скрытого рейтинга."""

    async def test_create_basic(self, async_session):
        """Базовый тест создания."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        result = await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=25.0,
            sigma=20.0
        )
        
        assert result.member_id == member_id
        assert result.role_id == role_id
        assert result.mu == 25.0
        assert result.sigma == 20.0
        assert result.id is not None
        assert result.created_at is not None

    async def test_create_with_custom_datetime(self, async_session):
        """Создание с кастомным временем."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        custom_time = datetime(2024, 1, 15, 12, 0, 0)
        
        result = await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=25.0,
            sigma=20.0,
            created_at=custom_time
        )
        
        assert result.created_at == custom_time


@pytest.mark.asyncio(loop_scope="session")
class TestHiddenRatingRepositoryGetLatest:
    """Тесты получения последнего скрытого рейтинга."""

    async def test_get_latest_exists(self, async_session):
        """Получение существующего рейтинга."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=30.0,
            sigma=20.0
        )
        
        result = await repo.get_latest(member_id, role_id)
        
        assert result is not None
        assert result.member_id == member_id
        assert result.role_id == role_id
        assert result.mu == 30.0

    async def test_get_latest_not_exists(self, async_session):
        """Получение несуществующего рейтинга."""
        repo = HiddenRatingRepository(async_session)
        
        result = await repo.get_latest(uuid.uuid4(), uuid.uuid4())
        
        assert result is None

    async def test_get_latest_gets_newest(self, async_session):
        """Получение самой новой записи."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=10.0,
            sigma=25.0,
            created_at=datetime(2024, 1, 1)
        )

        
        await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=20.0,
            sigma=25.0,
            created_at=datetime(2024, 1, 2)
        )

        
        await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=30.0,
            sigma=25.0,
            created_at=datetime(2024, 1, 3)
        )

        
        result = await repo.get_latest(member_id, role_id)
        
        assert result is not None
        assert result.mu == 30.0

    async def test_get_latest_different_member(self, async_session):
        """Рейтинги разных игроков не пересекаются."""
        repo = HiddenRatingRepository(async_session)
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role_id = uuid.uuid4()
        
        await repo.create(
            member_id=member1,
            role_id=role_id,
            mu=100.0,
            sigma=25.0
        )

        
        await repo.create(
            member_id=member2,
            role_id=role_id,
            mu=200.0,
            sigma=25.0
        )

        
        result1 = await repo.get_latest(member1, role_id)
        result2 = await repo.get_latest(member2, role_id)
        
        assert result1.mu == 100.0
        assert result2.mu == 200.0


@pytest.mark.asyncio(loop_scope="session")
class TestHiddenRatingRepositoryHistory:
    """Тесты истории рейтингов."""

    async def test_multiple_ratings_same_player_role(self, async_session):
        """Несколько записей для одного игрока на роли - история."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        for i in range(5):
            await repo.create(
                member_id=member_id,
                role_id=role_id,
                mu=float(i * 10),
                sigma=25.0
            )
    
        
        latest = await repo.get_latest(member_id, role_id)
        
        assert latest.mu == 40.0


@pytest.mark.asyncio(loop_scope="session")
class TestHiddenRatingRepositoryEdgeCases:
    """Тесты граничных случаев."""

    async def test_zero_mu(self, async_session):
        """Нулевое mu."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        result = await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=0.0,
            sigma=25.0
        )

        
        assert result.mu == 0.0
        
        retrieved = await repo.get_latest(member_id, role_id)
        assert retrieved.mu == 0.0

    async def test_negative_mu(self, async_session):
        """Отрицательное mu."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        result = await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=-50.0,
            sigma=25.0
        )

        
        assert result.mu == -50.0

    async def test_large_sigma(self, async_session):
        """Большая неопределённость."""
        repo = HiddenRatingRepository(async_session)
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        result = await repo.create(
            member_id=member_id,
            role_id=role_id,
            mu=0.0,
            sigma=100.0
        )

        
        assert result.sigma == 100.0
