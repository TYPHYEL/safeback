import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "safetaxi_backend.settings",
)


app = Celery("safetaxi_backend")


# ============================================================
# CONFIGURATION DJANGO
# ============================================================

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)


# ============================================================
# IMPORT EXPLICITE DES TÂCHES
# ============================================================
#
# L'autodiscovery ne fonctionne pas correctement dans notre
# configuration actuelle. On importe donc explicitement les
# modules contenant les tâches Celery.
#
# Cela garantit leur enregistrement au démarrage de Celery.
#

app.conf.imports = (
    "ratings.tasks",
    "sos.tasks",
)


# ============================================================
# TÂCHES PLANIFIÉES CELERY BEAT
# ============================================================

app.conf.beat_schedule = {

    # Recalcul des scores de confiance toutes les heures
    "recalculate_all_trust_scores_every_hour": {
        "task": "ratings.recalculate_all_trust_scores",
        "schedule": crontab(
            minute=0,
            hour="*",
        ),
    },

    # Nettoyage des alertes SOS expirées toutes les 30 minutes
    "cleanup_expired_alerts_every_30_min": {
        "task": "sos.cleanup_expired_alerts",
        "schedule": crontab(
            minute="*/30",
        ),
    },
}


# ============================================================
# FUSEAU HORAIRE
# ============================================================

app.conf.timezone = "Africa/Douala"