"""
URL configuration for ManageILIA project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path,include
from django.contrib.auth.views import LogoutView
from accounts.views import RegistrationView, LoginView
from ILIA.views import HomeView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page = "login"), name="logout"),
    path("register/", RegistrationView.as_view(), name="register"),
    path("accounts/", include('accounts.urls')),
    path("events/", include('events.urls')),
    path('timetable/', include('timetable.urls')),
    path("reservations/", include('reservations.urls')),
    path('projects/', include(('projects.urls', 'projects'), namespace='projects')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers (templates in ManageILIA/templates/)
handler400 = 'ManageILIA.error_views.error_400'
handler403 = 'ManageILIA.error_views.error_403'
handler404 = 'ManageILIA.error_views.error_404'
handler500 = 'ManageILIA.error_views.error_500'
