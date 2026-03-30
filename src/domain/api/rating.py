"""
RabbitMQ роутер для сервиса рейтингов.

Обработчики входящих запросов:
- rating.effective.calculate - оценка эффективных рейтингов
- rating.match.process - обработка результатов матча
"""

from faststream.rabbit import RabbitRouter

from src.domain.models.common import ResponseMessage
from src.domain.models.requests import (
    EffectiveRatingRequest,
    MatchResult,
)
from src.domain.models.responses import (
    EffectiveRatingResponse,
    MatchResultResponse,
    ErrorResponse,
)
from src.dependency import RatingServiceDependency

router = RabbitRouter()


@router.subscriber("rating.effective.calculate")
async def calculate_effective_ratings(
    request: EffectiveRatingRequest,
    rating_service: RatingServiceDependency,
) -> ResponseMessage[EffectiveRatingResponse]:
    try:
        response = await rating_service.calculate_effective_ratings(request)
        return ResponseMessage(status=200, message=response)
    except Exception as e:
        return ResponseMessage(
            status=500,
            message=ErrorResponse(message=str(e), error_code="EFFECTIVE_RATING_ERROR")
        )


@router.subscriber("rating.match.process")
async def process_match_result(
    request: MatchResult,
    rating_service: RatingServiceDependency,
) -> ResponseMessage[MatchResultResponse]:
    try:
        response = await rating_service.process_match_result(request)
        return ResponseMessage(status=200, message=response)
    except Exception as e:
        return ResponseMessage(
            status=500,
            message=ErrorResponse(message=str(e), error_code="MATCH_PROCESS_ERROR")
        )
