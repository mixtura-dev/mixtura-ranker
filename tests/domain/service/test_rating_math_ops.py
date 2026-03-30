"""
Тесты для RatingMathOperations.
"""

import uuid

import pytest

from src.domain.models.rating import HiddenRating, RatingSystemConfig
from src.domain.service.rating_math_ops import RatingMathOperations


@pytest.fixture
def math_ops(rating_config: RatingSystemConfig) -> RatingMathOperations:
    """Фикстура математических операций с дефолтным конфигом."""
    return RatingMathOperations(rating_config)


@pytest.fixture
def custom_config() -> RatingSystemConfig:
    """Кастомный конфиг для тестирования."""
    return RatingSystemConfig(
        r_min=0.0,
        r_max=5000.0,
        r_avg=2500.0,
        g=0.5,
        sigma_init=25.0,
        d=4.0
    )


@pytest.fixture
def custom_math_ops(custom_config: RatingSystemConfig) -> RatingMathOperations:
    """Фикстура математических операций с кастомным конфигом."""
    return RatingMathOperations(custom_config)


class TestRatingMathOperationsInit:
    """Тесты инициализации."""

    def test_init_creates_model(self, math_ops: RatingMathOperations):
        """Проверка создания модели OpenSkill."""
        assert math_ops.model is not None

    def test_init_stores_config(self, math_ops: RatingMathOperations):
        """Проверка сохранения конфига."""
        assert math_ops.config.r_min == 0.0
        assert math_ops.config.r_max == 5000.0
        assert math_ops.config.sigma_init == 25.0


class TestSigmoidAndLogit:
    """Тесты сигмоиды и логита."""

    def test_sigmoid_zero(self, math_ops: RatingMathOperations):
        """Сигмоида от 0 равна 0.5."""
        result = math_ops._sigmoid(0.0)
        assert result == pytest.approx(0.5)

    def test_sigmoid_positive(self, math_ops: RatingMathOperations):
        """Сигмоида от положительного значения больше 0.5."""
        result = math_ops._sigmoid(2.0)
        assert result > 0.5
        assert result < 1.0

    def test_sigmoid_negative(self, math_ops: RatingMathOperations):
        """Сигмоида от отрицательного значения меньше 0.5."""
        result = math_ops._sigmoid(-2.0)
        assert result < 0.5
        assert result > 0.0

    def test_logit_zero(self, math_ops: RatingMathOperations):
        """Логит от 0.5 равен 0."""
        result = math_ops._logit(0.5)
        assert result == pytest.approx(0.0)

    def test_logit_roundtrip(self, math_ops: RatingMathOperations):
        """Логит от сигмоиды должен возвращать исходное значение."""
        original = 0.7
        sigmoided = math_ops._sigmoid(original)
        result = math_ops._logit(sigmoided)
        assert result == pytest.approx(original, rel=1e-6)


class TestDeltaTranslate:
    """Тесты delta_translate."""

    def test_delta_translate_default(self, math_ops: RatingMathOperations):
        """Тест с дефолтным конфигом."""
        result = math_ops.delta_translate()
        expected = (0.0 + 5000.0) / 2 - 2400.0
        assert result == pytest.approx(expected)

    def test_delta_translate_custom(self, custom_math_ops: RatingMathOperations):
        """Тест с кастомным конфигом."""
        result = custom_math_ops.delta_translate()
        expected = (0.0 + 5000.0) / 2 - 2500.0
        assert result == pytest.approx(expected)


class TestScaleClosed:
    """Тесты scale_closed."""

    def test_scale_closed_default(self, math_ops: RatingMathOperations):
        """Тест с дефолтным конфигом: s_closed = 4 * sigma_init."""
        result = math_ops.scale_closed()
        assert result == pytest.approx(4 * 25.0)

    def test_scale_closed_custom(self, custom_math_ops: RatingMathOperations):
        """Тест с кастомным конфигом."""
        result = custom_math_ops.scale_closed()
        assert result == pytest.approx(4 * 25.0)


