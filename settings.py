# Django settings for hiicart project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

DATABASES = {
    "default": {
        # "postgresql_psycopg2", "mysql", "sqlite3" or "oracle".
        "engine": "django.db.backends.sqlite3",
        # or path to database file if using sqlite3.
        "name": "hiicart_test",
        "user": "",                      # not used with sqlite3.
        "password": "",                  # not used with sqlite3.
        "host": "",                      # set to empty string for localhost. not used with sqlite3.
        "port": "",                      # set to empty string for default. not used with sqlite3.
    }
}

TIME_ZONE = "America/Chicago"
LANGUAGE_CODE = "en-us"

SITE_ID = 1

USE_I18N = True
USE_L10N = True
# some test cases use native timestamps
USE_TZ = False
MEDIA_ROOT = ""
MEDIA_URL = ""

STATIC_ROOT = ""
STATIC_URL = "/static/"
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Make this unique, and don"t share it with anybody.
SECRET_KEY = "h^lx19yc9hrla&amp;1d=4g201@l)heqsi8qsbt7g8y518ld-8e+lg"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
)

ROOT_URLCONF = "urls"

# Python dotted path to the WSGI application used by Django"s runserver.
WSGI_APPLICATION = "hiicart.wsgi.application"

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don"t forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    #"django.contrib.staticfiles",
    "hiicart"
]

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse"
        }
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler"
        },
        "default": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "hiicart": {
            "handlers": ["default"],
            "level": "ERROR",
        },
        "sentry": {
            "handlers": ["default"],
            "level": "ERROR",
        }
    }
}

HIICART_SETTINGS = {}

try:
    from local_settings import *
except ImportError:
    print "%s: HiiCart's test suite will skip many tests without proper gateway configuration." % (
            "\033[01;93mWarning\033[0m"
    )
    pass

