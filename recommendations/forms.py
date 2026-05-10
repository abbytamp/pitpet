from django import forms


ANIMAL_TYPE_CHOICES = [
    ('dog', 'Anjing'),
    ('cat', 'Kucing'),
]

FUR_CONDITION_CHOICES = [
    ('thick_long_fur', 'Bulu tebal/panjang'),
    ('dull_shedding_fur', 'Bulu rontok/kusam'),
    ('matted_fur', 'Bulu kusut/gimbal'),
]

SKIN_CONDITION_CHOICES = [
    ('fleas', 'Berkutu'),
    ('fungus_irritation', 'Berjamur/iritasi'),
]

ADDITIONAL_CONDITION_CHOICES = [
    ('long_nails', 'Kuku panjang'),
    ('dirty_ears', 'Telinga kotor'),
    ('styling', 'Ingin styling/potong model'),
]


class RecommendationForm(forms.Form):
    animal_type = forms.ChoiceField(
        choices=ANIMAL_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        error_messages={
            'required': 'Jenis hewan wajib dipilih'
        }
    )

    fur_conditions = forms.MultipleChoiceField(
        choices=FUR_CONDITION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    skin_conditions = forms.MultipleChoiceField(
        choices=SKIN_CONDITION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    additional_conditions = forms.MultipleChoiceField(
        choices=ADDITIONAL_CONDITION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()

        fur_conditions = cleaned_data.get('fur_conditions') or []
        skin_conditions = cleaned_data.get('skin_conditions') or []
        additional_conditions = cleaned_data.get('additional_conditions') or []

        all_conditions = fur_conditions + skin_conditions + additional_conditions

        if not all_conditions:
            raise forms.ValidationError('Pilih minimal satu kondisi hewan')

        return cleaned_data