import logging
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except Exception:
    def shared_task(*args, **kwargs):
        def decorator(func):
            def wrapper(*fargs, **fkwargs):
                return func(*fargs, **fkwargs)
            wrapper.delay = wrapper
            wrapper.apply_async = wrapper
            return wrapper
        return decorator


@shared_task(name='ratings.recalculate_trust_score', bind=True, max_retries=3, default_retry_delay=60)
def recalculate_trust_score(self, user_id: int) -> dict:
    from users.models import CustomUser
    from .utils import calculate_trust_score

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.warning(f"recalculate_trust_score: User {user_id} not found")
        return {'status': 'error', 'detail': 'User not found', 'user_id': user_id}

    try:
        cache_key = f"trust:{user_id}"
        try:
            cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for user {user_id}: {e}")

        result = calculate_trust_score(user)

        logger.info(
            f"recalculate_trust_score: user={user_id} "
            f"score={result.get('trust_score')} level={result.get('level')}"
        )
        return {
            'status': 'ok',
            'user_id': user_id,
            'trust_score': result.get('trust_score'),
            'level': result.get('level'),
            'cached_at': timezone.now().isoformat(),
        }
    except Exception as exc:
        logger.exception(f"recalculate_trust_score failed for user {user_id}: {exc}")
        try:
            self.retry(exc=exc, countdown=60)
        except Exception:
            return {
                'status': 'error',
                'detail': str(exc),
                'user_id': user_id,
            }


@shared_task(name='ratings.recalculate_all_trust_scores', bind=True)
def recalculate_all_trust_scores(self) -> dict:
    from users.models import CustomUser

    user_ids = list(CustomUser.objects.values_list('id', flat=True))
    total = len(user_ids)
    succeeded = 0
    failed = 0

    logger.info(f"recalculate_all_trust_scores: starting batch for {total} users")

    for user_id in user_ids:
        try:
            recalculate_trust_score(user_id)
            succeeded += 1
        except Exception as e:
            logger.error(f"recalculate_all_trust_scores: failed for user {user_id}: {e}")
            failed += 1

    result = {
        'status': 'completed',
        'total': total,
        'succeeded': succeeded,
        'failed': failed,
        'finished_at': timezone.now().isoformat(),
    }
    logger.info(f"recalculate_all_trust_scores: {result}")
    return result
