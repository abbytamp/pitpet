from django.db import models
from django.conf import settings  # WAJIB untuk custom user

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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.owner.username}"