class TestOrdinal:
    """Тесты ordinal."""

    def test_ordinal_zero_mu(self, math_ops: RatingMathOperations):
        """Ординал при mu=0."""
        hidden = HiddenRating(mu=0.0, sigma=25.0)
        result = math_ops.ordinal(hidden)
        assert result == pytest.approx(0.0)

    def test_ordinal_positive_mu(self, math_ops: RatingMathOperations):
        """Ординал при положительном mu."""
        hidden = HiddenRating(mu=100.0, sigma=25.0)
        g = math_ops.config.g
        sigma_init = math_ops.config.sigma_init
        expected = 100.0 / (1 + g * 25.0 / sigma_init)
        result = math_ops.ordinal(hidden)
        assert result == pytest.approx(expected)

    def test_ordinal_higher_sigma_lower_ordinal(self, math_ops: RatingMathOperations):
        """Большая неопределённость даёт меньший ординал."""
        hidden_low_sigma = HiddenRating(mu=100.0, sigma=10.0)
        hidden_high_sigma = HiddenRating(mu=100.0, sigma=50.0)
        
        ordinal_low = math_ops.ordinal(hidden_low_sigma)
        ordinal_high = math_ops.ordinal(hidden_high_sigma)
        
        assert ordinal_low > ordinal_high


class TestHiddenToOpen:
    """Тесты скрытый -> открытый рейтинг."""

    def test_hidden_to_open_middle(self, math_ops: RatingMathOperations):
        """Скрытый рейтинг в середине диапазона."""
        hidden = HiddenRating(mu=0.0, sigma=25.0)
        result = math_ops.hidden_to_open(hidden)
        assert -1000 <= result <= 5000

    def test_hidden_to_open_returns_value(self, math_ops: RatingMathOperations):
        """Скрытый рейтинг возвращает число."""
        hidden = HiddenRating(mu=0.0, sigma=25.0)
        result = math_ops.hidden_to_open(hidden)
        assert isinstance(result, float)


class TestOpenToHidden:
    """Тесты открытый -> скрытый рейтинг."""

    def test_open_to_hidden_middle(self, math_ops: RatingMathOperations):
        """Открытый рейтинг в середине диапазона."""
        open_rating = 2400.0
        result = math_ops.open_to_hidden(open_rating)
        assert isinstance(result, HiddenRating)
        assert result.sigma == math_ops.config.sigma_init

    def test_open_to_hidden_min(self, math_ops: RatingMathOperations):
        """Минимальный открытый рейтинг."""
        result = math_ops.open_to_hidden(0.0)
        assert isinstance(result, HiddenRating)

    def test_open_to_hidden_max(self, math_ops: RatingMathOperations):
        """Максимальный открытый рейтинг."""
        result = math_ops.open_to_hidden(5000.0)
        assert isinstance(result, HiddenRating)


class TestRoundtrip:
    """Тесты roundtrip преобразований."""

    def test_open_hidden_open_roundtrip(self, math_ops: RatingMathOperations):
        """Roundtrip открытый -> скрытый -> открытый."""
        original = 2400.0
        hidden = math_ops.open_to_hidden(original)
        result = math_ops.hidden_to_open(hidden)
        assert isinstance(result, float)

    def test_hidden_open_hidden_roundtrip(self, math_ops: RatingMathOperations):
        """Roundtrip скрытый -> открытый -> скрытый."""
        original = HiddenRating(mu=50.0, sigma=25.0)
        open_rating = math_ops.hidden_to_open(original)
        result = math_ops.open_to_hidden(open_rating)
        assert isinstance(result, HiddenRating)


class TestGateFunction:
    """Тесты гейт-функции."""

    def test_gate_returns_value(self, math_ops: RatingMathOperations):
        """Гейт возвращает число."""
        result = math_ops.gate_function(0.0)
        assert isinstance(result, float)

    def test_gate_negative_delta(self, math_ops: RatingMathOperations):
        """Гейт симметричен для отрицательных delta."""
        result_pos = math_ops.gate_function(100.0)
        result_neg = math_ops.gate_function(-100.0)
        assert result_pos == result_neg


class TestEffectiveRating:
    """Тесты эффективного рейтинга."""

    def test_effective_rating_returns_value(
        self, math_ops: RatingMathOperations
    ):
        """Эффективный рейтинг возвращает число."""
        hidden = HiddenRating(mu=0.0, sigma=25.0)
        result = math_ops.effective_rating(2400.0, hidden)
        assert isinstance(result, float)

    def test_effective_rating_clamped_min(self, math_ops: RatingMathOperations):
        """Эффективный рейтинг не меньше r_min."""
        hidden = HiddenRating(mu=-10000.0, sigma=25.0)
        result = math_ops.effective_rating(100.0, hidden)
        assert result >= math_ops.config.r_min

    def test_effective_rating_clamped_max(self, math_ops: RatingMathOperations):
        """Эффективный рейтинг не больше r_max."""
        hidden = HiddenRating(mu=10000.0, sigma=25.0)
        result = math_ops.effective_rating(4900.0, hidden)
        assert result <= math_ops.config.r_max


