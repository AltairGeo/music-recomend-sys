from fastapi import Request
from src.core.recommendation.services import RecommendationService


def get_recommendation_service(request: Request) -> RecommendationService:
    service = getattr(request.app.state, "rec_service", None)

    if service is None:
        raise RuntimeError("RecommendationService not initialized")

    return service
