import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="ratings.recalculate_trust_score",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def recalculate_trust_score(self, user_id: int) -> dict:
    from users.models import CustomUser
    from .utils import calculate_trust_score

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.warning(
            "recalculate_trust_score: User %s not found",
            user_id,
        )
        return {
            "status": "error",
            "detail": "User not found",
            "user_id": user_id,
        }

    try:
        cache_key = f"trust:{user_id}"

        try:
            cache.delete(cache_key)
        except Exception as exc:
            logger.warning(
                "Failed to invalidate cache for user %s: %s",
                user_id,
                exc,
            )

        result = calculate_trust_score(user)

        logger.info(
            "recalculate_trust_score: user=%s score=%s level=%s",
            user_id,
            result.get("trust_score"),
            result.get("level"),
        )

        return {
            "status": "ok",
            "user_id": user_id,
            "trust_score": result.get("trust_score"),
            "level": result.get("level"),
            "cached_at": timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.exception(
            "recalculate_trust_score failed for user %s: %s",
            user_id,
            exc,
        )

        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            return {
                "status": "error",
                "detail": str(exc),
                "user_id": user_id,
            }


@shared_task(
    name="ratings.recalculate_all_trust_scores",
    bind=True,
)
def recalculate_all_trust_scores(self) -> dict:
    from users.models import CustomUser

    user_ids = list(
        CustomUser.objects.values_list("id", flat=True)
    )

    total = len(user_ids)
    succeeded = 0
    failed = 0

    logger.info(
        "recalculate_all_trust_scores: starting batch for %s users",
        total,
    )

    for user_id in user_ids:
        try:
            # Appel direct de la fonction Celery pour éviter
            # de créer une nouvelle tâche pour chaque utilisateur.
            recalculate_trust_score.run(user_id)

            succeeded += 1

        except Exception as exc:
            logger.error(
                "recalculate_all_trust_scores: failed for user %s: %s",
                user_id,
                exc,
            )
            failed += 1

    result = {
        "status": "completed",
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "finished_at": timezone.now().isoformat(),
    }

    logger.info(
        "recalculate_all_trust_scores: %s",
        result,
    )

    return result