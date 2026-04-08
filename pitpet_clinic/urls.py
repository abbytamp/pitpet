from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('packages/', include('packages.urls')),
    path('', lambda request: redirect('login')),
    path('user-profile/', include('user_profile.urls')),
    path('groomer/', include('groomer.urls')),
    path('groomer-jobs/', include('groomer_jobs.urls')),
]
