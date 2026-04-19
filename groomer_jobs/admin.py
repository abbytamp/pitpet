from django.contrib import admin
from .models import GroomingServiceForm


@admin.register(GroomingServiceForm)
class GroomingServiceFormAdmin(admin.ModelAdmin):
    list_display = ("id", "booking_item", "created_at")
    search_fields = ("booking_item__id", "booking_item__booking__id", "booking_item__pet__name")