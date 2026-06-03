from django import forms


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