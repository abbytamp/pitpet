from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .forms import BookingReviewForm
from .models import BookingReview
@login_required
def booking_review_create(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user"),
        id=booking_id,
        customer=request.user,
    )
    # Hanya bisa review jika status completed & paid
    if not (booking.status == Booking.Status.SERVICE_COMPLETED and booking.payment_status == Booking.PaymentStatus.PAID):
        messages.error(request, "Review hanya dapat diberikan untuk booking yang sudah selesai dan sudah dibayar.")
        return redirect("booking:history_detail", booking_id=booking.id)

    # Sudah ada review?
    if hasattr(booking, "review"):
        messages.error(request, "Review sudah pernah dibuat untuk booking ini.")
        return redirect("booking:history_detail", booking_id=booking.id)


    if request.method == "POST":
        form = BookingReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.customer = request.user
            review.save()
            messages.success(request, "Review berhasil dikirim")
            return redirect("booking:history_detail", booking_id=booking.id)
    else:
        form = BookingReviewForm()

    return render(request, "booking/review_form.html", {"form": form, "booking": booking})

# Cancel booking oleh staff (pastikan ada di bawah dan tidak error import)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

@login_required
def staff_cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    now = timezone.localtime()
    # Hanya staff dan status scheduled, tanpa cek waktu mulai
    if (
        request.user.role == User.Role.STAFF and
        booking.status == Booking.Status.SCHEDULED
    ):
        if request.method == "POST":
            booking.status = Booking.Status.CANCELLED
            booking.save()
            messages.success(request, "Booking berhasil dibatalkan.")
            return redirect('booking:staff_booking_detail', booking_id=booking_id)
        # GET: tampilkan konfirmasi
        return render(request, "booking/staff_cancel_confirm.html", {"booking": booking})
    else:
        messages.error(request, "Booking tidak dapat dibatalkan.")
        return redirect('booking:staff_booking_detail', booking_id=booking_id)
        
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import models, transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.models import Groomer, User
from booking.models import Booking, BookingItem, BookingItemAdditional
from booking.utils import (
    CLINIC_ADDRESS,
    MAX_BOOKING_DAYS,
    TRANSPORT_FEES,
    calculate_end_time,
    get_first_bookable_date,
    get_available_slots,
    get_package_price_for_pet,
    get_pet_animal_type,
    get_dog_size,
    is_working_day,
    is_slot_available,
    meets_minimum_lead_time,
)
from packages.models import Package
from pet.models import Pet


@login_required
def staff_booking_schedule(request):
    # Hanya staff operasional yang boleh akses
    if not request.user.is_authenticated or request.user.role != User.Role.STAFF:
        return redirect('login')

    # Pilihan tipe layanan dan tanggal
    service_type = request.GET.get('service_type', Booking.ServiceType.CLINIC)
    tanggal_str = request.GET.get('tanggal')
    if tanggal_str:
        try:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
        except ValueError:
            tanggal = timezone.localdate()
    else:
        tanggal = timezone.localdate()

    is_off_day = tanggal.weekday() == 0

    if is_off_day:
        return render(
            request,
            'booking/staff_booking_schedule_list.html',
            {
                'groomers': [],
                'groomer_schedules': {},
                'service_type': service_type,
                'tanggal': tanggal.strftime('%Y-%m-%d'),
                'is_off_day': True,
            },
        )

    # Ambil semua groomer aktif untuk tipe layanan
    # Jika ingin menampilkan groomer yang sudah dihapus untuk tanggal sebelum/sama dengan deleted_at,
    # gunakan all_objects dan filter manual
    from django.db.models import Q
    groomers = Groomer.all_objects.select_related('user').filter(
        Q(is_deleted=False, service_type=service_type) |
        Q(is_deleted=True, service_type=service_type, deleted_at__gte=datetime.combine(tanggal, datetime.min.time()))
    )

    # Tentukan slot waktu per 30 menit (mengikuti aturan booking)
    from booking.utils import WORK_START, WORK_END, SLOT_MINUTES
    slot_times = []
    current = datetime.combine(tanggal, WORK_START)
    end = datetime.combine(tanggal, WORK_END)
    while current < end:
        slot_times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=SLOT_MINUTES)

    # Ambil semua booking pada tanggal & tipe layanan
    bookings = (
        Booking.objects.filter(
            tanggal=tanggal,
            service_type=service_type,
            groomer__in=groomers,
        )
        .select_related('customer', 'groomer', 'groomer__user')
        .prefetch_related('items__pet', 'items__package')
    )

    def _slot_in_working_hours(slot_str):
        return slot_str in slot_times

    groomer_schedules = {}
    for groomer in groomers:
        groomer_bookings = [
            booking
            for booking in bookings
            if booking.groomer_id == groomer.id and booking.status != Booking.Status.CANCELLED
        ]
        groomer_bookings.sort(key=lambda booking: booking.waktu_mulai)

        booking_start_map = {}
        buffer_map = {}
        hidden_slots = set()

        for booking in groomer_bookings:
            start_str = booking.waktu_mulai.strftime('%H:%M')
            end_str = booking.waktu_selesai.strftime('%H:%M')
            booking_start_map[start_str] = booking

            current_time = datetime.combine(tanggal, booking.waktu_mulai) + timedelta(minutes=SLOT_MINUTES)
            booking_end = datetime.combine(tanggal, booking.waktu_selesai)
            while current_time < booking_end:
                hidden_slots.add(current_time.strftime('%H:%M'))
                current_time += timedelta(minutes=SLOT_MINUTES)

            if booking.service_type == Booking.ServiceType.HOME:
                before_slot = (datetime.combine(tanggal, booking.waktu_mulai) - timedelta(minutes=SLOT_MINUTES)).strftime('%H:%M')

                if _slot_in_working_hours(before_slot):
                    buffer_map.setdefault(before_slot, set()).add(booking.booking_code)

        schedule = []
        for slot_time in slot_times:
            if slot_time in hidden_slots:
                continue

            booking = booking_start_map.get(slot_time)
            if booking:
                if booking.items.exists():
                    pet_names = [item.pet.name for item in booking.items.all()]
                    pet_name_display = ' + '.join(pet_names)
                else:
                    pet_name_display = '-'

                schedule.append({
                    'type': 'booking',
                    'start': booking.waktu_mulai.strftime('%H:%M'),
                    'end': booking.waktu_selesai.strftime('%H:%M'),
                    'customer': booking.customer,
                    'pet_name': pet_name_display,
                    'status_display': booking.get_status_display(),
                    'payment_status_display': booking.get_payment_status_display(),
                    'booking_id': booking.id,
                })
                continue

            booking_codes = sorted(buffer_map.get(slot_time, set()))
            if booking_codes:
                schedule.append({
                    'type': 'buffer',
                    'start': slot_time,
                    'booking_codes': booking_codes,
                    'booking_label': booking_codes[0] if len(booking_codes) == 1 else 'Buffer',
                })
                continue

            schedule.append({
                'type': 'available',
                'start': slot_time,
            })

        groomer_schedules[groomer.id] = schedule

    context = {
        'groomers': groomers,
        'groomer_schedules': groomer_schedules,
        'service_type': service_type,
        'tanggal': tanggal.strftime('%Y-%m-%d'),
        'is_off_day': False,
    }
    return render(request, 'booking/staff_booking_schedule_list.html', context)


