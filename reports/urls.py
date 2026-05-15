from django.urls import path
from . import views

urlpatterns = [
    path(
        "trend",
        views.report_trend,
        name="report-trend"
    ),
]