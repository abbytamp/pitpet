from django.core.exceptions import ValidationError
from django.db import models

from booking.models import BookingItem


def validate_image_file(value):
    content_type = getattr(value, "content_type", None)
    if content_type and not content_type.startswith("image/"):
        raise ValidationError("File bukti layanan harus berupa gambar.")

    valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    file_name = value.name.lower()
    if not any(file_name.endswith(ext) for ext in valid_extensions):
        raise ValidationError("Format file gambar harus jpg, jpeg, png, atau webp.")


class GroomingServiceForm(models.Model):
    booking_item = models.OneToOneField(
        BookingItem,
        on_delete=models.CASCADE,
        related_name="grooming_service_form",
    )
    kondisi_bulu = models.TextField()
    kondisi_kulit = models.TextField()
    kondisi_telinga = models.TextField()
    kondisi_kuku = models.TextField()
    perilaku_hewan = models.TextField()
    catatan_tambahan = models.TextField(blank=True, null=True)
    foto_bukti_layanan = models.ImageField(
        upload_to="grooming_service_forms/",
        validators=[validate_image_file],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grooming_service_forms"

    def __str__(self):
        return f"Form layanan BookingItem #{self.booking_item_id}"