@login_required
def staff_booking_detail(request, booking_id):
    if not request.user.is_authenticated or request.user.role != User.Role.STAFF:
        return HttpResponseForbidden("403 Forbidden: hanya staff operasional yang dapat mengakses halaman ini.")

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user")
        .prefetch_related("items__pet", "items__package", "items__additionals__additional"),
        id=booking_id,
    )

    pet_items = []
    for item in booking.items.all():
        additionals = []
        total_pet_duration = item.durasi_paket

        for additional in item.additionals.all():
            additionals.append({
                "name": additional.additional_name if additional.additional_name else (additional.additional.name if additional.additional else "-"),
                "duration": additional.durasi,
            })
            total_pet_duration += additional.durasi

        pet_items.append({
            "pet_name": item.pet.name,
            "pet_type": item.pet.jenis,
            "pet_size": _get_pet_size_label(item.pet),
            "package_name": item.package_name if item.package_name else (item.package.name if item.package else "-"),
            "package_duration": item.durasi_paket,
            "additionals": additionals,
            "total_pet_duration": total_pet_duration,
        })

    grooming_notes = booking.grooming_notes if booking.grooming_notes else "belum tersedia"

    context = {
        "booking": booking,
        "owner_name": booking.customer.full_name,
        "owner_phone": booking.customer.phone_number,
        "service_type_label": booking.get_service_type_display(),
        "groomer_name": booking.groomer.user.full_name,
        "groomer_phone": booking.groomer.user.phone_number,
        "address": booking.alamat,
        "status": booking.status,
        "status_label": booking.get_status_display(),
        "payment_status": booking.payment_status,
        "payment_status_label": booking.get_payment_status_display(),
        "time_range": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
        "total_duration": booking.total_durasi,
        "total_harga": f"{booking.total_harga:,.0f}".replace(",", "."),
        "pet_items": pet_items,
        "can_cancel": booking.status == Booking.Status.SCHEDULED,
        "can_mark_paid": (
            booking.payment_status == Booking.PaymentStatus.UNPAID
            and booking.status == Booking.Status.SERVICE_COMPLETED
        ),
        "grooming_notes": grooming_notes,
    }

    return render(request, "booking/staff_booking_detail.html", context)

# Calculate size label (nanti ganti dengan defined method di model pet)
def _get_pet_size_label(pet):
    pet_type = (pet.jenis or "").lower()

    if pet_type == "cat":
        return ""

    if pet_type == "dog":
        if pet.berat is None:
            return "-"
        return get_dog_size(float(pet.berat))

    return "-"

def _is_customer(user) -> bool:
    return user.is_authenticated and user.role == User.Role.CUSTOMER

def _is_staff_operational(user) -> bool:
    return user.is_authenticated and user.role == User.Role.STAFF

def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


ACTIVE_BOOKING_STATUSES = [
    Booking.Status.SCHEDULED,
    Booking.Status.SERVICE_STARTED,
]


