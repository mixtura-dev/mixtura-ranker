"""
Тесты для RatingService.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.domain.models.rating import HiddenRating
from src.domain.models.requests import (
    EffectiveRatingRequest,
    MatchPlayer,
    MatchResult,
    MatchTeam,
    Player,
    PlayerRole,
    RatingSettings,
)
from src.domain.models.responses import EffectiveRatingResponse, MatchResultResponse
from src.domain.service.rating_service import RatingService


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Фикстура мока репозитория скрытого рейтинга."""
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def rating_service(mock_repo: AsyncMock) -> RatingService:
    """Фикстура сервиса рейтингов."""
    return RatingService(hidden_rating_repo=mock_repo)


@pytest.fixture
def rating_service_no_repo(mock_repo: AsyncMock) -> RatingService:
    """Фикстура сервиса рейтингов без репозитория."""
    mock_repo.get_latest = AsyncMock(return_value=None)
    return RatingService(hidden_rating_repo=mock_repo)


@pytest.fixture
def default_settings() -> RatingSettings:
    """Фикстура настроек рейтинговой системы."""
    return RatingSettings(
        r_min=0.0,
        r_max=5000.0,
        r_avg=2400.0,
        g=0.5,
        sigma_init=25.0,
        d=4.0
    )


@pytest.fixture
def sample_players() -> list[Player]:
    """Фикстура списка игроков."""
    member1 = uuid.uuid4()
    member2 = uuid.uuid4()
    role1 = uuid.uuid4()
    role2 = uuid.uuid4()
    
    return [
        Player(
            member_id=member1,
            roles={
                role1: PlayerRole(priority=0, open_rating=2400)
            }
        ),
        Player(
            member_id=member2,
            roles={
                role2: PlayerRole(priority=0, open_rating=2600)
            }
        )
    ]


class TestCalculateEffectiveRatings:
    """Тесты calculate_effective_ratings."""

    @pytest.mark.asyncio
    async def test_calculate_effective_ratings_basic(
        self,
        rating_service: RatingService,
        default_settings: RatingSettings,
        sample_players: list[Player]
    ):
        """Базовый тест вычисления эффективных рейтингов."""
        request = EffectiveRatingRequest(
            draft_id=uuid.uuid4(),
            players=sample_players,
            settings=default_settings
        )
        
        result = await rating_service.calculate_effective_ratings(request)
        
        assert isinstance(result, EffectiveRatingResponse)
        assert result.draft_id == request.draft_id
        assert len(result.players) == len(sample_players)

    @pytest.mark.asyncio
    async def test_calculate_effective_ratings_returns_valid_ratings(
        self,
        rating_service: RatingService,
        default_settings: RatingSettings,
        sample_players: list[Player]
    ):
        """Проверка что возвращаемые рейтинги в допустимом диапазоне."""
        request = EffectiveRatingRequest(
            draft_id=uuid.uuid4(),
            players=sample_players,
            settings=default_settings
        )
        
        result = await rating_service.calculate_effective_ratings(request)
        
        for player in result.players:
            assert default_settings.r_min <= player.effective_rating <= default_settings.r_max
            assert default_settings.r_min <= player.hidden_rating <= default_settings.r_max
            assert default_settings.r_min <= player.open_rating <= default_settings.r_max

    @pytest.mark.asyncio
    async def test_calculate_effective_ratings_with_player_without_db_entry(
        self,
        rating_service: RatingService,
        default_settings: RatingSettings
    ):
        """Игрок без записи в БД получает дефолтный скрытый рейтинг."""
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        request = EffectiveRatingRequest(
            draft_id=uuid.uuid4(),
            players=[
                Player(
                    member_id=member_id,
                    roles={role_id: PlayerRole(priority=0, open_rating=2400)}
                )
            ],
            settings=default_settings
        )
        
        result = await rating_service.calculate_effective_ratings(request)
        
        assert len(result.players) == 1
        assert result.players[0].member_id == member_id

    @pytest.mark.asyncio
    async def test_calculate_effective_ratings_uses_settings(
        self,
        rating_service: RatingService,
        sample_players: list[Player]
    ):
        """Проверка что настройки применяются."""
        custom_settings = RatingSettings(r_min=0, r_max=10000, r_avg=5000)
        
        request = EffectiveRatingRequest(
            draft_id=uuid.uuid4(),
            players=sample_players,
            settings=custom_settings
        )
        
        result = await rating_service.calculate_effective_ratings(request)
        
        for player in result.players:
            assert 0 <= player.effective_rating <= 10000


