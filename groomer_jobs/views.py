from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from booking.models import Booking


@login_required
def daily_job_list(request):
    user = request.user

    if user.role != "groomer":
        return HttpResponseForbidden("Hanya groomer yang dapat mengakses halaman ini.")

    # testing, balikin ke date.today() aja nanti
    offset_days = int(request.GET.get("days", 0))
    today = date.today() + timedelta(days=offset_days)
    
    task_statuses = ["scheduled", "service_started"]

    bookings = (
        Booking.objects.filter(
            groomer__user=user,
            tanggal=today
        )
        .exclude(status="cancelled")
        .select_related("customer", "groomer__user")
        .prefetch_related("items__pet")
        .order_by("waktu_mulai")
    )

    today_tasks = []
    today_history = []

    for booking in bookings:
        pets = [
            f"{item.pet.name} ({item.pet.jenis})"
            for item in booking.items.all()
        ]

        pet_names = ", ".join(pets) if pets else "-"

        data = {
            "id": booking.id,
            "time_range": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
            "owner_name": booking.customer.full_name,
            "pet_names": pet_names,
            "service_type_label": "Home Service" if booking.service_type == "home" else "Clinic Service",
            "status": booking.status,
            "status_label": booking.get_status_display(),
        }

        if booking.status == "service_completed":
            today_history.append(data)
        elif booking.status in task_statuses:
            today_tasks.append(data)

    groomer_profile = getattr(user, "groomer_profile", None)

    context = {
        "page_title": "Daftar Pekerjaan Hari Ini",
        "today": today,
        "groomer_name": user.full_name,
        "groomer_phone": user.phone_number,
        "groomer_service_type": groomer_profile.service_type if groomer_profile else "-",
        "unfinished_count": len(today_tasks),
        "completed_count": len(today_history),
        "today_tasks": today_tasks,
        "today_history": today_history,
    }

    return render(request, "groomer_jobs/daily_job_list.html", context)

def get_pet_size_label(pet):
    """
    Menghitung size hewan berdasarkan aturan, nanati ganti pakai field size dari model Pet
    - Cat: tidak tampilkan size
    - Dog:
        S  = 2-10 kg
        M  = 11-25 kg
        L  = 26-45 kg
        XL = >45 kg
    """
    pet_type = (pet.jenis or "").lower()
    weight = pet.berat

    if pet_type == "cat":
        return ""

    if pet_type == "dog":
        if weight is None:
            return "-"
        if 2 <= weight <= 10:
            return "S"
        if 11 <= weight <= 25:
            return "M"
        if 26 <= weight <= 45:
            return "L"
        if weight > 45:
            return "XL"

    return "-"

def booking_belongs_to_groomer(booking, user):
    return booking.groomer.user == user


def can_start_booking(booking):
    return booking.status == "scheduled"


def can_complete_booking(booking):
    return booking.status == "service_started"

def all_grooming_forms_completed(booking):
    """
    TODO:
    Ganti logic ini saat model catatan grooming / form layanan sudah tersedia.

    Harusnya return True jika SEMUA hewan pada booking ini sudah punya
    catatan grooming untuk booking yang sedang berjalan.
    """
    return False

@login_required
def job_detail(request, booking_id):
    user = request.user

    if user.role != "groomer":
        return HttpResponseForbidden("Hanya groomer yang dapat mengakses halaman ini.")

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer__user")
        .prefetch_related("items__pet", "items__package", "items__additionals__additional"),
        id=booking_id,
    )

    # Groomer hanya boleh akses booking miliknya sendiri
    if booking.groomer.user != user:
        return HttpResponseForbidden("Anda tidak dapat mengakses booking milik groomer lain.")

    pet_items = []
    for item in booking.items.all():
        additionals = []
        total_pet_duration = item.durasi_paket

        for additional in item.additionals.all():
            additionals.append({
                "name": additional.additional.name,
                "duration": additional.durasi,
            })
            total_pet_duration += additional.durasi

        pet_items.append({
            "booking_item_id": item.id,
            "pet_name": item.pet.name,
            "pet_type": item.pet.jenis,
            "pet_size": get_pet_size_label(item.pet),  # TODO: butuh field size pada model Pet
            "package_name": item.package.name,
            "package_duration": item.durasi_paket,
            "additionals": additionals,
            "total_pet_duration": total_pet_duration,

            # TODO: butuh model catatan grooming / grooming note
            # agar bisa cek apakah hewan ini sudah punya catatan atau belum
            "already_has_note": False,
        })

    service_type_label = "Home Service" if booking.service_type == "home" else "Clinic Service"

    context = {
        "booking": booking,
        "owner_name": booking.customer.full_name,
        "owner_phone": booking.customer.phone_number,
        "address": booking.alamat,
        "booking_note": booking.catatan,
        "service_type_label": service_type_label,
        "time_range": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
        "status": booking.status,
        "status_label": booking.get_status_display(),
        "total_duration": booking.total_durasi,
        "pet_items": pet_items,
        "can_start_service": can_start_booking(booking),
        "can_complete_service": can_complete_booking(booking),
        # Tombol isi form layanan per hewan, skrg hanya based on status booking dulu
        "can_show_pet_note_button": booking.status == "service_started",
    }

    return render(request, "groomer_jobs/job_detail.html", context)


@login_required
def update_booking_status(request, booking_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = request.user

    if user.role != "groomer":
        return HttpResponseForbidden("Hanya groomer yang dapat mengubah status layanan.")

    booking = get_object_or_404(
        Booking.objects.select_related("groomer__user"),
        id=booking_id,
    )

    if not booking_belongs_to_groomer(booking, user):
        return HttpResponseForbidden("Anda tidak dapat mengubah booking milik groomer lain.")

    if booking.status == "cancelled":
        messages.error(request, "Booking yang dibatalkan tidak dapat diubah statusnya.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    if booking.status == "service_completed":
        messages.error(request, "Booking yang sudah selesai tidak dapat diubah lagi.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    next_action = request.POST.get("action")

    if next_action == "start_service":
        if not can_start_booking(booking):
            messages.error(request, "Status booking ini tidak dapat diubah ke service started.")
            return redirect("groomer_jobs:job_detail", booking_id=booking.id)

        booking.status = "service_started"
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Status layanan berhasil diperbarui menjadi Service started.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    if next_action == "complete_service":
        if not can_complete_booking(booking):
            messages.error(request, "Status booking ini tidak dapat diubah ke service completed.")
            return redirect("groomer_jobs:job_detail", booking_id=booking.id)

        if not all_grooming_forms_completed(booking):
            return redirect(f"/groomer-jobs/bookings/{booking.id}/?error=incomplete_form")

        booking.status = "service_completed"
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Status layanan berhasil diperbarui menjadi Service completed.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    messages.error(request, "Aksi perubahan status tidak valid.")
    return redirect("groomer_jobs:job_detail", booking_id=booking.id)