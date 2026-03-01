from django.db import models

# Create your models here. 

class Package(models.Model):
    class AnimalType(models.TextChoices):
        CAT = "cat", "Cat"
        DOG = "dog", "Dog"
        
    class Duration(models.IntegerChoices):
        D30 = 30, "30 menit"
        D60 = 60, "60 menit"
        D90 = 90, "90 menit"
        D120 = 120, "120 menit"

    name = models.CharField(max_length=120)
    animal_type = models.CharField(max_length=10, choices=AnimalType.choices)
    description = models.TextField()
    duration_min = models.IntegerField(choices=Duration.choices)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "packages"

    def __str__(self):
        return f"{self.name} ({self.animal_type})"
    
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
    price = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "package_prices"
        unique_together = ("package", "size")

    def __str__(self):
        return f"{self.package.name} - {self.size or 'CAT'}: {self.price}"