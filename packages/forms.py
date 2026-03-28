from django import forms
from .models import Package

DURATION_CHOICES = [(30, "30 menit"), (60, "60 menit"), (90, "90 menit"), (120, "120 menit")]
ANIMAL_CHOICES = [("cat", "Kucing"), ("dog", "Anjing")]
PACKAGE_TYPE_CHOICES = [("grooming", "Grooming"), ("additional", "Additional")]

class PackageForm(forms.Form):
    name = forms.CharField(required=True, max_length=255)
    animal_type = forms.ChoiceField(required=True, choices=ANIMAL_CHOICES)
    package_type = forms.ChoiceField(required=True, choices=PACKAGE_TYPE_CHOICES)
    description = forms.CharField(required=True, widget=forms.Textarea)
    duration_min = forms.ChoiceField(required=True, choices=DURATION_CHOICES)

    # price fields (declare semua, nanti validasinya conditional)
    price_cat = forms.IntegerField(required=False, min_value=1)
    price_all_size = forms.IntegerField(required=False, min_value=1)
    price_s = forms.IntegerField(required=False, min_value=1)
    price_m = forms.IntegerField(required=False, min_value=1)
    price_l = forms.IntegerField(required=False, min_value=1)
    price_xl = forms.IntegerField(required=False, min_value=1)

    def __init__(self, *args, locked_animal_type=None, locked_package_type=None, package_instance=None, **kwargs):
        
        # locked_animal_type & locked_package_type:
        # None -> create biasa
        # "cat"/"dog" -> update, animal_type tetap sama, tidak bisa diubah
        # "grooming"/"additional" -> update, package_type tetap sama, tidak bisa diubah
        # package_instance: instance Package yang sedang diedit, untuk validasi unique name per animal_type saat edit (exclude dirinya sendiri, tidak menganggap dirinya sendiri duplikat)

        super().__init__(*args, **kwargs)
        self.locked_animal_type = locked_animal_type
        self.locked_package_type = locked_package_type
        self.package_instance = package_instance

        if locked_animal_type:
            self.fields["animal_type"].disabled = True
            self.fields["animal_type"].initial = locked_animal_type

        if locked_package_type:
            self.fields["package_type"].disabled = True
            self.fields["package_type"].initial = locked_package_type

    def clean(self):
        cleaned = super().clean()
        
        # kl locked, sesuai data DB
        if self.locked_animal_type:
            cleaned["animal_type"] = self.locked_animal_type
        if self.locked_package_type:
            cleaned["package_type"] = self.locked_package_type
        animal = cleaned.get("animal_type")
        package_type = cleaned.get("package_type")

        # unique name per animal_type
        name = cleaned.get("name")
        if name and animal:
            duplicate_qs = Package.all_objects.filter(
                name=name,
                animal_type=animal,
                is_deleted=False,
            )

            if self.package_instance:
                duplicate_qs = duplicate_qs.exclude(id=self.package_instance.id)

            if duplicate_qs.exists():
                self.add_error("name", "Nama paket sudah digunakan untuk jenis hewan ini.")
                
        # duration positive (choice udah fixed)
        duration = cleaned.get("duration_min")
        if duration:
            try:
                if int(duration) <= 0:
                    self.add_error("duration_min", "Durasi harus angka positif.")
            except ValueError:
                self.add_error("duration_min", "Durasi tidak valid.")

        # conditional prices
        if animal == "cat":
            if cleaned.get("price_cat") is None:
                self.add_error("price_cat", "Harga kucing wajib diisi.")
        elif animal == "dog":
            if package_type == "additional":
                if cleaned.get("price_all_size") is None:
                    self.add_error("price_all_size", "Harga wajib diisi.")
            else:
                for f in ["price_s", "price_m", "price_l", "price_xl"]:
                    if cleaned.get(f) is None:
                        self.add_error(f, "Harga wajib diisi.")
        else:
            self.add_error("animal_type", "Animal type tidak valid.")

        return cleaned