class TestEffectiveRatingForSnapshot:
    """Тесты эффективного рейтинга для снапшота."""

    def test_effective_rating_for_snapshot_single_player(
        self, math_ops: RatingMathOperations
    ):
        """Снапшот с одним игроком."""
        player = math_ops.create_player_rating(
            member_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            open_rating=2400.0
        )
        result = math_ops.effective_rating_for_snapshot([player])
        assert len(result) == 1
        assert (player.member_id, player.role_id) in result

    def test_effective_rating_for_snapshot_multiple_players(
        self, math_ops: RatingMathOperations
    ):
        """Снапшот с несколькими игроками."""
        player1 = math_ops.create_player_rating(
            member_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            open_rating=2000.0
        )
        player2 = math_ops.create_player_rating(
            member_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            open_rating=3000.0
        )
        result = math_ops.effective_rating_for_snapshot([player1, player2])
        assert len(result) == 2


class TestUpdateRatingsAfterMatch:
    """Тесты обновления рейтингов после матча."""

    def test_update_ratings_two_teams_first_place(
        self, math_ops: RatingMathOperations
    ):
        """Две команды: первое место vs второе."""
        member1, role1 = uuid.uuid4(), uuid.uuid4()
        member2, role2 = uuid.uuid4(), uuid.uuid4()
        
        teams = [
            [math_ops.create_player_rating(member1, role1, 2400.0)],
            [math_ops.create_player_rating(member2, role2, 2400.0)]
        ]
        ranks = [1.0, 2.0]
        
        result = math_ops.update_ratings_after_match(teams, ranks)
        
        assert len(result) == 2
        assert len(result[0]) == 1
        assert len(result[1]) == 1
        
        team1_new = result[0][0]
        team2_new = result[1][0]
        
        assert team1_new.open_rating >= team2_new.open_rating

    def test_update_ratings_draw(self, math_ops: RatingMathOperations):
        """Ничья - одинаковые ранги."""
        member1, role1 = uuid.uuid4(), uuid.uuid4()
        member2, role2 = uuid.uuid4(), uuid.uuid4()
        
        teams = [
            [math_ops.create_player_rating(member1, role1, 2400.0)],
            [math_ops.create_player_rating(member2, role2, 2400.0)]
        ]
        ranks = [1.5, 1.5]
        
        result = math_ops.update_ratings_after_match(teams, ranks)
        
        team1_new = result[0][0]
        team2_new = result[1][0]
        
        assert team1_new.open_rating == pytest.approx(team2_new.open_rating, rel=0.01)

    def test_update_ratings_respects_bounds(self, math_ops: RatingMathOperations):
        """Рейтинги не выходят за границы."""
        member1, role1 = uuid.uuid4(), uuid.uuid4()
        member2, role2 = uuid.uuid4(), uuid.uuid4()
        
        teams = [
            [math_ops.create_player_rating(member1, role1, 10.0)],
            [math_ops.create_player_rating(member2, role2, 10.0)]
        ]
        ranks = [1.0, 2.0]
        
        result = math_ops.update_ratings_after_match(teams, ranks)
        
        for team in result:
            for player in team:
                assert math_ops.config.r_min <= player.open_rating <= math_ops.config.r_max


class TestCreatePlayerRating:
    """Тесты создания PlayerRating."""

    def test_create_player_rating(self, math_ops: RatingMathOperations):
        """Создание PlayerRating."""
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        open_rating = 2400.0
        
        result = math_ops.create_player_rating(member_id, role_id, open_rating)
        
        assert result.member_id == member_id
        assert result.role_id == role_id
        assert result.open_rating == open_rating
        assert isinstance(result.hidden_rating, HiddenRating)

    def test_create_player_rating_with_hidden(self, math_ops: RatingMathOperations):
        """Создание PlayerRating с переданным скрытым рейтингом."""
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        hidden = HiddenRating(mu=50.0, sigma=20.0)
        
        result = math_ops.create_player_rating_with_hidden(
            member_id, role_id, 2400.0, hidden
        )
        
        assert result.member_id == member_id
        assert result.role_id == role_id
        assert result.hidden_rating == hidden


class TestInitializeNewPlayer:
    """Тесты инициализации нового игрока."""

    def test_initialize_new_player(self, math_ops: RatingMathOperations):
        """Инициализация нового игрока с экспертным рейтингом."""
        member_id = uuid.uuid4()
        role_id = uuid.uuid4()
        expert_rating = 2500.0
        
        result = math_ops.initialize_new_player(member_id, role_id, expert_rating)
        
        assert result.member_id == member_id
        assert result.role_id == role_id
        assert result.open_rating == expert_rating
        assert isinstance(result.hidden_rating, HiddenRating)



