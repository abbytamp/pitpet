from django.db import models
from django.conf import settings  # WAJIB untuk custom user
from django.utils import timezone


class ActivePetManager(models.Manager):
    """Manager yang hanya mengembalikan pet yang belum di-soft-delete."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Pet(models.Model):
    PET_TYPE_CHOICES = [
        ('Cat', 'Cat'),
        ('Dog', 'Dog'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # pakai custom user
        on_delete=models.CASCADE,
        related_name='pets'
    )
    name = models.CharField(max_length=100)
    jenis = models.CharField(max_length=10, choices=PET_TYPE_CHOICES)
    ras = models.CharField(max_length=100)
    umur = models.IntegerField(help_text="Umur dalam bulan")
    berat = models.FloatField(help_text="Berat dalam kg")

    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Default manager returns only active (non-deleted) pets
    objects = ActivePetManager()
    # Use all_objects to include soft-deleted pets if needed
    all_objects = models.Manager()

    def soft_delete(self):
        """Soft delete: tandai hewan sebagai dihapus tanpa menghapus dari database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore: batalkan soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def __str__(self):
        return f"{self.name} - {self.owner.username}"