@login_required
def booking_create(request):
    if not _is_customer(request.user):
        return redirect("login")

    pets = Pet.objects.filter(owner=request.user).order_by("name")
    blocked_pet_ids = set(
        BookingItem.objects.filter(
            booking__customer=request.user,
        )
        .filter(
            models.Q(booking__status__in=ACTIVE_BOOKING_STATUSES)
            | models.Q(booking__status=Booking.Status.SERVICE_COMPLETED, booking__payment_status=Booking.PaymentStatus.UNPAID)
        )
        .values_list("pet_id", flat=True)
        .distinct()
    )

    context = {
        "pets": pets,
        "blocked_pet_ids": blocked_pet_ids,
        "clinic_address": CLINIC_ADDRESS,
        "transport_fees": TRANSPORT_FEES,
        "min_date": get_first_bookable_date().isoformat(),
        "max_date": (timezone.localdate() + timedelta(days=MAX_BOOKING_DAYS)).isoformat(),
        "errors": {},
    }

    if request.method == "GET":
        return render(request, "booking/create.html", context)

    errors = {}

    service_type = request.POST.get("service_type", "").strip()
    groomer_id = request.POST.get("groomer_id", "").strip()
    tanggal_raw = request.POST.get("tanggal", "").strip()
    waktu_mulai_raw = request.POST.get("waktu_mulai", "").strip()
    alamat = request.POST.get("alamat", "").strip()
    catatan = request.POST.get("catatan", "").strip()
    payload_raw = request.POST.get("booking_payload", "").strip()

    if service_type not in [Booking.ServiceType.CLINIC, Booking.ServiceType.HOME]:
        errors["service_type"] = "Pilih jenis layanan terlebih dahulu."

    if not groomer_id:
        errors["groomer_id"] = "Pilih groomer terlebih dahulu."

    if not tanggal_raw:
        errors["tanggal"] = "Tanggal wajib dipilih."

    if not waktu_mulai_raw:
        errors["waktu_mulai"] = "Slot waktu wajib dipilih."

    if service_type == Booking.ServiceType.HOME and not alamat:
        errors["alamat"] = "Alamat wajib diisi untuk layanan home service."

    try:
        payload = json.loads(payload_raw) if payload_raw else {}
        raw_items = payload.get("items", [])
    except json.JSONDecodeError:
        raw_items = []
        errors["booking_payload"] = "Data booking tidak valid."

    if not raw_items:
        errors["booking_payload"] = "Pilih minimal satu hewan dan paket."

    selected_pet_ids = [_to_int(item.get("pet_id")) for item in raw_items if _to_int(item.get("pet_id")) > 0]

    customer_pets = {pet.id: pet for pet in Pet.objects.filter(owner=request.user, id__in=selected_pet_ids)}
    if selected_pet_ids and len(customer_pets) != len(set(selected_pet_ids)):
        errors["booking_payload"] = "Anda hanya dapat mem-booking hewan milik Anda sendiri."

    if selected_pet_ids and blocked_pet_ids.intersection(selected_pet_ids):
        errors["booking_payload"] = "Salah satu hewan yang dipilih sedang memiliki booking aktif."

    groomer = None
    if groomer_id:
        groomer = (
            Groomer.objects.select_related("user")
            .filter(
                id=_to_int(groomer_id),
                service_type=service_type,
                user__is_active=True,
            )
            .first()
        )
        if not groomer:
            errors["groomer_id"] = "Groomer tidak ditemukan atau tidak aktif untuk layanan ini."

    tanggal = None
    if tanggal_raw:
        try:
            tanggal = datetime.strptime(tanggal_raw, "%Y-%m-%d").date()
            today = timezone.localdate()
            max_date = today + timedelta(days=MAX_BOOKING_DAYS)
            if tanggal < today or tanggal > max_date:
                errors["tanggal"] = "Tanggal booking harus antara hari ini hingga 7 hari ke depan."
            elif not is_working_day(tanggal):
                errors["tanggal"] = "Hari Senin libur. Silakan pilih tanggal lain."
        except ValueError:
            errors["tanggal"] = "Format tanggal tidak valid."

    waktu_mulai = None
    if waktu_mulai_raw:
        try:
            waktu_mulai = datetime.strptime(waktu_mulai_raw, "%H:%M").time()
        except ValueError:
            errors["waktu_mulai"] = "Format slot waktu tidak valid."

    item_blueprints = []
    total_durasi = 0
    total_harga = Decimal("0")

    package_ids = [_to_int(item.get("package_id")) for item in raw_items if _to_int(item.get("package_id")) > 0]
    additional_ids = []
    for item in raw_items:
        for additional_id in item.get("additional_ids", []):
            add_id = _to_int(additional_id)
            if add_id > 0:
                additional_ids.append(add_id)

    packages = {
        p.id: p
        for p in Package.objects.prefetch_related("prices").filter(
            id__in=set(package_ids),
            package_type=Package.PackageType.GROOMING,
            is_deleted=False,
        )
    }
    additionals = {
        p.id: p
        for p in Package.objects.prefetch_related("prices").filter(
            id__in=set(additional_ids),
            package_type=Package.PackageType.ADDITIONAL,
            is_deleted=False,
        )
    }

    for item in raw_items:
        pet_id = _to_int(item.get("pet_id"))
        package_id = _to_int(item.get("package_id"))
        additional_item_ids = [_to_int(x) for x in item.get("additional_ids", []) if _to_int(x) > 0]

        pet = customer_pets.get(pet_id)
        package = packages.get(package_id)

        if not pet or not package:
            errors["booking_payload"] = "Terdapat paket atau hewan yang tidak valid."
            continue

        pet_animal_type = get_pet_animal_type(pet)
        if package.animal_type != pet_animal_type:
            errors["booking_payload"] = "Paket tidak sesuai dengan jenis hewan."
            continue

        package_price = get_package_price_for_pet(package, pet)
        if package_price <= 0:
            errors["booking_payload"] = "Harga paket tidak valid untuk hewan yang dipilih."
            continue

        item_duration = int(package.duration_min)
        item_subtotal = Decimal(package_price)

        item_additionals = []
        for add_id in additional_item_ids:
            add_pkg = additionals.get(add_id)
            if not add_pkg:
                errors["booking_payload"] = "Additional service tidak ditemukan."
                continue
            if add_pkg.animal_type != pet_animal_type:
                errors["booking_payload"] = "Additional service tidak sesuai dengan jenis hewan."
                continue

            add_price = get_package_price_for_pet(add_pkg, pet)
            if add_price <= 0:
                errors["booking_payload"] = "Harga additional service tidak valid."
                continue

            item_duration += int(add_pkg.duration_min)
            item_subtotal += Decimal(add_price)
            item_additionals.append(
                {
                    "additional": add_pkg,
                    "harga": Decimal(add_price),
                    "durasi": int(add_pkg.duration_min),
                }
            )

        item_blueprints.append(
            {
                "pet": pet,
                "package": package,
                "harga_paket": Decimal(package_price),
                "durasi_paket": int(package.duration_min),
                "subtotal": item_subtotal,
                "additionals": item_additionals,
                "item_duration": item_duration,
            }
        )
        total_durasi += item_duration
        total_harga += item_subtotal

    if total_durasi <= 0:
        errors["booking_payload"] = "Total durasi booking tidak valid."

    if groomer and tanggal and waktu_mulai and total_durasi > 0:
        if not meets_minimum_lead_time(tanggal, waktu_mulai):
            errors["waktu_mulai"] = "Booking hanya bisa dibuat minimal H+2 jam dari sekarang."
        elif not is_slot_available(groomer.id, tanggal, total_durasi, service_type, waktu_mulai):
            errors["waktu_mulai"] = "Slot sudah terisi, silakan pilih slot lain."

    if errors:
        context.update(
            {
                "errors": errors,
                "old": {
                    "service_type": service_type,
                    "groomer_id": groomer_id,
                    "tanggal": tanggal_raw,
                    "waktu_mulai": waktu_mulai_raw,
                    "alamat": alamat,
                    "catatan": catatan,
                    "booking_payload": payload_raw,
                },
            }
        )
        return render(request, "booking/create.html", context, status=400)

    with transaction.atomic():
        # Lock groomer row first so two submissions for same groomer are serialized.
        locked_groomer = Groomer.objects.select_for_update().get(id=groomer.id)

        if not meets_minimum_lead_time(tanggal, waktu_mulai):
            context.update(
                {
                    "errors": {
                        "waktu_mulai": "Booking hanya bisa dibuat minimal H+2 jam dari sekarang."
                    },
                    "old": {
                        "service_type": service_type,
                        "groomer_id": groomer_id,
                        "tanggal": tanggal_raw,
                        "waktu_mulai": waktu_mulai_raw,
                        "alamat": alamat,
                        "catatan": catatan,
                        "booking_payload": payload_raw,
                    },
                }
            )
            return render(request, "booking/create.html", context, status=409)

        if not is_slot_available(locked_groomer.id, tanggal, total_durasi, service_type, waktu_mulai):
            context.update(
                {
                    "errors": {
                        "waktu_mulai": "Slot sudah terisi oleh booking lain. Silakan pilih slot baru."
                    },
                    "old": {
                        "service_type": service_type,
                        "groomer_id": groomer_id,
                        "tanggal": tanggal_raw,
                        "waktu_mulai": waktu_mulai_raw,
                        "alamat": alamat,
                        "catatan": catatan,
                        "booking_payload": payload_raw,
                    },
                }
            )
            return render(request, "booking/create.html", context, status=409)

        booking = Booking.objects.create(
            customer=request.user,
            service_type=service_type,
            groomer=locked_groomer,
            tanggal=tanggal,
            waktu_mulai=waktu_mulai,
            waktu_selesai=calculate_end_time(waktu_mulai, total_durasi, tanggal),
            total_durasi=total_durasi,
            total_harga=total_harga,
            alamat=alamat if service_type == Booking.ServiceType.HOME else None,
            catatan=catatan or None,
            status=Booking.Status.SCHEDULED,
            payment_status=Booking.PaymentStatus.UNPAID,
        )

        booking_items = []
        booking_item_additionals = []
        for item in item_blueprints:
            booking_item = BookingItem(
                booking=booking,
                pet=item["pet"],
                package=item["package"],
                package_name=item["package"].name,
                harga_paket=item["harga_paket"],
                durasi_paket=item["durasi_paket"],
                subtotal=item["subtotal"],
            )
            booking_items.append(booking_item)

        created_items = BookingItem.objects.bulk_create(booking_items)

        for idx, created_item in enumerate(created_items):
            for add in item_blueprints[idx]["additionals"]:
                booking_item_additionals.append(
                    BookingItemAdditional(
                        booking_item=created_item,
                        additional=add["additional"],
                        additional_name=add["additional"].name,
                        harga=add["harga"],
                        durasi=add["durasi"],
                    )
                )

        if booking_item_additionals:
            BookingItemAdditional.objects.bulk_create(booking_item_additionals)

    return redirect("booking:success", booking_id=booking.id)


