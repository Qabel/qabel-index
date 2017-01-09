"""
Django settings for qabel_index project.

Generated by 'django-admin startproject' using Django 1.8.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'x$y_sf_kg2e&@+f(^zx=r=))1l$!y#c*nkr1jv72jq4%p)b0q6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'qabel_web_theme',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_prometheus',
    'rest_framework',
    'sendsms',
    'bootstrapform',
    'index_service',
)

MIDDLEWARE_CLASSES = (
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
)

ROOT_URLCONF = 'qabel_index.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'qabel_index.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
if 'TRAVIS' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql_psycopg2',
            'NAME':     'travisdb',  # Must match travis.yml setting
            'USER':     'postgres',
            'PASSWORD': '',
            'HOST':     'localhost',
            'PORT':     '',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'qabel_index',
            'USER': 'qabel',
            'PASSWORD': 'qabel_test',
            'HOST': '127.0.0.1',
            'PORT': '5432',
        }
    }


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/


from django.utils.translation import ugettext_lazy as _

LANGUAGE_CODE = 'de-DE'
LANGUAGES = (
    ('de', _('German')),
    ('en', _('English')),
)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'


# Application configuration

PROMETHEUS_EXPORT_MIGRATIONS = False

REQUIRE_AUTHORIZATION = False
ACCOUNTING_APISECRET = '1234'
ACCOUNTING_URL = 'http://localhost:1234'

# Pending update requests expire after this time interval
PENDING_REQUEST_MAX_AGE = datetime.timedelta(days=3)

SERVER_PRIVATE_KEY = '247a1db50f8747f0e5e1f755c4390a598d36a4c7af202c2234b0613645d9c22a'

SENDSMS_DEFAULT_FROM_PHONE = '+15005550006'

# https://en.wikipedia.org/wiki/List_of_country_calling_codes
SMS_BLACKLISTED_COUNTRIES = (
    # Cuba
    53,
    # Iran
    98,
    # Best korea
    850,
    # Sudan
    249,
    # Syria
    963,

    # France
    33,
        # Guadeloupe (including Saint Barthélemy, Saint Martin)
        590,

        # French Guiana
        594,

        # Martinique
        596,

        # Reunion + Mayotte
        262,

        # Saint Pierre and Miquelon
        508,

        # Wallis and Futuna
        681,

        # French Polynesia
        689,

        # New Caledonia,
        687,

    # Egypt
    20,

    # Armenia
    374,

    # Azerbaijan
    994,

    # Burundi
    257,

    # Ivory coast
    225,

    # Eritrea
    291,

    # Guinea
    224,

    # Guinea-Bissau
    245,

    # Iraq
    964,

    # Yemen
    967,

    # Congo
    242,

    # Lebanon
    961,

    # Liberia
    231,

    # Libya
    218,

    # Myanmar
    95,

    # Sierra Leone
    232,

    # Zimbabwe
    263,

    # Somalia
    252,

    # South Sudan
    211,

    # Tunisia
    216,

    # Ukraine
    380,

    # Belarus
    375,

    # Central African Republic
    236,
)

# Enable shallow verification, i.e. do not confirm via verification mails or SMSes.
FACET_SHALLOW_VERIFICATION = False
