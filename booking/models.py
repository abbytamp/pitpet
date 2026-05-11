
from django.conf import settings
from django.db import models
from accounts.models import Groomer
from packages.models import Package
from pet.models import Pet


class BookingReview(models.Model):
    booking = models.OneToOneField('Booking', on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'customer')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for Booking #{self.booking_id} by {self.customer.full_name}"


class Booking(models.Model):
    tanggal = models.DateField()
    class ServiceType(models.TextChoices):
        CLINIC = "clinic", "Clinic"
        HOME = "home", "Home"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        SERVICE_STARTED = "service_started", "Service started"
        SERVICE_COMPLETED = "service_completed", "Service completed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    service_type = models.CharField(max_length=10, choices=ServiceType.choices)

    groomer = models.ForeignKey(
        Groomer,
        on_delete=models.PROTECT,
        related_name="bookings",
    )


    waktu_mulai = models.TimeField()
    waktu_selesai = models.TimeField()
    total_durasi = models.PositiveIntegerField(help_text="Total durasi dalam menit")
    total_harga = models.DecimalField(max_digits=12, decimal_places=2)
    alamat = models.TextField(null=True, blank=True)
    catatan = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    is_rescheduled = models.BooleanField(default=False)
    original_tanggal = models.DateField(null=True, blank=True)
    original_waktu_mulai = models.TimeField(null=True, blank=True)
    original_waktu_selesai = models.TimeField(null=True, blank=True)
    grooming_notes = models.TextField(null=True, blank=True, help_text="Catatan hasil grooming yang diisi oleh groomer setelah layanan selesai")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bookings"
        ordering = ["-tanggal", "-waktu_mulai", "-id"]

    @property
    def booking_code(self) -> str:
        if not self.pk:
            return "BK-000"
        return f"BK-{self.pk:03d}"

    def __str__(self):
        return f"Booking {self.booking_code} - {self.customer.username} ({self.tanggal} {self.waktu_mulai})"

    @property
    def can_reschedule(self):
        if self.status != Booking.Status.SCHEDULED:
            return False
        if self.is_rescheduled:
            return False
        from django.utils import timezone
        from datetime import datetime, timedelta
        now = timezone.localtime()
        booking_datetime = timezone.make_aware(datetime.combine(self.tanggal, self.waktu_mulai))
        return (booking_datetime - now) >= timedelta(hours=2)

    @property
    def time_diff_hours(self):
        from django.utils import timezone
        from datetime import datetime, timedelta
        now = timezone.localtime()
        booking_datetime = timezone.make_aware(datetime.combine(self.tanggal, self.waktu_mulai))
        diff = booking_datetime - now
        return diff.total_seconds() / 3600 if diff.total_seconds() > 0 else 0
    
    @property
    def can_cancel(self):
        if self.status != Booking.Status.SCHEDULED:
            return False

        from django.utils import timezone
        from datetime import datetime, timedelta

        now = timezone.localtime()
        booking_datetime = timezone.make_aware(
            datetime.combine(self.tanggal, self.waktu_mulai)
        )
        return (booking_datetime - now) >= timedelta(hours=2)

    @property
    def cancel_block_message(self):
        if self.status != Booking.Status.SCHEDULED:
            return "Booking tidak dapat dibatalkan."

        if not self.can_cancel:
            return "Sisa waktu kurang dari 2 jam, harap lapor via Whatsapp ke staff untuk melakukan pembatalan."

        return ""

class BookingItem(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="items",
    )
    pet = models.ForeignKey(Pet, on_delete=models.PROTECT, related_name="booking_items")
    package = models.ForeignKey(
        Package,
        on_delete=models.PROTECT,
        related_name="booking_items",
    )
    package_name = models.CharField(max_length=120, null=True, blank=True)
    harga_paket = models.DecimalField(max_digits=12, decimal_places=2)
    durasi_paket = models.PositiveIntegerField(help_text="Durasi paket dalam menit")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "booking_items"

    def __str__(self):
        return f"BookingItem #{self.id} - Booking BK-{self.booking_id:03d}"


class BookingItemAdditional(models.Model):
    booking_item = models.ForeignKey(
        BookingItem,
        on_delete=models.CASCADE,
        related_name="additionals",
    )
    additional = models.ForeignKey(
        Package,
        on_delete=models.PROTECT,
        related_name="booking_item_additionals",
    )
    additional_name = models.CharField(max_length=120, null=True, blank=True)
    harga = models.DecimalField(max_digits=12, decimal_places=2)
    durasi = models.PositiveIntegerField(help_text="Durasi additional dalam menit")

    class Meta:
        db_table = "booking_item_additionals"

    def __str__(self):
        return f"BookingItemAdditional #{self.id} - BookingItem #{self.booking_item_id}"
