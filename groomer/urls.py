from django.urls import path
from .views import (
    groomer_list,
    groomer_create,
    groomer_edit,
    groomer_update,
    groomer_delete,
)

app_name = "groomer"

urlpatterns = [
    path("", groomer_list, name="groomer_list"),
    path("create/", groomer_create, name="groomer_create"),
    path("<int:groomer_id>/edit/", groomer_edit, name="groomer_edit"),
    path("<int:groomer_id>/update/", groomer_update, name="groomer_update"),
    path("<int:groomer_id>/delete/", groomer_delete, name="groomer_delete"),
]
