from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class PlayerRole(BaseModel):
    priority: int = Field(..., description="Role priority (0 = minimal)")
    open_rating: int = Field(..., description="Open rating for this role")


class Player(BaseModel):
    member_id: UUID = Field(..., description="Player ID")
    roles: dict[UUID, PlayerRole] = Field(
        ...,
        description="Player roles with priorities and open ratings"
    )


class RatingSettings(BaseModel):
    r_min: float = Field(default=0.0, description="Minimum open rating")
    r_max: float = Field(default=5000.0, description="Maximum open rating")
    r_avg: float = Field(default=2400.0, description="Expected open rating")
    g: float = Field(default=0.5, description="Player rating gravity")
    sigma_init: float = Field(default=25.0, description="Initial uncertainty")
    d: float = Field(default=4.0, description="Gate function steepness")


class EffectiveRatingRequest(BaseModel):
    draft_id: UUID = Field(..., description="Draft/match ID")
    players: list[Player] = Field(..., description="List of players")
    settings: RatingSettings = Field(
        default_factory=RatingSettings,
        description="Rating system settings"
    )


class MatchTeam(BaseModel):
    team_id: UUID = Field(..., description="Team ID")
    player_ids: list[UUID] = Field(..., description="Player IDs in team")


class MatchPlayer(BaseModel):
    member_id: UUID = Field(..., description="Player ID")
    role_id: UUID = Field(..., description="Role ID")
    open_rating: float = Field(..., description="Open rating at match time")


class MatchResult(BaseModel):
    match_id: UUID = Field(..., description="Match ID")
    match_time: datetime = Field(..., description="Match time")
    teams: list[MatchTeam] = Field(..., description="Teams in match")
    team_ranks: list[float] = Field(
        ...,
        description="Team ranks (1 = first place, 2 = second, etc.)"
    )
    players: list[MatchPlayer] = Field(
        ...,
        description="Match participants with roles and open ratings"
    )
    settings: RatingSettings = Field(
        default_factory=RatingSettings,
        description="Rating system settings"
    )
