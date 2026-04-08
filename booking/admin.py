from django.contrib import admin

from booking.models import Booking, BookingItem, BookingItemAdditional


class BookingItemAdditionalInline(admin.TabularInline):
    model = BookingItemAdditional
    extra = 0


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "service_type",
        "groomer",
        "tanggal",
        "waktu_mulai",
        "waktu_selesai",
        "status",
        "payment_status",
    )
    list_filter = ("service_type", "status", "payment_status", "tanggal")
    search_fields = ("customer__username", "groomer__user__full_name")
    inlines = [BookingItemInline]


@admin.register(BookingItem)
class BookingItemAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "pet", "package", "harga_paket", "durasi_paket", "subtotal")
    search_fields = ("booking__id", "pet__name", "package__name")
    inlines = [BookingItemAdditionalInline]


@admin.register(BookingItemAdditional)
class BookingItemAdditionalAdmin(admin.ModelAdmin):
    list_display = ("id", "booking_item", "additional", "harga", "durasi")
    search_fields = ("booking_item__id", "additional__name")
