from django import forms
from accounts.models import Groomer


class GroomerForm(forms.ModelForm):
    class Meta:
        model = Groomer
        fields = ['service_type']
        widgets = {
            'service_type': forms.RadioSelect,
        }


class GroomerCreateForm(forms.Form):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg',
        'placeholder': 'email@example.com',
    }))
    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg',
        'placeholder': 'Nama Lengkap'
    }))
    phone_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg',
        'placeholder': '0812xxxx'
    }))
    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg',
        'placeholder': 'Password (minimal 8 karakter)'
    }))
    service_type = forms.ChoiceField(choices=Groomer.ServiceType.choices, widget=forms.RadioSelect)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and not username.lower().endswith('@gmail.com'):
            raise forms.ValidationError('Hanya alamat email @gmail.com yang diperbolehkan')
        from accounts.models import User
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username sudah digunakan')
        return username

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        import re
        if not re.match(r'^\d+$', phone):
            raise forms.ValidationError('No HP hanya boleh berisi angka')
        return phone


class GroomerEditForm(forms.Form):
    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg',
    }))
    phone_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg',
    }))

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        import re
        if not re.match(r'^\d+$', phone):
            raise forms.ValidationError('No HP hanya boleh berisi angka')
        return phone
