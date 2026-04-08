from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
from .forms import LoginForm, RegisterCustomerForm, RegisterStaffManagerForm, ProfileForm
from .models import User, Groomer

@login_required
@user_passes_test(lambda u: u.role == 'superadmin')
def superadmin_staff_list(request):
    staffs = User.objects.filter(role='staff').order_by('full_name')
    return render(request, 'superadmin/staff_list.html', {'staffs': staffs})

@login_required
@user_passes_test(lambda u: u.role == 'superadmin')
def superadmin_manager_list(request):
    managers = User.objects.filter(role='manager').order_by('full_name')
    return render(request, 'superadmin/manager_list.html', {'managers': managers})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.role == 'customer':
                    return redirect('customer_dashboard')
                elif user.role == 'staff':
                    return redirect('staff_dashboard')
                elif user.role == 'groomer':
                    return redirect('groomer_dashboard')
                elif user.role == 'manager':
                    return redirect('manager_dashboard')
                elif user.role == 'superadmin':
                    return redirect('superadmin_dashboard')
            else:
                messages.error(request, "Invalid username or password")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})

def register_customer(request):
    if request.method == 'POST':
        form = RegisterCustomerForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = form.cleaned_data['password']
            user.role = 'customer'
            user.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = RegisterCustomerForm()
    return render(request, 'auth/register_customer.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.role in ['manager', 'superadmin'] or u.is_superuser)
def register_staff_manager(request):
    if request.method == 'POST':
        form = RegisterStaffManagerForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set password default untuk staff/manager
            user.password = 'password123'
            user.save()
            messages.success(request, f"Successfully registered {user.role}.")
            # Redirect based on current user's role
            if request.user.role == 'superadmin':
                return redirect('superadmin_dashboard')
            return redirect('manager_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = RegisterStaffManagerForm()
    return render(request, 'auth/register_staff_manager.html', {'form': form})

def logout_view(request):
    """Handle user logout for all roles.
    Clears the session and redirects to the login page with a success message.
    """
    logout(request)
    messages.success(request, 'Anda berhasil logout.')
    return redirect('login')

@login_required
def customer_dashboard(request):
    if request.user.role != 'customer':
        return redirect('login')
    return render(request, 'customer_dashboard.html', {'user': request.user})

@login_required
def staff_dashboard(request):
    if request.user.role != 'staff':
        return redirect('login')
    return render(request, 'staff_dashboard.html', {'user': request.user})

@login_required
def groomer_dashboard(request):
    if request.user.role != 'groomer':
        return redirect('login')
    return render(request, 'groomer_dashboard.html', {'user': request.user})

@login_required
def manager_dashboard(request):
    if request.user.role != 'manager':
        return redirect('login')
    return render(request, 'manager_dashboard.html', {'user': request.user})

@login_required
def superadmin_dashboard(request):
    if request.user.role != 'superadmin':
        return redirect('login')
    context = {
        'user': request.user,
        'total_customers': User.objects.filter(role='customer').count(),
        'total_groomers': User.objects.filter(role='groomer').count(),
        'total_staff': User.objects.filter(role='staff').count(),
        'total_managers': User.objects.filter(role='manager').count(),
    }
    return render(request, 'superadmin_dashboard.html', context)


# =============================================
# Staff: Melihat Data Customer dan Hewan (Read-Only)
# Endpoint: GET /accounts/staff/customers/
# Endpoint: GET /accounts/staff/customers/<customer_id>/
# =============================================

@login_required
def staff_customer_list(request):
    """Menampilkan daftar seluruh customer.
    Hanya dapat diakses oleh Staff Operasional.
    Mendukung pencarian berdasarkan nama atau username.
    """
    if request.user.role != 'staff':
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('login')

    query = request.GET.get('q', '').strip()
    customers = User.objects.filter(role='customer')

    if query:
        customers = customers.filter(
            Q(full_name__icontains=query) | Q(username__icontains=query)
        )

    customers = customers.order_by('full_name')

    return render(request, 'staff/customer_list.html', {
        'customers': customers,
        'query': query,
        'user': request.user,
    })


@login_required
def staff_customer_detail(request, customer_id):
    """Menampilkan detail customer beserta daftar hewan peliharaannya.
    Hanya dapat diakses oleh Staff Operasional. Data bersifat read-only.
    """
    if request.user.role != 'staff':
        messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
        return redirect('login')

    customer = get_object_or_404(User, id=customer_id, role='customer')
    pets = customer.pets.all()

    return render(request, 'staff/customer_detail.html', {
        'customer': customer,
        'pets': pets,
        'user': request.user,
    })


@login_required
def staff_customer_list_api(request):
    """API endpoint GET /api/admin/customers
    Mengembalikan daftar seluruh customer. Hanya untuk Staff Operasional.
    """
    if request.user.role != 'staff':
        return JsonResponse({"error": "Forbidden"}, status=403)

    customers = User.objects.filter(role='customer').values(
        'id', 'full_name', 'username', 'phone_number'
    )
    return JsonResponse({"customers": list(customers)}, status=200)


@login_required
def staff_customer_detail_api(request, customer_id):
    """API endpoint GET /api/admin/customers/<customer_id>
    Mengembalikan detail customer beserta daftar hewan peliharaannya.
    Hanya untuk Staff Operasional.
    """
    if request.user.role != 'staff':
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        customer = User.objects.get(id=customer_id, role='customer')
    except User.DoesNotExist:
        return JsonResponse({"error": "Customer tidak ditemukan."}, status=404)

    pets = list(customer.pets.values(
        'id', 'name', 'jenis', 'ras', 'umur', 'berat'
    ))

    return JsonResponse({
        "customer": {
            "id": customer.id,
            "full_name": customer.full_name,
            "username": customer.username,
            "phone_number": customer.phone_number,
        },
        "pets": pets,
    }, status=200)

# API Views
@method_decorator(login_required(login_url='login'), name='dispatch')
class ProfileAPIView(View):
    """API endpoint for GET and PUT profile"""
    
    def get(self, request):
        """Get user profile data"""
        user = request.user
        data = {
            'id': user.id,
            'full_name': user.full_name,
            'username': user.username,
            'phone_number': user.phone_number,
            'role': user.role,
        }
        if user.role == 'groomer':
            try:
                groomer_profile = user.groomer_profile
                data.update({
                    'service_type': groomer_profile.service_type,
                    'status': 'Aktif' if not groomer_profile.is_deleted else 'Nonaktif',
                })
            except Groomer.DoesNotExist:
                data.update({
                    'service_type': None,
                    'status': 'Nonaktif',
                })
        return JsonResponse(data, status=200)

    def put(self, request):
        """Update user profile data"""
        user = request.user
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            full_name = data.get('full_name', '').strip()
            phone_number = data.get('phone_number', '').strip()
            
            if not full_name:
                return JsonResponse({'error': 'Full Name tidak boleh kosong.'}, status=400)
            if not phone_number:
                return JsonResponse({'error': 'Nomor Telepon tidak boleh kosong.'}, status=400)
            
            user.full_name = full_name
            user.phone_number = phone_number
            user.save()
            
            return JsonResponse({
                'message': 'Profil berhasil diperbarui',
                'user': {
                    'full_name': user.full_name,
                    'phone_number': user.phone_number,
                }
            }, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')
def profile_view(request):
    """Display user profile"""
    user = request.user
    is_groomer = user.role == 'groomer'
    groomer_profile = None
    
    if is_groomer:
        try:
            groomer_profile = user.groomer_profile
        except Groomer.DoesNotExist:
            groomer_profile = None
    
    context = {
        'user': user,
        'is_groomer': is_groomer,
        'groomer_profile': groomer_profile,
    }
    return render(request, 'accounts/profile.html', context)

@login_required(login_url='login')
def edit_profile_view(request):
    """Edit user profile (Full Name and Phone)"""
    user = request.user
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil berhasil diperbarui')
            return redirect('profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ProfileForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'accounts/edit_profile.html', context)

@login_required(login_url='login')
@require_http_methods(["GET"])
def change_password_view(request):
    """Redirect to change password page"""
    return render(request, 'accounts/change_password.html')
