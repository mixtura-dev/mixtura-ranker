"""
Точка входа FastStream приложения.
"""

from contextlib import asynccontextmanager
from faststream import ContextRepo, FastStream
from faststream.rabbit import RabbitBroker

from src.env_config import env
from src.infra.postgre.engine import DatabaseSessionManager
from src.domain.api.rating import router


@asynccontextmanager
async def lifespan(context: ContextRepo):
    """Управление временем жизни приложения."""
    session_manager = DatabaseSessionManager(env.postgres.url)

    context.set_global("session_manager", session_manager)

    yield

    await session_manager.close()


broker = RabbitBroker(env.rabbit.url)
broker.include_router(router)

app = FastStream(broker, lifespan=lifespan)
