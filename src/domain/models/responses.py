from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class PlayerEffectiveRating(BaseModel):
    member_id: UUID = Field(..., description="Player ID")
    role_id: UUID = Field(..., description="Role ID")
    open_rating: float = Field(..., description="Open rating")
    effective_rating: float = Field(..., description="Effective rating")
    hidden_rating: float = Field(..., description="Projected hidden rating to open system")


class EffectiveRatingResponse(BaseModel):
    draft_id: UUID = Field(..., description="Draft ID from request")
    players: list[PlayerEffectiveRating] = Field(
        ...,
        description="Player effective ratings"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Response creation time"
    )


class PlayerRatingUpdate(BaseModel):
    member_id: UUID = Field(..., description="Player ID")
    role_id: UUID = Field(..., description="Role ID")
    old_open_rating: float = Field(..., description="Open rating before match")
    new_open_rating: float = Field(..., description="Open rating after match")
    open_rating_delta: float = Field(..., description="Open rating change")


class MatchResultResponse(BaseModel):
    match_id: UUID = Field(..., description="Match ID")
    player_updates: list[PlayerRatingUpdate] = Field(
        ...,
        description="Player rating updates"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Response creation time"
    )


class InitializedPlayerResponse(BaseModel):
    member_id: UUID = Field(..., description="Player ID")
    role_id: UUID = Field(..., description="Role ID")
    open_rating: float = Field(..., description="Open rating")
    projected_open: float = Field(..., description="Projected hidden rating")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Response creation time"
    )


class ExpertCorrectionResponse(BaseModel):
    member_id: UUID = Field(..., description="Player ID")
    role_id: UUID = Field(..., description="Role ID")
    open_rating: float = Field(..., description="New open rating")
    delta: float = Field(..., description="Difference between projection and new open rating")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Response creation time"
    )


class ErrorResponse(BaseModel):
    message: str = Field(..., description="Error description")
    error_code: str = Field(default="UNKNOWN_ERROR", description="Error code")
