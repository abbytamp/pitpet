from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # Logout: clears session & redirects to login
    path('register/', views.register_customer, name='register_customer'),
    path('register/staff-manager/', views.register_staff_manager, name='register_staff_manager'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/groomer/', views.groomer_dashboard, name='groomer_dashboard'),
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),
    path('dashboard/superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),
]