@login_required
def booking_success(request, booking_id: int):
    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user")
        .prefetch_related("items__pet", "items__package", "items__additionals__additional"),
        id=booking_id,
        customer=request.user,
    )

    return render(
        request,
        "booking/success.html",
        {
            "booking": booking,
            "clinic_address": CLINIC_ADDRESS,
        },
    )


@login_required
def booking_detail(request, booking_id: int):
    if not _is_customer(request.user):
        return redirect("login")

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user")
        .prefetch_related("items__pet", "items__package", "items__additionals__additional"),
        id=booking_id,
    )

    if booking.customer_id != request.user.id:
        return HttpResponseForbidden("403 Forbidden: booking ini bukan milik Anda.")

    return render(
        request,
        "booking/detail.html",
        {
            "booking": booking,
            "clinic_address": CLINIC_ADDRESS,
        },
    )


@login_required
def cancel_booking(request, booking_id):
    if not _is_customer(request.user):
        return redirect("login")

    booking = get_object_or_404(
        Booking.objects.select_related("groomer", "groomer__user"),
        id=booking_id,
        customer=request.user,
    )

    if booking.status != Booking.Status.SCHEDULED:
        messages.error(request, booking.cancel_block_message)
        return redirect("booking:detail", booking_id=booking.id)

    if not booking.can_cancel:
        messages.error(request, booking.cancel_block_message)
        return redirect("booking:detail", booking_id=booking.id)

    if request.method == "POST":
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, "Booking berhasil dibatalkan.")
        return redirect("booking:my_bookings")

    return render(request, "booking/cancel_confirm.html", {"booking": booking})



