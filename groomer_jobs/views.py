from datetime import date, datetime, timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from booking.models import Booking, BookingItem
from booking.utils import get_dog_size
from .models import GroomingServiceForm

@login_required
def daily_job_list(request):
    user = request.user

    if user.role != "groomer":
        return HttpResponseForbidden("Hanya groomer yang dapat mengakses halaman ini.")
    
    auto_cancel_expired_scheduled_bookings(user)

    # testing, balikin ke date.today() aja nanti
    offset_days = int(request.GET.get("days", 0))
    today = date.today() + timedelta(days=offset_days)
    
    task_statuses = [Booking.Status.SCHEDULED, Booking.Status.SERVICE_STARTED]

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

        if booking.status == Booking.Status.SERVICE_COMPLETED:
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
    pet_type = (pet.jenis or "").lower()

    if pet_type == "cat":
        return ""

    if pet_type == "dog":
        if pet.berat is None:
            return "-"
        return get_dog_size(float(pet.berat))

    return "-"

    return "-"

def booking_belongs_to_groomer(booking, user):
    return booking.groomer.user == user

def get_booking_end_datetime(booking):
    return timezone.make_aware(
        datetime.combine(booking.tanggal, booking.waktu_selesai)
    )
    
def auto_cancel_expired_scheduled_bookings(user):
    now = timezone.localtime()

    scheduled_bookings = Booking.objects.filter(
        groomer__user=user,
        status=Booking.Status.SCHEDULED,
    )

    expired_ids = []

    for booking in scheduled_bookings:
        booking_end = get_booking_end_datetime(booking)

        if now > booking_end:
            expired_ids.append(booking.id)

    if expired_ids:
        Booking.objects.filter(id__in=expired_ids).update(
            status=Booking.Status.CANCELLED,
            updated_at=now,
        )
        
def has_unfinished_previous_booking(booking):
    previous_booking = (
        Booking.objects.filter(
            groomer=booking.groomer,
            tanggal=booking.tanggal,
            waktu_mulai__lt=booking.waktu_mulai,
        )
        .exclude(status=Booking.Status.CANCELLED)
        .order_by("-waktu_mulai")
        .first()
    )

    if not previous_booking:
        return False

    return previous_booking.status != Booking.Status.SERVICE_COMPLETED

def get_start_block_reason(booking):
    if booking.status != Booking.Status.SCHEDULED:
        return "invalid_status"

    now = timezone.localtime()

    booking_start = timezone.make_aware(
        datetime.combine(booking.tanggal, booking.waktu_mulai)
    )

    booking_end = timezone.make_aware(
        datetime.combine(booking.tanggal, booking.waktu_selesai)
    )

    if now < booking_start:
        return "before_start_time"

    if now > booking_end:
        return "after_end_time"

    if has_unfinished_previous_booking(booking):
        return "previous_not_completed"

    return ""

def can_start_booking(booking):
    return get_start_block_reason(booking) == ""

def can_complete_booking(booking):
    if booking.status != Booking.Status.SERVICE_STARTED:
        return False

    now = timezone.localtime()

    booking_end = timezone.make_aware(
        datetime.combine(booking.tanggal, booking.waktu_selesai)
    )

    # boleh complete 15 menit sebelum selesai, antisipasi groomer selesai lebih cepat dari estimasi
    allowed_complete_time = booking_end - timedelta(minutes=15)

    return now >= allowed_complete_time

