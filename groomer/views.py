from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseBadRequest
from accounts.models import Groomer, User
from packages.decorators import staff_required
from .forms import GroomerForm, GroomerCreateForm, GroomerEditForm


@staff_required
def groomer_list(request):
    """Read: Display list of all active groomers"""
    groomers = Groomer.objects.select_related("user").all()
    return render(request, "groomer_list.html", {"groomers": groomers})


@staff_required
def groomer_create(request):
    """Display form untuk create groomer baru and handle submission"""
    if request.method == 'POST':
        form = GroomerCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            username = data['username']
            full_name = data['full_name']
            phone = data['phone_number']
            password = data['password']
            service_type = data['service_type']

            # Double-check username uniqueness
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username sudah digunakan')
            else:
                # create user and groomer
                user = User(
                    username=username,
                    full_name=full_name,
                    phone_number=phone,
                    role='groomer',
                    is_active=True,
                )
                user.set_password(password)
                user.save()

                Groomer.objects.create(user=user, service_type=service_type)

                messages.success(request, 'Groomer berhasil ditambahkan')
                return redirect('groomer:groomer_list')
    else:
        form = GroomerCreateForm()

    return render(request, 'groomer_form.html', {
        'form': form,
        'mode': 'create',
    })





@staff_required
def groomer_edit(request, groomer_id: int):
    """Display form untuk edit groomer"""
    groomer = get_object_or_404(Groomer.objects.select_related("user"), id=groomer_id)

    # Prefill edit form with user's data
    initial = {
        'full_name': groomer.user.full_name,
        'phone_number': groomer.user.phone_number,
    }

    form = GroomerEditForm(initial=initial)

    return render(request, "groomer_form.html", {
        "form": form,
        "mode": "edit",
        "groomer": groomer,
    })


@staff_required
def groomer_update(request, groomer_id: int):
    """Update: Update data groomer"""
    if request.method != "POST":
        return HttpResponseBadRequest("Bad Request")
    
    groomer = get_object_or_404(Groomer.objects.select_related("user"), id=groomer_id)

    form = GroomerEditForm(request.POST)
    if not form.is_valid():
        # re-render with errors
        return render(request, "groomer_form.html", {
            'form': form,
            'mode': 'edit',
            'groomer': groomer,
        }, status=400)

    data = form.cleaned_data
    # Update user's editable fields
    groomer.user.full_name = data['full_name']
    groomer.user.phone_number = data['phone_number']
    groomer.user.save()
    
    messages.success(request, "Data groomer berhasil diperbarui")
    return redirect("groomer:groomer_list")


@staff_required
def groomer_delete(request, groomer_id: int):
    """Soft delete a groomer"""
    if request.method != "POST":
        return HttpResponseBadRequest("Bad Request")

    groomer = get_object_or_404(
        Groomer.objects.select_related("user"), id=groomer_id
    )

    # TODO: check for active bookings when booking feature is implemented
    # if groomer has active bookings, deny deletion
    # has_active_booking = Booking.objects.filter(
    #     groomer=groomer, status__in=['scheduled', 'in_progress']
    # ).exists()
    # if has_active_booking:
    #     messages.error(
    #         request,
    #         f'Tidak dapat menghapus groomer yang memiliki booking aktif.'
    #     )
    #     return redirect('groomer:groomer_list')

    groomer.soft_delete()
    messages.success(request, f'Groomer {groomer.user.full_name} berhasil dihapus.')
    return redirect('groomer:groomer_list')