# Halaman booking aktif
@login_required
def my_bookings(request):
    if not _is_customer(request.user):
        return redirect("login")

    bookings = (
        Booking.objects.select_related("groomer", "groomer__user")
        .prefetch_related("items__pet")
        .filter(customer=request.user)
        .filter(
            models.Q(status__in=[Booking.Status.SCHEDULED, Booking.Status.SERVICE_STARTED])
            | models.Q(status=Booking.Status.SERVICE_COMPLETED, payment_status=Booking.PaymentStatus.UNPAID)
        )
        .order_by("-tanggal", "-waktu_mulai")
    )

    return render(request, "booking/my_bookings.html", {"bookings": bookings})


@login_required
def reschedule_booking(request, booking_id):
    if not _is_customer(request.user):
        return redirect("login")

    booking = get_object_or_404(
        Booking.objects.select_related("groomer", "groomer__user")
        .prefetch_related("items__pet", "items__package"),
        id=booking_id,
        customer=request.user,
    )

    if booking.status != Booking.Status.SCHEDULED:
        messages.error(request, "Booking tidak dapat di-reschedule.")
        return redirect("booking:my_bookings")

    if booking.is_rescheduled:
        messages.error(request, "Booking sudah pernah di-reschedule sebelumnya.")
        return redirect("booking:my_bookings")

    now = timezone.localtime()
    booking_datetime = timezone.make_aware(datetime.combine(booking.tanggal, booking.waktu_mulai))
    if booking_datetime - now < timedelta(hours=2):
        messages.error(request, "Perubahan jadwal kurang dari 2 jam. Silakan hubungi staff untuk perubahan jadwal.")
        return redirect("booking:my_bookings")

    today = timezone.localdate()
    min_date = today.isoformat()
    max_date = (today + timedelta(days=MAX_BOOKING_DAYS)).isoformat()

    context = {
        "booking": booking,
        "groomer": booking.groomer,
        "groomer_name": booking.groomer.user.full_name,
        "service_type": booking.service_type,
        "service_type_display": booking.get_service_type_display(),
        "total_durasi": booking.total_durasi,
        "min_date": min_date,
        "max_date": max_date,
    }

    return render(request, "booking/reschedule_form.html", context)