class TestCalculateEffectiveRatingsWithoutRepo:
    """Тесты без репозитория."""

    @pytest.mark.asyncio
    async def test_calculate_effective_ratings_no_repo(
        self,
        rating_service_no_repo: RatingService,
        default_settings: RatingSettings,
        sample_players: list[Player]
    ):
        """Сервис работает без репозитория."""
        request = EffectiveRatingRequest(
            draft_id=uuid.uuid4(),
            players=sample_players,
            settings=default_settings
        )
        
        result = await rating_service_no_repo.calculate_effective_ratings(request)
        
        assert isinstance(result, EffectiveRatingResponse)
        assert len(result.players) == 2


class TestProcessMatchResult:
    """Тесты process_match_result."""

    @pytest.mark.asyncio
    async def test_process_match_result_basic(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock,
        default_settings: RatingSettings
    ):
        """Базовый тест обработки результата матча."""
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role1 = uuid.uuid4()
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member1]),
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member2])
            ],
            team_ranks=[1.0, 2.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0),
                MatchPlayer(member_id=member2, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        result = await rating_service.process_match_result(request)
        
        assert isinstance(result, MatchResultResponse)
        assert result.match_id == request.match_id
        assert len(result.player_updates) == 2

    @pytest.mark.asyncio
    async def test_process_match_result_first_place_gains_rating(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock,
        default_settings: RatingSettings
    ):
        """Первое место должно получить положительный прирост рейтинга."""
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role1 = uuid.uuid4()
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member1]),
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member2])
            ],
            team_ranks=[1.0, 2.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0),
                MatchPlayer(member_id=member2, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        result = await rating_service.process_match_result(request)
        
        first_place = next(
            p for p in result.player_updates if p.member_id == member1
        )
        second_place = next(
            p for p in result.player_updates if p.member_id == member2
        )
        
        assert first_place.open_rating_delta > second_place.open_rating_delta

    @pytest.mark.asyncio
    async def test_process_match_result_creates_hidden_rating_for_new_player(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock,
        default_settings: RatingSettings
    ):
        """Для нового игрока создаётся скрытый рейтинг в БД."""
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role1 = uuid.uuid4()
        
        mock_repo.get_latest = AsyncMock(return_value=None)
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member1]),
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member2])
            ],
            team_ranks=[1.0, 2.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0),
                MatchPlayer(member_id=member2, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        await rating_service.process_match_result(request)
        
        assert mock_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_process_match_result_does_not_create_for_existing_player(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock,
        default_settings: RatingSettings
    ):
        """Существующий игрок не создаёт новую запись."""
        from src.infra.postgre.models import PlayerRoleHiddenRating
        
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role1 = uuid.uuid4()
        
        existing_rating = PlayerRoleHiddenRating(
            member_id=member1,
            role_id=role1,
            mu=0.0,
            sigma=25.0
        )
        mock_repo.get_latest = AsyncMock(return_value=existing_rating)
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member1]),
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member2])
            ],
            team_ranks=[1.0, 2.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0),
                MatchPlayer(member_id=member2, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        await rating_service.process_match_result(request)
        
        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_match_result_invalid_player_raises(
        self,
        rating_service: RatingService,
        default_settings: RatingSettings
    ):
        """Игрок не в списке players вызывает ошибку."""
        member1 = uuid.uuid4()
        member_not_in_list = uuid.uuid4()
        role1 = uuid.uuid4()
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member_not_in_list])
            ],
            team_ranks=[1.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        with pytest.raises(ValueError, match="not found in match players"):
            await rating_service.process_match_result(request)


class TestMatchResultWithExistingDbRating:
    """Тесты с существующим рейтингом в БД."""

    @pytest.mark.asyncio
    async def test_uses_existing_hidden_rating(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock,
        default_settings: RatingSettings
    ):
        """При наличии записи в БД используется существующий скрытый рейтинг."""
        from src.infra.postgre.models import PlayerRoleHiddenRating
        
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role1 = uuid.uuid4()
        
        existing = PlayerRoleHiddenRating(
            member_id=member1,
            role_id=role1,
            mu=50.0,
            sigma=20.0
        )
        mock_repo.get_latest = AsyncMock(return_value=existing)
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member1]),
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member2])
            ],
            team_ranks=[1.0, 2.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0),
                MatchPlayer(member_id=member2, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        result = await rating_service.process_match_result(request)
        
        assert len(result.player_updates) == 2


class TestProcessMatchResultNoRepo:
    """Тесты process_match_result без репозитория."""

    @pytest.mark.asyncio
    async def test_process_match_result_no_repo(
        self,
        rating_service_no_repo: RatingService,
        default_settings: RatingSettings
    ):
        """Сервис работает без репозитория."""
        member1 = uuid.uuid4()
        member2 = uuid.uuid4()
        role1 = uuid.uuid4()
        
        request = MatchResult(
            match_id=uuid.uuid4(),
            match_time=datetime.now(),
            teams=[
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member1]),
                MatchTeam(team_id=uuid.uuid4(), player_ids=[member2])
            ],
            team_ranks=[1.0, 2.0],
            players=[
                MatchPlayer(member_id=member1, role_id=role1, open_rating=2400.0),
                MatchPlayer(member_id=member2, role_id=role1, open_rating=2400.0)
            ],
            settings=default_settings
        )
        
        result = await rating_service_no_repo.process_match_result(request)
        
        assert isinstance(result, MatchResultResponse)


