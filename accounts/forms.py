from django import forms
from .models import User
import re

class LoginForm(forms.Form):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        if not username or not password:
            raise forms.ValidationError("Semua field wajib diisi")
        return cleaned_data

class RegisterCustomerForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), min_length=6, error_messages={
        'min_length': 'Password harus minimal 6 karakter'
    })
    
    class Meta:
        model = User
        fields = ['username', 'full_name', 'phone_number', 'password']
        widgets = {
            'username': forms.EmailInput(attrs={'placeholder': 'Email'}),
        }
        error_messages = {
            'username': {
                'invalid': 'Username harus berupa format email',
                'unique': 'Username sudah ada, silhkan pilih username lain',
            }
        }

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not re.match(r'^\d+$', phone_number):
            raise forms.ValidationError("Nomor telepon hanya boleh angka")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        for field in self.fields:
            if not cleaned_data.get(field):
                raise forms.ValidationError("Semua field wajib diisi")
        return cleaned_data

class RegisterStaffManagerForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), min_length=6, error_messages={
        'min_length': 'Password harus minimal 6 karakter'
    })
    role = forms.ChoiceField(choices=[('staff', 'Staff'), ('manager', 'Manager'), ('superadmin', 'Superadmin')], widget=forms.Select())

    class Meta:
        model = User
        fields = ['username', 'full_name', 'phone_number', 'password', 'role']
        error_messages = {
            'username': {
                'invalid': 'Username harus berupa format email',
                'unique': 'Username sudah ada, silhkan pilih username lain',
            }
        }

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not re.match(r'^\d+$', phone_number):
            raise forms.ValidationError("Nomor telepon hanya boleh angka")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        for field in self.fields:
            if not cleaned_data.get(field):
                raise forms.ValidationError("Semua field wajib diisi")
        return cleaned_data
