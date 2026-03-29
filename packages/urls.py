from django.urls import path
from . import views

urlpatterns = [
    path("", views.package_list, name="package_list"),
    
    path("create/", views.package_create, name="package_create"),
    path("store/", views.package_store, name="package_store"),
    
    path("<int:package_id>/edit/", views.package_edit, name="package_edit"),
    path("<int:package_id>/update/", views.package_update, name="package_update"),
    path("<int:package_id>/delete/", views.package_delete, name="package_delete"),

    path("catalog/", views.package_catalog, name="package_catalog"),
]