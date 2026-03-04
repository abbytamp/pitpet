from django.urls import path
from . import views
from .views import update_pet_api

app_name = 'user_profile'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('pet/add/', views.add_pet, name='add_pet'),
    path('pet/edit/<int:pet_id>/', views.edit_pet, name='edit_pet'),
    path('pet/delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),
    path('api/profile/', views.update_profile_api, name='update_profile_api'),
    path('api/pets/<int:pet_id>/', update_pet_api, name='update_pet_api'),
    path('api/pets/<int:pet_id>/delete/', views.delete_pet_api, name='delete_pet_api'),
]