import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from pet.models import Pet
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

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

    # VALIDASI
    if not full_name:
        return JsonResponse(
            {"error": "Nama lengkap wajib diisi."},
            status=400
        )

    if not phone_number:
        return JsonResponse(
            {"error": "No HP wajib diisi."},
            status=400
        )

    if not phone_number.isdigit():
        return JsonResponse(
            {"error": "No HP hanya boleh berisi angka."},
            status=400
        )

    # Update hanya field yang boleh diubah
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

        # VALIDASI
        if not full_name:
            messages.error(request, "Nama lengkap wajib diisi.")
            return render(request, "user_profile/edit_profile.html")

        if not phone_number:
            messages.error(request, "No HP wajib diisi.")
            return render(request, "user_profile/edit_profile.html")

        if not phone_number.isdigit():
            messages.error(request, "No HP hanya boleh berisi angka.")
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
        Pet.objects.create(
            owner=request.user,
            name=request.POST.get('name'),
            jenis=request.POST.get('jenis'),
            ras=request.POST.get('ras'),
            berat=request.POST.get('berat'),
            umur=request.POST.get('umur'),
        )

        return redirect('user_profile:profile')

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

        # Validasi wajib
        if not all([name, ras, umur, berat]):
            return JsonResponse(
                {"error": "Field ini wajib diisi."},
                status=400
            )

        # Update tanpa mengubah jenis
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
    # Hanya boleh edit hewan milik sendiri
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    if request.method == "POST":
        name = request.POST.get("name")
        ras = request.POST.get("ras")
        umur = request.POST.get("umur")
        berat = request.POST.get("berat")

        # Validasi field wajib (sesuai acceptance criteria)
        if not name or not ras or not umur or not berat:
            messages.error(request, "Field ini wajib diisi.")
            return render(request, "edit_pet.html", {"pet": pet})

        # Update (jenis TIDAK diubah)
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
    """Menghapus data hewan peliharaan milik customer.
    - Customer hanya dapat menghapus hewan miliknya sendiri.
    - Hewan tidak dapat dihapus jika masih memiliki booking aktif (scheduled/on the way).
    """
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    # TODO: Uncomment when model Booking udh ada
    # from booking.models import Booking
    # active_bookings = Booking.objects.filter(
    #     pet=pet,
    #     status__in=['scheduled', 'on_the_way', 'in_progress']
    # )
    # if active_bookings.exists():
    #     messages.error(request, "Hewan tidak dapat dihapus karena masih memiliki booking aktif.")
    #     return redirect('user_profile:profile')

    if request.method == 'POST':
        pet.soft_delete()
        messages.success(request, "Hewan peliharaan berhasil dihapus.")
        return redirect('user_profile:profile')

    # GET request — shouldn't happen normally, redirect back
    return redirect('user_profile:profile')


@login_required
@require_http_methods(["DELETE"])
def delete_pet_api(request, pet_id):
    """API endpoint DELETE /api/pets/{pet_id} untuk menghapus data hewan peliharaan.
    - Customer hanya dapat menghapus hewan miliknya sendiri.
    - Mengembalikan 400 jika hewan masih terikat booking aktif.
    - Mengembalikan 200 jika berhasil dihapus.
    """
    try:
        pet = Pet.objects.get(id=pet_id, owner=request.user)
    except Pet.DoesNotExist:
        return JsonResponse({"error": "Hewan tidak ditemukan."}, status=404)

    # TODO: Uncomment when model Booking udh ada
    # from booking.models import Booking
    # active_bookings = Booking.objects.filter(
    #     pet=pet,
    #     status__in=['scheduled', 'on_the_way', 'in_progress']
    # )
    # if active_bookings.exists():
    #     return JsonResponse(
    #         {"error": "Hewan tidak dapat dihapus karena masih memiliki booking aktif."},
    #         status=400
    #     )

    pet.soft_delete()
    return JsonResponse({"message": "Hewan peliharaan berhasil dihapus."}, status=200)