@login_required
def job_detail(request, booking_id):
    user = request.user

    if user.role != "groomer":
        return HttpResponseForbidden("Hanya groomer yang dapat mengakses halaman ini.")
    
    auto_cancel_expired_scheduled_bookings(user)

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer__user")
        .prefetch_related(
            "items__pet",
            "items__package",
            "items__additionals__additional",
            "items__grooming_service_form",
        ),
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
                "name": additional.additional_name if additional.additional_name else (additional.additional.name if additional.additional else "-"),
                "duration": additional.durasi,
                "harga": additional.harga,
            })
            total_pet_duration += additional.durasi

        # Add grooming_service_form fields if exists
        grooming_service_form = getattr(item, "grooming_service_form", None)
        if grooming_service_form:
            service_form_data = {
                "kondisi_bulu": grooming_service_form.kondisi_bulu,
                "kondisi_kulit": grooming_service_form.kondisi_kulit,
                "kondisi_telinga": grooming_service_form.kondisi_telinga,
                "kondisi_kuku": grooming_service_form.kondisi_kuku,
                "perilaku_hewan": grooming_service_form.perilaku_hewan,
                "catatan_tambahan": grooming_service_form.catatan_tambahan,
            }
        else:
            service_form_data = None

        pet_items.append({
            "booking_item_id": item.id,
            "pet_name": item.pet.name,
            "pet_type": item.pet.jenis,
            "pet_size": get_pet_size_label(item.pet),
            "package_name": item.package_name if item.package_name else (item.package.name if item.package else "-"),
            "package_duration": item.durasi_paket,
            "package_price": item.harga_paket,
            "additionals": additionals,
            "total_pet_duration": total_pet_duration,
            "subtotal": item.subtotal,
            "already_has_note": grooming_service_form is not None,
            "service_form": service_form_data,
        })

    service_type_label = "Home Service" if booking.service_type == "home" else "Clinic Service"

    total_price = sum(item.subtotal for item in booking.items.all())
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
        "total_price": total_price,
        "show_start_service": booking.status == Booking.Status.SCHEDULED,
        "show_complete_service": booking.status == Booking.Status.SERVICE_STARTED,
        "can_start_service": can_start_booking(booking),
        "start_block_reason": get_start_block_reason(booking),
        "can_complete_service": can_complete_booking(booking),
        "can_show_pet_note_button": booking.status == Booking.Status.SERVICE_STARTED,
        "all_forms_completed": all_grooming_forms_completed(booking),
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

    if booking.status == Booking.Status.CANCELLED:
        messages.error(request, "Booking yang dibatalkan tidak dapat diubah statusnya.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    if booking.status == Booking.Status.SERVICE_COMPLETED:
        messages.error(request, "Booking yang sudah selesai tidak dapat diubah lagi.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    next_action = request.POST.get("action")

    if next_action == "start_service":
        auto_cancel_expired_scheduled_bookings(user)
        booking.refresh_from_db()
        
        if booking.status == Booking.Status.CANCELLED:
            messages.error(request, "Booking sudah melewati waktu selesai dan otomatis dibatalkan.")
            return redirect("groomer_jobs:daily_job_list")

        start_block_reason = get_start_block_reason(booking)

        if start_block_reason:
            if start_block_reason == "previous_not_completed":
                messages.error(request, "Layanan belum dapat dimulai karena pekerjaan sebelumnya belum selesai.")
            elif start_block_reason == "before_start_time":
                messages.error(request, "Layanan hanya dapat dimulai sesuai waktu pada jadwal.")
            elif start_block_reason == "after_end_time":
                messages.error(request, "Booking sudah melewati waktu selesai dan tidak dapat dimulai.")
            else:
                messages.error(request, "Layanan tidak dapat dimulai.")

            return redirect("groomer_jobs:job_detail", booking_id=booking.id)

        booking.status = Booking.Status.SERVICE_STARTED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Status layanan berhasil diperbarui menjadi Service started.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    if next_action == "complete_service":
        if not can_complete_booking(booking):
            messages.error(request, "Layanan hanya dapat diselesaikan minimal 15 menit sebelum waktu selesai pada jadwal.")
            return redirect("groomer_jobs:job_detail", booking_id=booking.id)

        if not all_grooming_forms_completed(booking):
            detail_url = reverse("groomer_jobs:job_detail", kwargs={"booking_id": booking.id})
            return redirect(f"{detail_url}?error=incomplete_form")

        booking.status = Booking.Status.SERVICE_COMPLETED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Status layanan berhasil diperbarui menjadi Service completed.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    messages.error(request, "Aksi perubahan status tidak valid.")
    return redirect("groomer_jobs:job_detail", booking_id=booking.id)

def is_groomer(user):
    return user.is_authenticated and user.role == "groomer"


def can_access_service_form(booking, user):
    return booking.groomer.user == user and booking.status == Booking.Status.SERVICE_STARTED


def booking_item_belongs_to_booking(booking_item, booking):
    return booking_item.booking_id == booking.id


def booking_item_belongs_to_groomer(booking_item, user):
    return booking_item.booking.groomer.user == user


def booking_item_already_has_form(booking_item):
    return hasattr(booking_item, "grooming_service_form")


def all_grooming_forms_completed(booking):
    total_items = booking.items.count()
    completed_forms = GroomingServiceForm.objects.filter(
        booking_item__booking=booking
    ).count()
    return total_items > 0 and total_items == completed_forms

@login_required
def grooming_service_form(request, booking_id, booking_item_id):
    user = request.user

    if not is_groomer(user):
        return HttpResponseForbidden("Hanya groomer yang dapat mengakses form layanan.")

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer__user")
        .prefetch_related("items__pet", "items__package", "items__additionals__additional"),
        id=booking_id,
    )

    if booking.groomer.user != user:
        return HttpResponseForbidden("Anda tidak dapat mengakses booking milik groomer lain.")

    if booking.status != Booking.Status.SERVICE_STARTED :
        messages.error(request, "Form layanan hanya dapat diakses saat status booking service started.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    booking_item = get_object_or_404(
        BookingItem.objects.select_related("pet", "package", "booking", "booking__customer", "booking__groomer__user"),
        id=booking_item_id,
        booking=booking,
    )

    if booking_item_already_has_form(booking_item):
        messages.error(request, "Catatan grooming untuk hewan ini sudah pernah diisi.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    context = {
        "booking": booking,
        "booking_item": booking_item,
        "pet": booking_item.pet,
        "owner_name": booking.customer.full_name,
        "groomer_name": booking.groomer.user.full_name,
        "service_type_label": "Home Service" if booking.service_type == "home" else "Clinic Service",
        "time_range": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
        "errors": {},
        "old": {},
    }

    return render(request, "groomer_jobs/grooming_service_form.html", context)

@login_required
def submit_grooming_service_form(request, booking_id, booking_item_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = request.user

    if not is_groomer(user):
        return HttpResponseForbidden("Hanya groomer yang dapat mengisi form layanan.")

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer__user"),
        id=booking_id,
    )

    if booking.groomer.user != user:
        return HttpResponseForbidden("Anda tidak dapat mengisi form booking milik groomer lain.")

    if booking.status != Booking.Status.SERVICE_STARTED:
        messages.error(request, "Form layanan hanya dapat disimpan saat status booking service started.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    booking_item = get_object_or_404(
        BookingItem.objects.select_related("pet", "package", "booking"),
        id=booking_item_id,
        booking=booking,
    )

    if GroomingServiceForm.objects.filter(booking_item=booking_item).exists():
        messages.error(request, "Catatan grooming untuk hewan ini sudah pernah diisi.")
        return redirect("groomer_jobs:job_detail", booking_id=booking.id)

    kondisi_bulu = request.POST.get("kondisi_bulu", "").strip()
    kondisi_kulit = request.POST.get("kondisi_kulit", "").strip()
    kondisi_telinga = request.POST.get("kondisi_telinga", "").strip()
    kondisi_kuku = request.POST.get("kondisi_kuku", "").strip()
    perilaku_hewan = request.POST.get("perilaku_hewan", "").strip()
    catatan_tambahan = request.POST.get("catatan_tambahan", "").strip()
    foto_bukti_layanan = None  # Field foto sudah tidak digunakan

    errors = {}

    if not kondisi_bulu:
        errors["kondisi_bulu"] = "Kondisi bulu wajib diisi."
    if not kondisi_kulit:
        errors["kondisi_kulit"] = "Kondisi kulit wajib diisi."
    if not kondisi_telinga:
        errors["kondisi_telinga"] = "Kondisi telinga wajib diisi."
    if not kondisi_kuku:
        errors["kondisi_kuku"] = "Kondisi kuku wajib diisi."
    if not perilaku_hewan:
        errors["perilaku_hewan"] = "Perilaku hewan wajib diisi."


    if errors:
        context = {
            "booking": booking,
            "booking_item": booking_item,
            "pet": booking_item.pet,
            "owner_name": booking.customer.full_name,
            "groomer_name": booking.groomer.user.full_name,
            "service_type_label": "Home Service" if booking.service_type == "home" else "Clinic Service",
            "time_range": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
            "errors": errors,
            "old": {
                "kondisi_bulu": kondisi_bulu,
                "kondisi_kulit": kondisi_kulit,
                "kondisi_telinga": kondisi_telinga,
                "kondisi_kuku": kondisi_kuku,
                "perilaku_hewan": perilaku_hewan,
                "catatan_tambahan": catatan_tambahan,
            },
        }
        return render(request, "groomer_jobs/grooming_service_form.html", context, status=400)

    with transaction.atomic():
        GroomingServiceForm.objects.create(
            booking_item=booking_item,
            kondisi_bulu=kondisi_bulu,
            kondisi_kulit=kondisi_kulit,
            kondisi_telinga=kondisi_telinga,
            kondisi_kuku=kondisi_kuku,
            perilaku_hewan=perilaku_hewan,
            catatan_tambahan=catatan_tambahan or None,
            foto_bukti_layanan=foto_bukti_layanan,
        )

    messages.success(request, "Catatan grooming berhasil disimpan.")

    if all_grooming_forms_completed(booking):
        return redirect(f"{reverse('groomer_jobs:job_detail', kwargs={'booking_id': booking.id})}?all_forms_completed=1")

    return redirect("groomer_jobs:job_detail", booking_id=booking.id)