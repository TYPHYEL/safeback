import logging
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.core.cache import cache

logger = logging.getLogger(__name__)

WEIGHTS = {
    'ratings': 0.40,
    'safe_trips': 0.30,
    'account_age': 0.15,
    'verified': 0.15,
}

MAX_ACCOUNT_DAYS = 180
SCALE_MIN = 0.0
SCALE_MAX = 5.0


def _get_level(trust_score: float) -> str:
    if trust_score >= 4.5:
        return 'Excellent'
    if trust_score >= 4.0:
        return 'Très bon'
    if trust_score >= 3.5:
        return 'Bon'
    if trust_score >= 3.0:
        return 'Moyen'
    if trust_score >= 2.0:
        return 'Faible'
    return 'Très faible'


def calculate_trust_score(user) -> dict:
    cache_key = f"trust:{user.id}"
    cached = cache.get(cache_key)
    if cached and isinstance(cached, dict):
        return cached

    from ratings.models import Rating
    from trips.models import Trip
    from sos.models import Incident
    from documents.models import DriverDocument
    from users.models import DriverProfile

    now = timezone.now()

    ratings_received = Rating.objects.filter(ratee=user)
    ratings_count = ratings_received.count()
    ratings_avg = float(ratings_received.aggregate(models.Avg('score'))['score__avg'] or 3.0)
    ratings_pct = min(1.0, max(0.0, ratings_avg / SCALE_MAX))

    trips_as_driver = Trip.objects.filter(driver=user, status='completed')
    trips_as_passenger = Trip.objects.filter(passengers=user, status='completed')
    all_completed_trips = trips_as_driver | trips_as_passenger
    total_completed = all_completed_trips.count()

    incident_user_ids = set(
        Incident.objects.filter(user=user, status__in=('open', 'resolved'))
        .values_list('user_id', flat=True)
    )
    incident_trips_count = 0
    if user.id in incident_user_ids:
        incident_trips_count = max(1, min(total_completed, Incident.objects.filter(user=user).count()))

    incident_free_trips = max(0, total_completed - incident_trips_count)
    if total_completed == 0:
        safe_trips_pct = 0.5
    else:
        safe_trips_pct = incident_free_trips / total_completed

    account_td = now - user.date_joined
    account_days = max(0, int(account_td.total_seconds() // 86400))
    account_age_pct = min(1.0, account_days / MAX_ACCOUNT_DAYS) if MAX_ACCOUNT_DAYS > 0 else 1.0

    verified = False
    try:
        driver_profile = DriverProfile.objects.get(user=user)
        if driver_profile.verified:
            verified = True
    except DriverProfile.DoesNotExist:
        driver_profile = None

    if not verified:
        required_docs = {'license', 'cni', 'vehicle'}
        uploaded_docs = set()
        if driver_profile and driver_profile.documents:
            uploaded_docs = set(driver_profile.documents.keys())
        docs_approved = DriverDocument.objects.filter(
            driver=user,
            status='approved',
        ).values_list('doc_type', flat=True)
        uploaded_docs.update(docs_approved)
        if required_docs.issubset(uploaded_docs):
            verified = True

    verified_pct = 1.0 if verified else 0.0

    trust_score = (
        WEIGHTS['ratings'] * ratings_pct * SCALE_MAX
        + WEIGHTS['safe_trips'] * safe_trips_pct * SCALE_MAX
        + WEIGHTS['account_age'] * account_age_pct * SCALE_MAX
        + WEIGHTS['verified'] * verified_pct * SCALE_MAX
    )
    trust_score = round(min(SCALE_MAX, max(SCALE_MIN, trust_score)), 2)

    level = _get_level(trust_score)

    result = {
        'trust_score': trust_score,
        'level': level,
        'breakdown': {
            'ratings_avg': round(ratings_avg, 2),
            'safe_trips_pct': round(safe_trips_pct * 100, 2),
            'account_age_pct': round(account_age_pct * 100, 2),
            'verified_pct': round(verified_pct * 100, 2),
            'weights': dict(WEIGHTS),
            'ratings_count': ratings_count,
            'verified': verified,
            'account_days': account_days,
            'incident_free_trips': incident_free_trips,
        },
        'ratings_count': ratings_count,
        'verified': verified,
        'account_days': account_days,
        'incident_free_trips': incident_free_trips,
    }

    try:
        cache.set(cache_key, result, timeout=60 * 30)
    except Exception as e:
        logger.warning(f"Failed to cache trust score for user {user.id}: {e}")

    return result
