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

SECRET_SETTINGS = {}
with open(os.path.join(BASE_DIR,"secrets.json"),'r') as f:
    SECRET_SETTINGS = json.load(f)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["192.168.1.200", "localhost", "127.0.0.1", "hvz.henderson.codes",  "137.184.204.67"]


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
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
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
                'hvz.contextprocessors.notification_context_processor.get_notifications',
                'hvz.contextprocessors.announcement_context_processor.get_announcements',
                'hvz.contextprocessors.banned_context_processor.is_player_banned'
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
        'USER': SECRET_SETTINGS['user'],
        'PASSWORD': SECRET_SETTINGS['pass'],
        'HOST': SECRET_SETTINGS['host'],
        'PORT': SECRET_SETTINGS['port']
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

STATIC_URL = 'static_root/'

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
    BASE_DIR / "staticfiles"
]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = SECRET_SETTINGS['email_host']
EMAIL_PORT = SECRET_SETTINGS['email_port']
EMAIL_USE_TLS = SECRET_SETTINGS['email_use_tls']
EMAIL_HOST_USER = SECRET_SETTINGS['email']
EMAIL_HOST_PASSWORD = SECRET_SETTINGS['email_password']

DEFAULT_FROM_EMAIL = SECRET_SETTINGS['email_from']

if 'discord_report_webhook_url' in SECRET_SETTINGS:
    DISCORD_REPORT_WEBHOOK_URL = SECRET_SETTINGS['discord_report_webhook_url']
else:
    DISCORD_REPORT_WEBHOOK_URL = None

ACCOUNT_ACTIVATION_DAYS = 7 # One-week activation window

SECURE_REFERRER_POLICY = "no-referrer-when-downgrade"

TINYMCE_DEFAULT_CONFIG = {
    "skin": "oxide-dark",
    "content_css": "dark",
    'height': 500,
    'plugins': 'code,textcolor,paste,lists,advlist,link',
    'toolbar': 'undo redo | link | styleselect | forecolor backcolor bold italic | alignleft aligncenter alignright alignjustify | bullist numlist | outdent indent | code',
    'menubar': 'edit view tools'
}

CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'
CAPTCHA_LENGTH = 6
CAPTCHA_NOISE_FUNCTIONS = ('captcha.helpers.noise_dots',)
