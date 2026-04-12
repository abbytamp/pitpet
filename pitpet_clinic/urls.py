from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from booking import views as booking_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('packages/', include('packages.urls')),
    path('', lambda request: redirect('login')),
    path('user-profile/', include('user_profile.urls')),
    path('groomer/', include('groomer.urls')),
    path('groomer-jobs/', include('groomer_jobs.urls')),
    path('booking/', include(('booking.urls', 'booking'), namespace='booking')),
    path('api/slots/', booking_views.api_slots, name='api_slots'),
]
