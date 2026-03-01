from django import forms

DURATION_CHOICES = [(30, "30 menit"), (60, "60 menit"), (90, "90 menit"), (120, "120 menit")]
ANIMAL_CHOICES = [("cat", "Kucing"), ("dog", "Anjing")]

class PackageForm(forms.Form):
    name = forms.CharField(required=True, max_length=255)
    animal_type = forms.ChoiceField(required=True, choices=ANIMAL_CHOICES)
    description = forms.CharField(required=True, widget=forms.Textarea)
    duration_min = forms.ChoiceField(required=True, choices=DURATION_CHOICES)

    # price fields (declare semua, nanti validasinya conditional)
    price_cat = forms.IntegerField(required=False, min_value=0)
    price_s = forms.IntegerField(required=False, min_value=0)
    price_m = forms.IntegerField(required=False, min_value=0)
    price_l = forms.IntegerField(required=False, min_value=0)
    price_xl = forms.IntegerField(required=False, min_value=0)

    def __init__(self, *args, locked_animal_type=None, **kwargs):
        
        # locked_animal_type:
        # None -> create biasa
        # "cat"/"dog" -> update, animal_type harus segitu dan tidak boleh berubah
        
        super().__init__(*args, **kwargs)
        self.locked_animal_type = locked_animal_type

        if locked_animal_type:
            # tetap render di template, tapi akan disable di HTML
            # lock di server-side
            self.fields["animal_type"].disabled = True
            self.fields["animal_type"].initial = locked_animal_type
        
    def clean(self):
        cleaned = super().clean()
        
        # kl locked, paksa animal_type sesuai data DB
        if self.locked_animal_type:
            cleaned["animal_type"] = self.locked_animal_type
        animal = cleaned.get("animal_type")

        # duration positive (choice udah fixed, tapi kita jaga-jaga)
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
            for f in ["price_s", "price_m", "price_l", "price_xl"]:
                if cleaned.get(f) is None:
                    self.add_error(f, "Harga wajib diisi.")
        else:
            self.add_error("animal_type", "Animal type tidak valid.")

        return cleaned