import os
from pathlib import Path
from decouple import config

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me")

# Only this email may access /admin/, even if another account is
# accidentally granted is_staff/is_superuser. Override via the
# ADMIN_ALLOWED_EMAIL env var if it ever needs to change.
ADMIN_ALLOWED_EMAIL = config("ADMIN_ALLOWED_EMAIL", default="majjihboy@gmail.com")
DEBUG = config("DEBUG", default=False, cast=bool)

if not DEBUG and SECRET_KEY == "django-insecure-change-me":
    raise ImproperlyConfigured(
        "SECRET_KEY is still set to the insecure default while DEBUG=False. "
        "Set a real SECRET_KEY environment variable before deploying."
    )

# Vercel sets VERCEL=1 in the function's environment automatically. Used
# below to skip filesystem operations that aren't safe in that environment
# (only /tmp is writable there, and it doesn't persist between invocations).
IS_VERCEL = config("VERCEL", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

# Vercel exposes the project's current production domain (whichever custom
# domain is attached, or the *.vercel.app one if none is) as this system
# env var automatically -- no dashboard step needed. Without this, adding
# a custom domain in Vercel gives a 400 Bad Request from Django's own
# ALLOWED_HOSTS check the moment traffic arrives on that new host, even
# though the *.vercel.app domain keeps working fine.
_vercel_production_host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
if _vercel_production_host and _vercel_production_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_vercel_production_host)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "import_export",
    "django_ratelimit",
    "axes",
    "predictions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",  # must stay last
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",  # must stay first
    "django.contrib.auth.backends.ModelBackend",
]

# django-axes: lock out a specific *username* after repeated failed
# logins, on top of the existing per-IP rate limiting in views.py (which
# only slows down one IP hammering many accounts, not a distributed
# attempt against one account).
AXES_FAILURE_LIMIT = 5
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_COOLOFF_TIME = 1  # hours
AXES_RESET_ON_SUCCESS = True

ROOT_URLCONF = "matchday.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "matchday.wsgi.application"

# Database
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=0,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
# Matters more than it looks: the home view's "today" filter is computed
# with timezone.now() against this setting. Leaving it as UTC means a
# match with a kickoff "today" by your local clock can silently fall
# outside the query window whenever it's currently between midnight and
# your UTC offset (e.g. 00:00-03:00 in Nairobi, UTC+3). Set TIME_ZONE=
# Africa/Nairobi in your .env (and Vercel env vars in production) so
# "today" matches your actual calendar day.
TIME_ZONE = config("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# Static
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "predictions" / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "home"
LOGIN_URL = "login"

# Security
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default=",".join(f"https://{h}" for h in ALLOWED_HOSTS if h not in ("127.0.0.1", "localhost")),
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Sessions
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1209600

# Redis cache. In production (Vercel or anywhere else) set REDIS_URL to a
# real managed Redis instance (e.g. Upstash via the Vercel Marketplace) --
# there is no local Redis process available inside a Vercel serverless
# function, and pointing at 127.0.0.1 there would just raise ConnectionError
# on every cache access. If REDIS_URL isn't set at all, fall back to an
# in-process LocMemCache so local dev / misconfigured deploys degrade
# gracefully instead of 500ing.
REDIS_URL = config("REDIS_URL", default="")

if REDIS_URL:
    _connection_pool_kwargs = {
        "protocol": 2,  # This forces Redis to skip the HELLO command
    }
    if REDIS_URL.startswith("rediss://"):
        # Most managed providers (Upstash included) terminate TLS with
        # a cert that Python's default verification is picky about from
        # inside serverless runtimes. Relaxing verification here is the
        # commonly recommended workaround for django-redis + rediss://.
        # NOTE: merge into the same dict rather than passing a second
        # "CONNECTION_POOL_KWARGS" key, which would silently clobber the
        # "protocol" setting above instead of combining with it.
        _connection_pool_kwargs["ssl_cert_reqs"] = None

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": _connection_pool_kwargs,
                # Treat a Redis outage/misconfiguration as a cache miss
                # rather than a 500 -- pages still render, just uncached.
                "IGNORE_EXCEPTIONS": True,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# Email
# Zero-cost transactional email: Brevo (https://brevo.com) gives 300
# emails/day free forever, no card required -- plenty for password resets
# on a project this size. Setup:
#   1. Sign up at brevo.com (free plan)
#   2. Settings -> SMTP & API -> SMTP -> generate an SMTP key
#   3. Set these env vars in production (Vercel dashboard -> Environment
#      Variables):
#        EMAIL_HOST=smtp-relay.brevo.com
#        EMAIL_HOST_USER=<your Brevo account email>
#        EMAIL_HOST_PASSWORD=<the SMTP key from step 2, not your account password>
#        DEFAULT_FROM_EMAIL=Matchday Pro <no-reply@yourdomain.com>
#
# Any other free SMTP provider (Resend, Mailjet, etc.) works the same way
# -- just point EMAIL_HOST at their relay. With EMAIL_HOST unset (e.g.
# local dev with no provider configured yet), emails print to the console
# instead of raising a connection error.
EMAIL_HOST = config("EMAIL_HOST", default="")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="Matchday Pro <majjihboy@gmail.com>"
)

# WhatsApp
# VIP access is arranged manually over WhatsApp, not through a payment
# processor. Set WHATSAPP_NUMBER to your number in international format
# with no leading + or spaces (e.g. 254712345678 for a Kenyan number) so
# the "Chat on WhatsApp" button on the Upgrade page builds a valid
# wa.me link. Left blank, that button is simply hidden.
WHATSAPP_NUMBER = config("WHATSAPP_NUMBER", default="")

# Cron
# Verifies that requests to /cron/cleanup-matches/ actually came from
# Vercel's own Cron Jobs feature, not a random public request. Vercel
# automatically sends this value as "Authorization: Bearer <CRON_SECRET>"
# when it invokes a scheduled job, as long as CRON_SECRET is set as an
# environment variable in the Vercel project settings.
CRON_SECRET = config("CRON_SECRET", default="")

# Logging
# File logging is only safe on a filesystem that's actually writable and
# persistent. Vercel functions only expose a writable /tmp that doesn't
# survive between invocations, so on Vercel we log to stdout only (visible
# in the Vercel dashboard's function logs) and skip the file handler
# entirely rather than crashing on LOGS_DIR.mkdir().
LOG_HANDLERS = {
    "console": {
        "level": "DEBUG" if DEBUG else "INFO",
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}

if not IS_VERCEL:
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
    LOG_HANDLERS["file"] = {
        "level": "ERROR",
        "class": "logging.FileHandler",
        "filename": LOGS_DIR / "django.log",
        "formatter": "verbose",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": LOG_HANDLERS,
    "loggers": {
        "django": {
            "handlers": list(LOG_HANDLERS.keys()),
            "level": "ERROR",
            "propagate": True,
        },
        # Catches logger.exception()/logger.warning() calls added in
        # views.py (e.g. VIP code redemption errors, unknown-customer warnings)
        # that previously had nowhere to go.
        "predictions": {
            "handlers": list(LOG_HANDLERS.keys()),
            "level": "INFO",
            "propagate": False,
        },
    },
}
