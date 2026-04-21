from django.urls import path
from .views import *

app_name = "groomer_jobs"

urlpatterns = [
    path("dashboard/", daily_job_list, name="daily_job_list"),
    path("bookings/<int:booking_id>/", job_detail, name="job_detail"),
    path("bookings/<int:booking_id>/status/", update_booking_status, name="update_booking_status"),

    path(
        "bookings/<int:booking_id>/items/<int:booking_item_id>/service-form/",
        grooming_service_form,
        name="grooming_service_form",
    ),
    path(
        "bookings/<int:booking_id>/items/<int:booking_item_id>/service-form/submit/",
        submit_grooming_service_form,
        name="submit_grooming_service_form",
    ),
]