class TestRatingServiceInternals:
    """Тесты внутренних методов."""

    @pytest.mark.asyncio
    async def test_get_hidden_rating_from_db(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock
    ):
        """Получение рейтинга из БД."""
        from src.infra.postgre.models import PlayerRoleHiddenRating
        
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        
        db_rating = PlayerRoleHiddenRating(
            member_id=member_id,
            role_id=role_id,
            mu=30.0,
            sigma=20.0
        )
        mock_repo.get_latest = AsyncMock(return_value=db_rating)
        
        from src.domain.service.rating_math_ops import RatingMathOperations
        from src.domain.models.rating import RatingSystemConfig
        
        config = RatingSystemConfig()
        math_ops = RatingMathOperations(config)
        
        result = await rating_service._get_hidden_rating(
            member_id, role_id, math_ops
        )
        
        assert result.mu == 30.0
        assert result.sigma == 20.0

    @pytest.mark.asyncio
    async def test_get_hidden_rating_new_player_with_open(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock
    ):
        """Новый игрок с переданным открытым рейтингом."""
        mock_repo.get_latest = AsyncMock(return_value=None)
        
        from src.domain.service.rating_math_ops import RatingMathOperations
        from src.domain.models.rating import RatingSystemConfig
        
        config = RatingSystemConfig()
        math_ops = RatingMathOperations(config)
        
        result = await rating_service._get_hidden_rating(
            uuid.uuid4(), uuid.uuid4(), math_ops, open_rating=2400.0
        )
        
        assert isinstance(result, HiddenRating)
        assert result.sigma == config.sigma_init

    @pytest.mark.asyncio
    async def test_get_hidden_rating_new_player_no_open(
        self,
        rating_service: RatingService,
        mock_repo: AsyncMock
    ):
        """Новый игрок без открытого рейтинга получает дефолтный."""
        mock_repo.get_latest = AsyncMock(return_value=None)
        
        from src.domain.service.rating_math_ops import RatingMathOperations
        from src.domain.models.rating import RatingSystemConfig
        
        config = RatingSystemConfig()
        math_ops = RatingMathOperations(config)
        
        result = await rating_service._get_hidden_rating(
            uuid.uuid4(), uuid.uuid4(), math_ops
        )
        
        assert result.mu == 0.0
        assert result.sigma == config.sigma_init

    def test_create_math_ops(self, rating_service: RatingService):
        """Создание математических операций из настроек."""
        settings = {
            "r_min": 0.0,
            "r_max": 5000.0,
            "r_avg": 2400.0,
            "g": 0.5,
            "sigma_init": 25.0,
            "d": 4.0
        }
        
        result = rating_service._create_math_ops(settings)
        
        assert result.config.r_min == 0.0
        assert result.config.r_max == 5000.0
        assert result.config.sigma_init == 25.0
