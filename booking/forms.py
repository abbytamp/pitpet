from django import forms
from .models import BookingReview

class BookingReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} ⭐") for i in range(1, 6)],
        widget=forms.RadioSelect,
        label="Rating",
        required=True,
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Tulis komentar (opsional)"}),
        required=False,
        label="Komentar",
    )

    class Meta:
        model = BookingReview
        fields = ["rating", "comment"]
