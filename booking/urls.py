from django.urls import path

from . import views

app_name = "booking"

urlpatterns = [
    path("staff/schedule/", views.staff_booking_schedule, name="staff_booking_schedule"),
    path("create/", views.booking_create, name="create"),
    path("success/<int:booking_id>/", views.booking_success, name="success"),
    path("my/", views.my_bookings, name="my_bookings"),
    path("api/options/pet/", views.api_pet_options, name="api_pet_options"),
    path("api/groomers/", views.api_groomers, name="api_groomers"),
    path("api/slots/", views.api_slots, name="api_slots"),
]
