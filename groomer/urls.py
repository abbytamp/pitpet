from django.urls import path
from .views import groomer_list

urlpatterns = [
    path("", groomer_list, name="groomer_list"),
]