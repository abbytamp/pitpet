from django.urls import path

from . import views

app_name = "booking"

urlpatterns = [
    path("history/<int:booking_id>/review/", views.booking_review_create, name="booking_review_create"),
    path("staff/schedule/", views.staff_booking_schedule, name="staff_booking_schedule"),
    path("staff/schedule/<int:booking_id>/", views.staff_booking_detail, name="staff_booking_detail"),
    path("staff/cancel/<int:booking_id>/", views.staff_cancel_booking, name="staff_cancel_booking"),
    path("staff/history/all/", views.staff_booking_history_all, name="staff_booking_history_all"),
    path("staff/history/all/<int:booking_id>/", views.staff_booking_history_detail, name="staff_booking_history_detail"),
    path("staff/api/<int:booking_id>/", views.staff_booking_detail_api, name="staff_booking_detail_api"),
    path("create/", views.booking_create, name="create"),
    path("<int:booking_id>/", views.booking_detail, name="detail"),
    path("success/<int:booking_id>/", views.booking_success, name="success"),
    path("my/", views.my_bookings, name="my_bookings"),
    path("my/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("my/<int:booking_id>/reschedule/", views.reschedule_booking, name="reschedule_booking"),
    path("my/<int:booking_id>/reschedule/api/slots/", views.api_reschedule_slots, name="api_reschedule_slots"),
    path("my/<int:booking_id>/reschedule/submit/", views.reschedule_booking_submit, name="reschedule_booking_submit"),
    path("history/", views.booking_history, name="history"),
    path("history/<int:booking_id>/", views.booking_history_detail, name="history_detail"),
    path("api/options/pet/", views.api_pet_options, name="api_pet_options"),
    path("api/groomers/", views.api_groomers, name="api_groomers"),
    path("api/slots/", views.api_slots, name="api_slots"),
    path("api/bookings/<int:booking_id>/payment-status/", views.api_update_payment_status, name="api_update_payment_status"),
]
