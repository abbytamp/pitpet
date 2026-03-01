from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import LoginForm, RegisterCustomerForm, RegisterStaffManagerForm
from .models import User

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
            # Re-matching the specific error message requirement
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
            user.password = form.cleaned_data['password']
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
