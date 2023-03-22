"""
Django settings for hvzsite project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import json
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ""
with open(os.path.join(BASE_DIR,"secret.txt"),'r') as f:
    SECRET_KEY = f.readline().strip()

DB_SECRETS = {}
with open(os.path.join(BASE_DIR,"secrets.json"),'r') as f:
    DB_SECRETS = json.load(f)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["192.168.1.200", "localhost", "127.0.0.1", "hvz.henderson.codes"]


# Application definition
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

INSTALLED_APPS = [
    'hvz',
    'django_extensions',
    'rest_framework',
    'rest_framework_api_key',
    'crispy_forms',
    'grappelli',
    'filebrowser',
    'tinymce',
    'captcha',
    'django_registration',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "verify_email.apps.VerifyEmailConfig"
]

SITE_ID = 2


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hvzsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hvzsite.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'hvzdb',
        'USER': DB_SECRETS['user'],
        'PASSWORD': DB_SECRETS['pass'],
        'HOST': DB_SECRETS['host'],
        'PORT': DB_SECRETS['port']
    }
}

STATIC_ROOT = os.path.join(BASE_DIR,"static_root")
MEDIA_ROOT = os.path.join(BASE_DIR,"media")
MEDIA_URL = '/media/'

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTH_USER_MODEL = 'hvz.Person'

CSRF_TRUSTED_ORIGINS = ["http://localhost", "https://hvz.henderson.codes"]

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = DB_SECRETS['email_host']
EMAIL_PORT = DB_SECRETS['email_port']
EMAIL_USE_TLS = DB_SECRETS['email_use_tls']
EMAIL_HOST_USER = DB_SECRETS['email']
EMAIL_HOST_PASSWORD = DB_SECRETS['email_password']

DEFAULT_FROM_EMAIL = DB_SECRETS['email_from']

ACCOUNT_ACTIVATION_DAYS = 7 # One-week activation window

SECURE_REFERRER_POLICY = "no-referrer-when-downgrade"

TINYMCE_DEFAULT_CONFIG = {
    "skin": "oxide-dark",
    "content_css": "dark",
    'height': 500,
    'plugins': 'code',
    'toolbar': 'undo redo | styleselect | bold italic | alignleft aligncenter alignright alignjustify | outdent indent | code',
    'menubar': 'edit view tools'
}

CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'
