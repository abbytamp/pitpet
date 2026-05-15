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
        # Cek format gmail hanya untuk customer, staff, manager (bukan superadmin/groomer)
        from .models import User
        try:
            user = User.objects.get(username=username)
            if user.role in ['customer', 'manager', 'staff'] and not username.endswith('@gmail.com'):
                raise forms.ValidationError("Username hanya bisa format @gmail.com")
        except User.DoesNotExist:
            pass
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
        username = cleaned_data.get('username')
        if username and not username.endswith('@gmail.com'):
            raise forms.ValidationError("Username hanya bisa format @gmail.com")
        empty_fields = [field for field in self.fields if not cleaned_data.get(field)]
        if empty_fields:
            raise forms.ValidationError("Semua field wajib diisi")
        return cleaned_data

class RegisterStaffManagerForm(forms.ModelForm):
    role = forms.ChoiceField(choices=[('staff', 'Staff'), ('manager', 'Manager')], widget=forms.Select())

    class Meta:
        model = User
        fields = ['username', 'full_name', 'phone_number', 'role']
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
        username = cleaned_data.get('username')
        role = cleaned_data.get('role')
        if username and role in ['manager', 'staff'] and not username.endswith('@gmail.com'):
            raise forms.ValidationError("Username hanya bisa format @gmail.com")
        empty_fields = [field for field in self.fields if not cleaned_data.get(field)]
        if empty_fields:
            raise forms.ValidationError("Semua field wajib diisi")
        return cleaned_data

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'phone_number']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nomor Telepon'
            }),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        if not full_name or full_name.strip() == '':
            raise forms.ValidationError('Full Name tidak boleh kosong.')
        return full_name

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        if not phone_number:
            raise forms.ValidationError('Nomor Telepon tidak boleh kosong.')
        if not re.match(r'^\d+$', phone_number):
            raise forms.ValidationError('Nomor telepon hanya boleh angka')
        return phone_number


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'placeholder': 'Masukkan password lama',
        }),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Masukkan password baru',
        }),
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Ulangi password baru',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password', '')
        if not self.user or not self.user.check_password(old_password):
            raise forms.ValidationError('Password lama tidak sesuai.')
        return old_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password', '')
        old_password = self.cleaned_data.get('old_password', '')

        if new_password and old_password and new_password == old_password:
            raise forms.ValidationError('Password baru tidak boleh sama dengan password lama.')

        if new_password and len(new_password) < 8:
            raise forms.ValidationError('Password minimal 8 karakter.')

        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password', '')
        confirm_new_password = cleaned_data.get('confirm_new_password', '')

        if new_password and confirm_new_password and new_password != confirm_new_password:
            self.add_error('confirm_new_password', 'Konfirmasi password tidak cocok.')

        return cleaned_data
