from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MinValueValidator


class ActivePackageManager(models.Manager):
    """Manager yang hanya mengembalikan paket yang belum di-soft-delete."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

RECOMMENDATION_TAG_CHOICES = [
    ("thick_long_fur", "Bulu tebal/panjang"),
    ("dull_shedding_fur", "Bulu rontok/kusam"),
    ("matted_fur", "Bulu kusut/gimbal"),
    ("fleas", "Berkutu"),
    ("fungus_irritation", "Berjamur/iritasi"),
    ("long_nails", "Kuku panjang"),
    ("dirty_ears", "Telinga kotor"),
    ("styling", "Ingin styling/potong model"),
]

class Package(models.Model):
    class AnimalType(models.TextChoices):
        CAT = "cat", "Cat"
        DOG = "dog", "Dog"
        
    class PackageType(models.TextChoices):
        GROOMING = "grooming", "Grooming"
        ADDITIONAL = "additional", "Additional"
        
    class Duration(models.IntegerChoices):
        D30 = 30, "30 menit"
        D60 = 60, "60 menit"
        D90 = 90, "90 menit"
        D120 = 120, "120 menit"

    name = models.CharField(max_length=120)
    animal_type = models.CharField(max_length=10, choices=AnimalType.choices)
    package_type = models.CharField(max_length=10, choices=PackageType.choices, default=PackageType.GROOMING)
    description = models.TextField()
    duration_min = models.IntegerField(choices=Duration.choices)
    recommendation_tags = models.JSONField(default=list, blank=True)
    is_all_size = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Default manager: hanya paket aktif
    objects = ActivePackageManager()
    # Semua paket termasuk yang soft-deleted
    all_objects = models.Manager()

    class Meta:
        db_table = "packages"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "animal_type"],
                condition=Q(is_deleted=False),
                name="unique_active_package_name_per_animal",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.animal_type} - {self.package_type})"
    
    @property
    def price_s(self):
        return self.dog_prices.get("S")

    @property
    def price_m(self):
        return self.dog_prices.get("M")

    @property
    def price_l(self):
        return self.dog_prices.get("L")

    @property
    def price_xl(self):
        return self.dog_prices.get("XL")
    
    @property
    def cat_price(self):
        """
        Untuk kucing: cuma 1 harga (size NULL).
        Return integer atau None.
        """
        obj = self.prices.filter(size__isnull=True).first()
        return obj.price if obj else None

    @property
    def dog_prices(self):
        """
        Untuk anjing: dict harga per size.
        Return: {"S": 50000, "M": 60000, ...}
        """
        qs = self.prices.exclude(size__isnull=True)
        return {pp.size: pp.price for pp in qs}

    def get_price_by_size(self, size: str):
        return self.dog_prices.get(size)

    def soft_delete(self):
        """Soft delete: tandai paket sebagai dihapus tanpa menghapus dari database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore: batalkan soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class PackagePrice(models.Model):
    class Size(models.TextChoices):
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    # cat: size = NULL
    # dog: size in S/M/L/XL
    size = models.CharField(max_length=2, choices=Size.choices, null=True, blank=True)
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "package_prices"
        unique_together = ("package", "size")

    def __str__(self):
        return f"{self.package.name} - {self.size or 'CAT'}: {self.price}"