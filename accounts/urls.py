
from django.urls import path
from . import views

urlpatterns = [
    path('superadmin/staff/', views.superadmin_staff_list, name='superadmin_staff_list'),
    path('superadmin/manager/', views.superadmin_manager_list, name='superadmin_manager_list'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # Logout: clears session & redirects to login
    path('register/', views.register_customer, name='register_customer'),
    path('register/staff-manager/', views.register_staff_manager, name='register_staff_manager'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/groomer/', views.groomer_dashboard, name='groomer_dashboard'),
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),
    path('dashboard/superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),

    # Staff: Melihat Data Customer dan Hewan (Read-Only)
    path('staff/customers/', views.staff_customer_list, name='staff_customer_list'),
    path('staff/customers/<int:customer_id>/', views.staff_customer_detail, name='staff_customer_detail'),

    # API endpoints
    path('api/admin/customers/', views.staff_customer_list_api, name='staff_customer_list_api'),
    path('api/admin/customers/<int:customer_id>/', views.staff_customer_detail_api, name='staff_customer_detail_api'),
]
