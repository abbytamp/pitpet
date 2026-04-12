from django.urls import path
from .views import *

# urlpatterns = [
#     path('', views.daily_job_list, name='daily_job_list'),
# ]

app_name = "groomer_jobs"

urlpatterns = [
    path("dashboard/", daily_job_list, name="daily_job_list"),
    path("bookings/<int:booking_id>/", job_detail, name="job_detail"),
    path("bookings/<int:booking_id>/status/", update_booking_status, name="update_booking_status"),
]