from django.urls import path
from . import views

urlpatterns = [
    path(
        "operational-dashboard",
        views.operational_dashboard,
        name="operational-dashboard"
    ),
    path(
        "operational-dashboard-page",
        views.operational_dashboard_page,
        name="operational-dashboard-page"
    ),
    path(
        "trend",
        views.report_trend,
        name="report-trend"
    ),
    # API endpoint matching PBI: /reports/api/trend
    path(
        "api/trend",
        views.report_trend_api,
        name="report-trend-api"
    ),
]