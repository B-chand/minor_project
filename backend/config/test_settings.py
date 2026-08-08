"""Test-only Django settings: silences app logging so test output is clean."""
from config.settings import *  # noqa: F401,F403

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {
        "django": {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
        "django.request": {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
    },
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}