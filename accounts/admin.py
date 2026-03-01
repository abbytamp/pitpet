from django.contrib import admin
from .models import User, Groomer

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'role', 'phone_number', 'is_active')
    search_fields = ('username', 'full_name')
    list_filter = ('role', 'is_active')

@admin.register(Groomer)
class GroomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'service_type')
