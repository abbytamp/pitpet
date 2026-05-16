import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from pet.models import Pet
from booking.models import Booking, BookingItem
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import IntegrityError  


@login_required
def profile_view(request):
    user = request.user
    pets = Pet.objects.filter(owner=user)

    return render(request, 'user_profile/profile.html', {
        'user': user,
        'pets': pets
    })


@login_required
@require_http_methods(["PUT"])
def update_profile_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    full_name = data.get("full_name", "").strip()
    phone_number = data.get("phone_number", "").strip()

    if not full_name:
        return JsonResponse({"error": "Nama lengkap wajib diisi."}, status=400)

    if not phone_number:
        return JsonResponse({"error": "No HP wajib diisi."}, status=400)

    import re
    if not re.match(r'^08\d{8,10}$', phone_number):
        return JsonResponse({"error": "Nomor telepon harus dimulai dengan 08 dan berisi 10-12 digit angka."}, status=400)

    user = request.user
    user.full_name = full_name
    user.phone_number = phone_number
    user.save()

    return JsonResponse({
        "message": "Profil berhasil diperbarui.",
        "data": {
            "username": user.username,
            "full_name": user.full_name,
            "phone_number": user.phone_number
        }
    }, status=200)

@login_required
def edit_profile_view(request):
    user = request.user

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()

        if not full_name:
            messages.error(request, "Nama lengkap wajib diisi.")
            return render(request, "user_profile/edit_profile.html")

        if not phone_number:
            messages.error(request, "No HP wajib diisi.")
            return render(request, "user_profile/edit_profile.html")

        import re
        if not re.match(r'^08\d{8,10}$', phone_number):
            messages.error(request, "Nomor telepon harus dimulai dengan 08 dan berisi 10-12 digit angka.")
            return render(request, "user_profile/edit_profile.html")

        user.full_name = full_name
        user.phone_number = phone_number
        user.save()

        messages.success(request, "Profil berhasil diperbarui.")
        return redirect("user_profile:profile")

    return render(request, "user_profile/edit_profile.html")


@login_required
def add_pet(request):
    if request.method == 'POST':
        try:
            Pet.objects.create(
                owner=request.user,
                name=request.POST.get('name'),
                jenis=request.POST.get('jenis'),
                ras=request.POST.get('ras'),
                berat=request.POST.get('berat'),
                umur=request.POST.get('umur'),
            )

            messages.success(request, "Hewan berhasil ditambahkan!")
            return redirect('user_profile:profile')

        except IntegrityError:
            messages.error(request, "Nama hewan sudah ada!")
            return render(request, 'user_profile/add_pet.html')

    return render(request, 'user_profile/add_pet.html')


@require_http_methods(["PUT"])
def update_pet_api(request, pet_id):
    try:
        pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

        data = json.loads(request.body)

        name = data.get("name")
        ras = data.get("ras")
        umur = data.get("umur")
        berat = data.get("berat")

        if not all([name, ras, umur, berat]):
            return JsonResponse({"error": "Field ini wajib diisi."}, status=400)

        pet.name = name
        pet.ras = ras
        pet.umur = umur
        pet.berat = berat
        pet.save()

        return JsonResponse({
            "message": "Data hewan berhasil diperbarui",
            "pet": {
                "id": pet.id,
                "name": pet.name,
                "jenis": pet.jenis,
                "ras": pet.ras,
                "umur": pet.umur,
                "berat": pet.berat,
            }
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    if request.method == "POST":
        name = request.POST.get("name")
        ras = request.POST.get("ras")
        umur = request.POST.get("umur")
        berat = request.POST.get("berat")

        if not name or not ras or not umur or not berat:
            messages.error(request, "Field ini wajib diisi.")
            return render(request, "edit_pet.html", {"pet": pet})

        pet.name = name
        pet.ras = ras
        pet.umur = umur
        pet.berat = berat
        pet.save()

        messages.success(request, "Data hewan berhasil diperbarui")
        return redirect("user_profile:profile")

    return render(request, "user_profile/edit_pet.html", {"pet": pet})


@login_required
def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    if request.method == 'POST':
        has_active_booking = BookingItem.objects.filter(
            pet_id=pet.id,
            booking__customer=request.user,
        ).filter(
            booking__status__in=[
                Booking.Status.SCHEDULED,
                Booking.Status.SERVICE_STARTED,
            ]
        ).exists() or BookingItem.objects.filter(
            pet_id=pet.id,
            booking__customer=request.user,
            booking__status=Booking.Status.SERVICE_COMPLETED,
            booking__payment_status=Booking.PaymentStatus.UNPAID,
        ).exists()

        if has_active_booking:
            messages.error(request, "Hewan tidak dapat dihapus karena masih memiliki booking aktif.")
            return redirect('user_profile:profile')

        pet.soft_delete()
        messages.success(request, "Hewan peliharaan berhasil dihapus.")
        return redirect('user_profile:profile')

    return redirect('user_profile:profile')


@login_required
@require_http_methods(["DELETE"])
def delete_pet_api(request, pet_id):
    try:
        pet = Pet.objects.get(id=pet_id, owner=request.user)
    except Pet.DoesNotExist:
        return JsonResponse({"error": "Hewan tidak ditemukan."}, status=404)

    has_active_booking = BookingItem.objects.filter(
        pet_id=pet.id,
        booking__customer=request.user,
    ).filter(
        booking__status__in=[
            Booking.Status.SCHEDULED,
            Booking.Status.SERVICE_STARTED,
        ]
    ).exists() or BookingItem.objects.filter(
        pet_id=pet.id,
        booking__customer=request.user,
        booking__status=Booking.Status.SERVICE_COMPLETED,
        booking__payment_status=Booking.PaymentStatus.UNPAID,
    ).exists()

    if has_active_booking:
        return JsonResponse(
            {"error": "Hewan tidak dapat dihapus karena masih memiliki booking aktif."},
            status=400,
        )

    pet.soft_delete()
    return JsonResponse({"message": "Hewan peliharaan berhasil dihapus."}, status=200)
