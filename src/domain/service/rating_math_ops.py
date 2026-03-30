import math
from typing import Sequence
from uuid import UUID

from openskill.models import ThurstoneMostellerFull, ThurstoneMostellerFullRating

from src.domain.models.rating import HiddenRating, PlayerRating, RatingSystemConfig


class RatingMathOperations:

    def __init__(self, config: RatingSystemConfig):
        self.config = config
        self.model = ThurstoneMostellerFull()

    def _sigmoid(self, x: float) -> float:
        return 1 / (1 + math.exp(-x))

    def _logit(self, p: float) -> float:
        p = max(1e-10, min(1 - 1e-10, p))
        return math.log(p / (1 - p))

    def _to_open_skill_players(self, hidden_ratings: Sequence[HiddenRating]) -> list[ThurstoneMostellerFullRating]:
        return [self.model.create_rating([hr.mu, hr.sigma]) for hr in hidden_ratings]

    def _from_open_skill_players(self, players: Sequence[ThurstoneMostellerFullRating]) -> list[HiddenRating]:
        return [HiddenRating(mu=p.mu, sigma=p.sigma) for p in players]

    def delta_translate(self) -> float:
        return (self.config.r_min + self.config.r_max) / 2 - self.config.r_avg

    def scale_closed(self) -> float:
        return 4 * self.config.sigma_init

    def ordinal(self, hidden: HiddenRating) -> float:
        return hidden.mu / (1 + self.config.g * hidden.sigma / self.config.sigma_init)

    def hidden_to_open(self, hidden: HiddenRating) -> float:
        o = self.ordinal(hidden)
        s_closed = self.scale_closed()
        delta_translate = self.delta_translate()

        return (
            self.config.r_min
            + self.config.delta_open * self._sigmoid(o / s_closed)
            - delta_translate
        )

    def open_to_hidden(self, open_rating: float) -> HiddenRating:
        s_closed = self.scale_closed()
        delta_translate = self.delta_translate()

        adjusted_rating = open_rating + delta_translate
        numerator = adjusted_rating - self.config.r_min
        denominator = self.config.r_max - adjusted_rating

        if denominator <= 0:
            denominator = 1e-10
        if numerator <= 0:
            numerator = 1e-10

        mu = s_closed * self._logit(numerator / denominator)
        return HiddenRating(mu=mu, sigma=self.config.sigma_init)

    def gate_function(self, delta: float) -> float:
        d = self.config.d
        delta_open = self.config.delta_open
        return self._sigmoid(2 * d * abs(delta) / delta_open - d)

    def effective_rating(self, open_rating: float, hidden: HiddenRating) -> float:
        projected_open = self.hidden_to_open(hidden)
        delta = projected_open - open_rating

        gate = self.gate_function(delta)
        delta_eff = gate * delta

        eff = open_rating + delta_eff
        return max(self.config.r_min, min(self.config.r_max, eff))

    def effective_rating_for_snapshot(
        self,
        player_ratings: Sequence[PlayerRating]
    ) -> dict[tuple[UUID, UUID], float]:
        return {
            (pr.member_id, pr.role_id): self.effective_rating(pr.open_rating, pr.hidden_rating)
            for pr in player_ratings
        }

    def update_ratings_after_match(
        self,
        teams: list[list[PlayerRating]],
        ranks: list[float]
    ) -> list[list[PlayerRating]]:
        openskill_teams = [
            [self._to_open_skill_players([pr.hidden_rating])[0] for pr in team]
            for team in teams
        ]

        updated_players = self.model.rate(
            openskill_teams,
            ranks=ranks
        )

        result = []
        for team_idx, team in enumerate(teams):
            new_team = []
            for player_idx, pr in enumerate(team):
                new_hidden = self._from_open_skill_players([updated_players[team_idx][player_idx]])[0]

                old_projected = self.hidden_to_open(pr.hidden_rating)
                new_projected = self.hidden_to_open(new_hidden)

                delta_old = old_projected - pr.open_rating
                delta_match = new_projected - old_projected

                sign_delta_match = 1 if delta_match >= 0 else -1
                correction = self._sigmoid(
                    2 * delta_old * sign_delta_match / self.config.delta_open
                )
                rating_change = 2 * delta_match * correction

                new_open = pr.open_rating + rating_change
                new_open = max(self.config.r_min, min(self.config.r_max, new_open))

                new_team.append(PlayerRating(
                    member_id=pr.member_id,
                    role_id=pr.role_id,
                    open_rating=new_open,
                    hidden_rating=new_hidden
                ))
            result.append(new_team)

        return result

    def create_player_rating(
        self,
        member_id: UUID,
        role_id: UUID,
        open_rating: float
    ) -> PlayerRating:
        hidden = self.open_to_hidden(open_rating)
        return PlayerRating(
            member_id=member_id,
            role_id=role_id,
            open_rating=open_rating,
            hidden_rating=hidden
        )

    def create_player_rating_with_hidden(
        self,
        member_id: UUID,
        role_id: UUID,
        open_rating: float,
        hidden_rating: HiddenRating
    ) -> PlayerRating:
        return PlayerRating(
            member_id=member_id,
            role_id=role_id,
            open_rating=open_rating,
            hidden_rating=hidden_rating
        )

    def initialize_new_player(
        self,
        member_id: UUID,
        role_id: UUID,
        expert_rating: float
    ) -> PlayerRating:
        hidden = self.open_to_hidden(expert_rating)
        return PlayerRating(
            member_id=member_id,
            role_id=role_id,
            open_rating=expert_rating,
            hidden_rating=hidden
        )