@login_required
def api_reschedule_slots(request, booking_id):
    if not _is_customer(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    booking = get_object_or_404(
        Booking.objects.select_related("groomer"),
        id=booking_id,
        customer=request.user,
    )

    date_raw = request.GET.get("date", "").strip()
    if not date_raw:
        return JsonResponse({"error": "date wajib diisi."}, status=400)

    try:
        date_obj = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Format date tidak valid."}, status=400)

    today = timezone.localdate()
    if date_obj < today or date_obj > today + timedelta(days=MAX_BOOKING_DAYS):
        return JsonResponse({"error": "Tanggal di luar range booking."}, status=400)

    if not is_working_day(date_obj):
        return JsonResponse(
            {
                "slots": [],
                "message": "Hari Senin libur. Silakan pilih tanggal lain.",
            }
        )

    from .utils import get_available_slots

    groomer = booking.groomer
    duration = booking.total_durasi
    service_type = booking.service_type

    slots = get_available_slots(groomer.id, date_obj, duration, service_type)

    return JsonResponse({
        "booking_id": booking_id,
        "groomer_id": groomer.id,
        "duration": duration,
        "service_type": service_type,
        "date": str(date_obj),
        "slots": slots,
        "message": "" if slots else "Tidak ada slot tersedia untuk tanggal tersebut."
    })


@login_required
def reschedule_booking_submit(request, booking_id):
    if not _is_customer(request.user):
        return redirect("login")

    if request.method != "POST":
        return HttpResponseForbidden("Method not allowed")

    booking = get_object_or_404(
        Booking.objects.select_related("groomer"),
        id=booking_id,
        customer=request.user,
    )

    now = timezone.localtime()
    booking_datetime = timezone.make_aware(datetime.combine(booking.tanggal, booking.waktu_mulai))

    if booking.status != Booking.Status.SCHEDULED:
        messages.error(request, "Booking tidak dapat di-reschedule.")
        return redirect("booking:my_bookings")

    if booking.is_rescheduled:
        messages.error(request, "Booking sudah pernah di-reschedule sebelumnya.")
        return redirect("booking:my_bookings")

    if booking_datetime - now < timedelta(hours=2):
        messages.error(request, "Perubahan jadwal kurang dari 2 jam. Silakan hubungi staff untuk perubahan jadwal.")
        return redirect("booking:my_bookings")

    groomer_id_raw = request.POST.get("groomer_id", "").strip()
    tanggal_raw = request.POST.get("tanggal", "").strip()
    waktu_mulai_raw = request.POST.get("waktu_mulai", "").strip()

    if not groomer_id_raw:
        messages.error(request, "Groomer wajib dipilih.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    if not tanggal_raw:
        messages.error(request, "Tanggal wajib diisi.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    if not waktu_mulai_raw:
        messages.error(request, "Waktu mulai wajib dipilih.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    try:
        groomer_id = int(groomer_id_raw)
        tanggal = datetime.strptime(tanggal_raw, "%Y-%m-%d").date()
        waktu_mulai = datetime.strptime(waktu_mulai_raw, "%H:%M").time()
    except ValueError as e:
        messages.error(request, "Format groomer, tanggal, atau waktu tidak valid.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    today = timezone.localdate()
    max_date = today + timedelta(days=MAX_BOOKING_DAYS)
    if tanggal < today or tanggal > max_date:
        messages.error(request, "Tanggal booking harus antara hari ini hingga 7 hari ke depan.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    if not is_working_day(tanggal):
        messages.error(request, "Hari Senin libur. Silakan pilih tanggal lain.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    try:
        new_groomer = Groomer.objects.get(id=groomer_id, user__is_active=True)
    except Groomer.DoesNotExist:
        messages.error(request, "Groomer tidak valid atau tidak aktif.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    if not meets_minimum_lead_time(tanggal, waktu_mulai):
        messages.error(request, "Booking/reschedule hanya bisa dipilih minimal H+2 jam dari sekarang.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    if not is_slot_available(new_groomer.id, tanggal, booking.total_durasi, booking.service_type, waktu_mulai):
        messages.error(request, "Slot yang dipilih sudah terisi. Silakan pilih waktu lain.")
        return redirect("booking:reschedule_booking", booking_id=booking_id)

    end_time = calculate_end_time(waktu_mulai, booking.total_durasi, tanggal)

    if booking.original_tanggal is None:
        booking.original_tanggal = booking.tanggal
        booking.original_waktu_mulai = booking.waktu_mulai
        booking.original_waktu_selesai = booking.waktu_selesai

    booking.groomer = new_groomer
    booking.tanggal = tanggal
    booking.waktu_mulai = waktu_mulai
    booking.waktu_selesai = end_time
    booking.is_rescheduled = True
    booking.save()

    messages.success(request, f"Booking berhasil di-reschedule ke {new_groomer.user.full_name} pada {tanggal} {waktu_mulai} - {end_time}.")
    return redirect("booking:my_bookings")


# Halaman riwayat booking (hanya milik sendiri, status Paid & Cancelled, filter status)
@login_required
def booking_history(request):
    if not _is_customer(request.user):
        return redirect("login")

    status_filter = request.GET.get('status', 'all')

    bookings = Booking.objects.select_related("groomer", "groomer__user") \
        .prefetch_related("items__pet", "items__package") \
        .filter(customer=request.user) \
        .filter(
            models.Q(status=Booking.Status.CANCELLED) |
            (models.Q(status=Booking.Status.SERVICE_COMPLETED) & models.Q(payment_status=Booking.PaymentStatus.PAID))
        ) \
        .order_by("-tanggal", "-waktu_mulai")

    if status_filter == 'paid':
        bookings = bookings.filter(payment_status=Booking.PaymentStatus.PAID, status=Booking.Status.SERVICE_COMPLETED)
    elif status_filter == 'cancelled':
        bookings = bookings.filter(status=Booking.Status.CANCELLED)

    return render(request, "booking/history.html", {"bookings": bookings, "status_filter": status_filter})


@login_required
def booking_history_detail(request, booking_id):
    if not _is_customer(request.user):
        return redirect("login")

    from groomer_jobs.models import GroomingServiceForm

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user")
        .prefetch_related(
            "items__pet",
            "items__package",
            "items__additionals__additional",
        ),
        id=booking_id,
        customer=request.user,
    )

    is_history_booking = (
        booking.status == Booking.Status.CANCELLED
        or (
            booking.status == Booking.Status.SERVICE_COMPLETED
            and booking.payment_status == Booking.PaymentStatus.PAID
        )
    )
    if not is_history_booking:
        messages.error(request, "Booking ini belum masuk riwayat.")
        return redirect("booking:my_bookings")

    grooming_forms = {
        form.booking_item_id: form
        for form in GroomingServiceForm.objects.filter(booking_item__booking=booking)
    }

    pet_items = []
    grooming_summaries = []

    for item in booking.items.all():
        additionals = []
        for additional in item.additionals.all():
            additionals.append({
                "name": additional.additional_name if additional.additional_name else (additional.additional.name if additional.additional else "-"),
                "harga": additional.harga,
            })

        grooming_form = grooming_forms.get(item.id)

        pet_items.append({
            "pet_name": item.pet.name,
            "pet_type": item.pet.jenis,
            "package_name": item.package_name if item.package_name else (item.package.name if item.package else "-"),
            "package_price": item.harga_paket,
            "durasi_paket": item.durasi_paket,
            "additionals": additionals,
            "subtotal": item.subtotal,
        })

        if grooming_form:
            grooming_summaries.append(
                {
                    "pet_name": item.pet.name,
                    "kondisi_bulu": grooming_form.kondisi_bulu,
                    "kondisi_kulit": grooming_form.kondisi_kulit,
                    "kondisi_telinga": grooming_form.kondisi_telinga,
                    "kondisi_kuku": grooming_form.kondisi_kuku,
                    "perilaku_hewan": grooming_form.perilaku_hewan,
                    "catatan_tambahan": grooming_form.catatan_tambahan,
                    "foto_bukti_url": grooming_form.foto_bukti_layanan.url if grooming_form.foto_bukti_layanan else None,
                }
            )

    grooming_notes = "belum tersedia" if not grooming_summaries else None

    context = {
        "booking": booking,
        "customer_name": booking.customer.full_name,
        "booking_date": booking.tanggal,
        "booking_time": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
        "service_type": booking.get_service_type_display(),
        "groomer_name": booking.groomer.user.full_name,
        "total_durasi": booking.total_durasi,
        "total_harga": booking.total_harga,
        "status": booking.get_status_display(),
        "payment_status": booking.get_payment_status_display(),
        "pet_items": pet_items,
        "grooming_summaries": grooming_summaries,
        "grooming_notes": grooming_notes,
    }

    return render(request, "booking/history_detail.html", context)

@login_required
def staff_booking_history_all(request):
    if not request.user.is_authenticated or request.user.role != User.Role.STAFF:
        return HttpResponseForbidden("403 Forbidden: hanya staff operasional yang dapat mengakses halaman ini.")

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    page = _to_int(request.GET.get('page'), 1)
    per_page = 10

    bookings = (
        Booking.objects.select_related("customer", "groomer", "groomer__user")
        .prefetch_related("items__pet", "items__package")
        .filter(status__in=[Booking.Status.CANCELLED, Booking.Status.SERVICE_COMPLETED])
        .order_by("-tanggal", "-waktu_mulai")
    )

    if search_query:
        bookings = bookings.filter(
            models.Q(customer__full_name__icontains=search_query) |
            models.Q(items__pet__name__icontains=search_query)
        ).distinct()

    if status_filter == 'paid':
        bookings = bookings.filter(payment_status=Booking.PaymentStatus.PAID, status=Booking.Status.SERVICE_COMPLETED)
    elif status_filter == 'cancelled':
        bookings = bookings.filter(status=Booking.Status.CANCELLED)

    total_count = bookings.count()
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page
    bookings = bookings[offset:offset + per_page]

    booking_list = []
    for booking in bookings:
        pet_names = [item.pet.name for item in booking.items.all()]
        booking_list.append({
            'id': booking.id,
            'tanggal': booking.tanggal,
            'waktu_mulai': booking.waktu_mulai.strftime('%H:%M'),
            'waktu_selesai': booking.waktu_selesai.strftime('%H:%M'),
            'customer_name': booking.customer.full_name,
            'pet_names': pet_names,
            'groomer_name': booking.groomer.user.full_name,
            'service_type': booking.get_service_type_display(),
            'status': booking.status,
            'status_label': booking.get_status_display(),
            'payment_status': booking.payment_status,
            'payment_status_label': booking.get_payment_status_display(),
        })

    context = {
        'bookings': booking_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'page': page,
        'total_pages': total_pages,
        'total_count': total_count,
        'prev_page': page - 1,
        'next_page': page + 1,
    }

    return render(request, "booking/staff_history_all.html", context)


@login_required
def staff_booking_history_detail(request, booking_id):
    if not request.user.is_authenticated or request.user.role != User.Role.STAFF:
        return HttpResponseForbidden("403 Forbidden: hanya staff operasional yang dapat mengakses halaman ini.")

    from groomer_jobs.models import GroomingServiceForm

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user")
        .prefetch_related(
            "items__pet",
            "items__package",
            "items__additionals__additional",
        ),
        id=booking_id,
    )

    grooming_forms = {
        form.booking_item_id: form
        for form in GroomingServiceForm.objects.filter(booking_item__booking=booking)
    }

    pet_items = []
    grooming_notes_parts = []

    for item in booking.items.all():
        additionals = []
        for additional in item.additionals.all():
            additionals.append({
                "name": additional.additional_name if additional.additional_name else (additional.additional.name if additional.additional else "-"),
                "harga": additional.harga,
            })

        grooming_form = grooming_forms.get(item.id)

        pet_items.append({
            "pet_name": item.pet.name,
            "pet_type": item.pet.jenis,
            "package_name": item.package_name if item.package_name else (item.package.name if item.package else "-"),
            "package_price": item.harga_paket,
            "durasi_paket": item.durasi_paket,
            "additionals": additionals,
            "subtotal": item.subtotal,
        })

        if grooming_form:
            note_lines = [
                f"{item.pet.name}",
                f"Kondisi bulu: {grooming_form.kondisi_bulu}",
                f"Kondisi kulit: {grooming_form.kondisi_kulit}",
                f"Kondisi telinga: {grooming_form.kondisi_telinga}",
                f"Kondisi kuku: {grooming_form.kondisi_kuku}",
                f"Perilaku hewan: {grooming_form.perilaku_hewan}",
            ]

            if grooming_form.catatan_tambahan:
                note_lines.append(f"Catatan tambahan: {grooming_form.catatan_tambahan}")

            if grooming_form.foto_bukti_layanan:
                note_lines.append(f"Foto bukti layanan: {grooming_form.foto_bukti_layanan.url}")

            grooming_notes_parts.append("\n".join(note_lines))

    grooming_notes = "\n\n".join(grooming_notes_parts) if grooming_notes_parts else "belum tersedia"

    context = {
        "booking": booking,
        "customer_name": booking.customer.full_name,
        "customer_phone": booking.customer.phone_number,
        "booking_date": booking.tanggal,
        "booking_time": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
        "service_type": booking.get_service_type_display(),
        "groomer_name": booking.groomer.user.full_name,
        "address": booking.alamat,
        "total_durasi": booking.total_durasi,
        "total_harga": booking.total_harga,
        "status": booking.status,
        "status_label": booking.get_status_display(),
        "payment_status": booking.payment_status,
        "payment_status_label": booking.get_payment_status_display(),
        "catatan": booking.catatan,
        "pet_items": pet_items,
        "grooming_notes": grooming_notes,
    }

    return render(request, "booking/staff_booking_history_detail.html", context)


@login_required
@require_GET
def api_pet_options(request):
    if not _is_customer(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    pet_id = _to_int(request.GET.get("pet_id"))
    if pet_id <= 0:
        return JsonResponse({"error": "pet_id wajib diisi."}, status=400)

    pet = Pet.objects.filter(owner=request.user, id=pet_id).first()
    if not pet:
        return JsonResponse({"error": "Pet tidak ditemukan."}, status=404)

    animal_type = get_pet_animal_type(pet)
    grooming_packages = (
        Package.objects.prefetch_related("prices")
        .filter(is_deleted=False, animal_type=animal_type, package_type=Package.PackageType.GROOMING)
        .order_by("name")
    )
    additional_services = (
        Package.objects.prefetch_related("prices")
        .filter(is_deleted=False, animal_type=animal_type, package_type=Package.PackageType.ADDITIONAL)
        .order_by("name")
    )

    return JsonResponse(
        {
            "pet": {
                "id": pet.id,
                "name": pet.name,
                "animal_type": animal_type,
            },
            "packages": [
                {
                    "id": pkg.id,
                    "name": pkg.name,
                    "duration": int(pkg.duration_min),
                    "price": int(get_package_price_for_pet(pkg, pet)),
                    "label": f"{pkg.name} - {int(pkg.duration_min)} menit - Rp {int(get_package_price_for_pet(pkg, pet)):,}".replace(",", "."),
                }
                for pkg in grooming_packages
            ],
            "additionals": [
                {
                    "id": add.id,
                    "name": add.name,
                    "duration": int(add.duration_min),
                    "price": int(get_package_price_for_pet(add, pet)),
                    "label": f"{add.name} (+{int(add.duration_min)} menit) - Rp {int(get_package_price_for_pet(add, pet)):,}".replace(",", "."),
                }
                for add in additional_services
            ],
        }
    )


@login_required
@require_GET
def api_groomers(request):
    if not _is_customer(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    service_type = request.GET.get("service_type", "").strip()
    if service_type not in [Booking.ServiceType.CLINIC, Booking.ServiceType.HOME]:
        return JsonResponse({"error": "service_type tidak valid."}, status=400)

    groomers = (
        Groomer.objects.select_related("user")
        .filter(service_type=service_type, user__is_active=True)
        .order_by("user__full_name")
    )

    return JsonResponse(
        {
            "groomers": [
                {
                    "id": groomer.id,
                    "name": groomer.user.full_name,
                    "phone": groomer.user.phone_number,
                    "service_type": groomer.service_type,
                }
                for groomer in groomers
            ]
        }
    )


@login_required
@require_GET
def api_slots(request):
    if not _is_customer(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    groomer_id = _to_int(request.GET.get("groomer_id"))
    date_raw = request.GET.get("date", "").strip()
    duration = _to_int(request.GET.get("duration"))
    service_type = request.GET.get("service_type", "").strip()

    if groomer_id <= 0:
        return JsonResponse({"error": "groomer_id wajib diisi."}, status=400)
    if not date_raw:
        return JsonResponse({"error": "date wajib diisi."}, status=400)
    if duration <= 0:
        return JsonResponse({"error": "duration wajib > 0."}, status=400)
    if service_type not in [Booking.ServiceType.CLINIC, Booking.ServiceType.HOME]:
        return JsonResponse({"error": "service_type tidak valid."}, status=400)

    try:
        date_obj = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Format date tidak valid."}, status=400)

    today = timezone.localdate()
    if date_obj < today or date_obj > today + timedelta(days=MAX_BOOKING_DAYS):
        return JsonResponse({"error": "Tanggal di luar range booking."}, status=400)

    if not is_working_day(date_obj):
        return JsonResponse(
            {
                "slots": [],
                "message": "Hari Senin libur. Silakan pilih tanggal lain.",
            }
        )

    groomer = (
        Groomer.objects.select_related("user")
        .filter(id=groomer_id, service_type=service_type, user__is_active=True)
        .first()
    )
    if not groomer:
        return JsonResponse({"error": "Groomer tidak tersedia."}, status=404)

    slots = get_available_slots(groomer.id, date_obj, duration, service_type)
    return JsonResponse(
        {
            "slots": slots,
            "message": None
            if slots
            else "Tidak ada slot tersedia untuk groomer ini pada tanggal tersebut, silakan pilih tanggal atau groomer lain.",
        }
    )

@login_required
@require_http_methods(["PUT"])
def api_update_payment_status(request, booking_id):
    if not _is_staff_operational(request.user):
        return JsonResponse(
            {"message": "403 Forbidden: hanya staff operasional yang dapat mengubah status pembayaran."},
            status=403,
        )

    booking = get_object_or_404(
        Booking.objects.select_related("customer", "groomer", "groomer__user"),
        id=booking_id,
    )

    if booking.payment_status == Booking.PaymentStatus.PAID:
        return JsonResponse(
            {
                "message": "Status pembayaran booking sudah paid.",
                "booking_id": booking.id,
                "payment_status": booking.payment_status,
                "payment_status_label": booking.get_payment_status_display(),
            },
            status=400,
        )

    booking.payment_status = Booking.PaymentStatus.PAID
    booking.save(update_fields=["payment_status", "updated_at"])

    return JsonResponse(
        {
            "message": "Status pembayaran berhasil diperbarui.",
            "booking_id": booking.id,
            "booking_code": booking.booking_code,
            "payment_status": booking.payment_status,
            "payment_status_label": booking.get_payment_status_display(),
            "updated_at": booking.updated_at.isoformat(),
        },
        status=200,
    )