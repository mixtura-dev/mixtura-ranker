from dataclasses import dataclass
from uuid import UUID


@dataclass
class HiddenRating:
    mu: float
    sigma: float


@dataclass
class RatingSystemConfig:
    r_min: float = 0.0
    r_max: float = 5000.0
    r_avg: float = 2400.0
    g: float = 0.5
    sigma_init: float = 25.0
    d: float = 4.0

    @property
    def delta_open(self) -> float:
        return self.r_max - self.r_min


@dataclass
class PlayerRating:
    member_id: UUID
    role_id: UUID
    open_rating: float
    hidden_rating: HiddenRating
