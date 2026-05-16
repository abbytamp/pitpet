from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from booking import views as booking_views
from reports import views as reports_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('packages/', include('packages.urls')),
    path('reports/', include('reports.urls')),
    path('', lambda request: redirect('login')),
    path('user-profile/', include('user_profile.urls')),
    path('groomer/', include('groomer.urls')),
    path('groomer-jobs/', include('groomer_jobs.urls')),
    path('booking/', include(('booking.urls', 'booking'), namespace='booking')),
    # API endpoints
    path('api/slots/', booking_views.api_slots, name='api_slots'),
    path('api/bookings/history/all/', booking_views.staff_booking_history_api, name='staff_booking_history_api'),
    path('api/reports/trend', reports_views.report_trend_api, name='api-trend'),
    path('manager/reports/operational-dashboard-page', reports_views.operational_dashboard_page, name='manager-operational-dashboard-page'),
    path('manager/api/reports/operational-dashboard', reports_views.operational_dashboard, name='manager-api-operational-dashboard'),
    path('manager/api/reports/trend', reports_views.report_trend_api, name='manager-api-trend'),
    path('recommendations/', include('recommendations.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
