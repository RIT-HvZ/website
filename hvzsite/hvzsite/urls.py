"""hvzsite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import re_path,include
from hvz.forms import HVZRegistrationForm
from django_registration.backends.activation.views import RegistrationView
from filebrowser.sites import site
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    re_path(r"", include('hvz.urls')),
    re_path(r'admin/filebrowser/?', site.urls),
    re_path(r'grappelli/?', include('grappelli.urls')), # grappelli URLS 
    re_path(r'admin/?', admin.site.urls),
    re_path(r'tinymce/?', include('tinymce.urls')),
    re_path(r'accounts/register/?',
        RegistrationView.as_view(
            form_class=HVZRegistrationForm
        ),
        name='django_registration_register',
    ),
    re_path(r'accounts/?', include('django_registration.backends.activation.urls')),
    re_path(r'accounts/?', include('django.contrib.auth.urls')),
    re_path(r'verification/?', include('verify_email.urls')),
    re_path(r'captcha/?', include('captcha.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
