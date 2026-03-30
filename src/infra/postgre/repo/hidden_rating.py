import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.postgre.models import PlayerRoleHiddenRating


class HiddenRatingRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest(
        self,
        member_id: uuid.UUID,
        role_id: uuid.UUID
    ) -> Optional[PlayerRoleHiddenRating]:
        stmt = (
            select(PlayerRoleHiddenRating)
            .where(PlayerRoleHiddenRating.member_id == member_id)
            .where(PlayerRoleHiddenRating.role_id == role_id)
            .order_by(PlayerRoleHiddenRating.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        member_id: uuid.UUID,
        role_id: uuid.UUID,
        mu: float,
        sigma: float,
        created_at: Optional[datetime] = None
    ) -> PlayerRoleHiddenRating:
        if created_at is None:
            created_at = datetime.now()

        rating = PlayerRoleHiddenRating(
            member_id=member_id,
            role_id=role_id,
            mu=mu,
            sigma=sigma,
            created_at=created_at
        )
        self.session.add(rating)
        await self.session.flush()
        return rating
