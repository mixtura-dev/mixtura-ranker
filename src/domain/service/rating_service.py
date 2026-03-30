from datetime import datetime
from uuid import UUID

from src.domain.models.rating import (
    RatingSystemConfig,
    PlayerRating,
    HiddenRating,
)
from src.domain.service.rating_math_ops import RatingMathOperations
from src.domain.models.requests import (
    EffectiveRatingRequest,
    MatchResult,
)
from src.domain.models.responses import (
    EffectiveRatingResponse,
    MatchResultResponse,
    PlayerEffectiveRating,
    PlayerRatingUpdate,
)
from src.infra.postgre.repo import HiddenRatingRepository


class RatingService:

    def __init__(self, hidden_rating_repo: HiddenRatingRepository):
        self.hidden_rating_repo = hidden_rating_repo

    def _create_math_ops(self, settings: dict) -> RatingMathOperations:
        config = RatingSystemConfig(**settings)
        return RatingMathOperations(config)

    async def _get_hidden_rating(
        self,
        member_id: UUID,
        role_id: UUID,
        math_ops: RatingMathOperations,
        open_rating: float | None = None
    ) -> HiddenRating:
        if self.hidden_rating_repo is None:
            if open_rating is not None:
                return math_ops.open_to_hidden(open_rating)
            return HiddenRating(mu=0.0, sigma=math_ops.config.sigma_init)

        db_rating = await self.hidden_rating_repo.get_latest(member_id, role_id)
        if db_rating is None:
            if open_rating is not None:
                return math_ops.open_to_hidden(open_rating)
            return HiddenRating(mu=0.0, sigma=math_ops.config.sigma_init)
        return HiddenRating(mu=db_rating.mu, sigma=db_rating.sigma)

    async def calculate_effective_ratings(
        self,
        request: EffectiveRatingRequest
    ) -> EffectiveRatingResponse:
        settings_dict = request.settings.model_dump()
        math_ops = self._create_math_ops(settings_dict)

        player_ratings = []
        for player in request.players:
            for role_id, role_data in player.roles.items():
                hidden_rating = await self._get_hidden_rating(
                    player.member_id,
                    role_id,
                    math_ops,
                    open_rating=float(role_data.open_rating)
                )
                pr = math_ops.create_player_rating_with_hidden(
                    member_id=player.member_id,
                    role_id=role_id,
                    open_rating=float(role_data.open_rating),
                    hidden_rating=hidden_rating
                )
                player_ratings.append(pr)

        effective_map = math_ops.effective_rating_for_snapshot(player_ratings)

        response_players = []
        for pr in player_ratings:
            key = (pr.member_id, pr.role_id)
            eff_rating = effective_map[key]
            projected = math_ops.hidden_to_open(pr.hidden_rating)

            response_players.append(PlayerEffectiveRating(
                member_id=pr.member_id,
                role_id=pr.role_id,
                open_rating=pr.open_rating,
                effective_rating=eff_rating,
                hidden_rating=projected
            ))

        return EffectiveRatingResponse(
            draft_id=request.draft_id,
            players=response_players,
            created_at=datetime.now()
        )

    async def process_match_result(
        self,
        request: MatchResult
    ) -> MatchResultResponse:
        settings_dict = request.settings.model_dump()
        math_ops = self._create_math_ops(settings_dict)

        player_map = {p.member_id: p for p in request.players}

        teams: list[list[PlayerRating]] = []
        for team in request.teams:
            team_ratings = []
            for member_id in team.player_ids:
                if member_id not in player_map:
                    raise ValueError(f"Player {member_id} not found in match players")

                player = player_map[member_id]
                hidden_rating = await self._get_hidden_rating(
                    player.member_id, player.role_id, math_ops,
                    open_rating=float(player.open_rating)
                )
                pr = math_ops.create_player_rating_with_hidden(
                    member_id=player.member_id,
                    role_id=player.role_id,
                    open_rating=float(player.open_rating),
                    hidden_rating=hidden_rating
                )
                team_ratings.append(pr)
            teams.append(team_ratings)

        updated_teams = math_ops.update_ratings_after_match(
            teams,
            [float(r) for r in request.team_ranks]
        )

        player_updates = []
        for old_team, new_team in zip(teams, updated_teams):
            for old_pr, new_pr in zip(old_team, new_team):
                existing_rating = await self.hidden_rating_repo.get_latest(
                    new_pr.member_id,
                    new_pr.role_id
                ) if self.hidden_rating_repo else None

                if existing_rating is None and self.hidden_rating_repo is not None:
                    await self.hidden_rating_repo.create(
                        member_id=new_pr.member_id,
                        role_id=new_pr.role_id,
                        mu=new_pr.hidden_rating.mu,
                        sigma=new_pr.hidden_rating.sigma
                    )

                player_updates.append(PlayerRatingUpdate(
                    member_id=new_pr.member_id,
                    role_id=new_pr.role_id,
                    old_open_rating=old_pr.open_rating,
                    new_open_rating=new_pr.open_rating,
                    open_rating_delta=new_pr.open_rating - old_pr.open_rating
                ))

        return MatchResultResponse(
            match_id=request.match_id,
            player_updates=player_updates,
            created_at=request.match_time
        )
