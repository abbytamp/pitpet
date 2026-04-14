
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction
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
    get_available_slots,
    get_package_price_for_pet,
    get_pet_animal_type,
    is_slot_available,
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

    # Ambil semua groomer aktif untuk tipe layanan
    groomers = Groomer.objects.select_related('user').filter(service_type=service_type, is_deleted=False)

    # Tentukan slot waktu per 30 menit (mengikuti aturan booking)
    from booking.utils import WORK_START, WORK_END, SLOT_MINUTES
    slot_times = []
    current = datetime.combine(tanggal, WORK_START)
    end = datetime.combine(tanggal, WORK_END)
    while current < end:
        slot_times.append(current.strftime('%H:%M'))
        current += timedelta(minutes=SLOT_MINUTES)

    # Ambil semua booking pada tanggal & tipe layanan
    bookings = (Booking.objects.filter(
        tanggal=tanggal,
        service_type=service_type,
        groomer__in=groomers
    ).select_related('customer', 'groomer', 'groomer__user')
    .prefetch_related('items__pet', 'items__package')
    )

    # --- Untuk tampilan list: satu kotak per booking, slot kosong tetap muncul ---
    from collections import defaultdict
    groomer_schedules = {}
    for groomer in groomers:
        # Ambil semua booking untuk groomer ini, urutkan mulai
        groomer_bookings = [b for b in bookings if b.groomer_id == groomer.id]
        groomer_bookings.sort(key=lambda b: b.waktu_mulai)
        schedule = []
        slot_idx = 0
        while slot_idx < len(slot_times):
            slot_time = slot_times[slot_idx]
            # Cek apakah ada booking yang mulai di slot ini
            found = False
            for booking in groomer_bookings:
                start = booking.waktu_mulai.strftime('%H:%M')
                end = booking.waktu_selesai.strftime('%H:%M')
                if slot_time == start:
                    # Hitung durasi dalam slot
                    start_idx = slot_idx
                    try:
                        end_idx = slot_times.index(end)
                    except ValueError:
                        end_idx = len(slot_times)
                    duration = end_idx - start_idx
                    # Ambil info booking
                    if booking.items.exists():
                        first_item = booking.items.first()
                        pet_name = first_item.pet.name
                        package_name = first_item.package.name
                    else:
                        pet_name = "-"
                        package_name = "-"
                    schedule.append({
                        'type': 'booking',
                        'start': start,
                        'end': end,
                        'customer': booking.customer,
                        'package_name': package_name,
                        'status_display': booking.get_status_display(),
                        'payment_status_display': booking.get_payment_status_display(),
                        'booking_id': booking.id,
                    })
                    slot_idx += duration
                    found = True
                    break
            if not found:
                # Slot kosong
                schedule.append({
                    'type': 'available',
                    'start': slot_time,
                })
                slot_idx += 1
        groomer_schedules[groomer.id] = schedule

    context = {
        'groomers': groomers,
        'groomer_schedules': groomer_schedules,
        'service_type': service_type,
        'tanggal': tanggal.strftime('%Y-%m-%d'),
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
                "name": additional.additional.name,
                "duration": additional.durasi,
            })
            total_pet_duration += additional.durasi

        pet_items.append({
            "pet_name": item.pet.name,
            "pet_type": item.pet.jenis,
            "pet_size": _get_pet_size_label(item.pet),
            "package_name": item.package.name if item.package else "-",
            "package_duration": item.durasi_paket,
            "additionals": additionals,
            "total_pet_duration": total_pet_duration,
        })

    context = {
        "booking": booking,
        "owner_name": booking.customer.full_name,
        "owner_phone": booking.customer.phone_number,
        "service_type_label": booking.get_service_type_display(),
        "groomer_name": booking.groomer.user.full_name,
        "address": booking.alamat,
        "status": booking.status,
        "status_label": booking.get_status_display(),
        "payment_status": booking.payment_status,
        "payment_status_label": booking.get_payment_status_display(),
        "time_range": f"{booking.waktu_mulai.strftime('%H:%M')} - {booking.waktu_selesai.strftime('%H:%M')}",
        "total_duration": booking.total_durasi,
        "pet_items": pet_items,
        "can_cancel": booking.status == Booking.Status.SCHEDULED,
        "can_mark_paid": (
            booking.payment_status == Booking.PaymentStatus.UNPAID
            and booking.status == Booking.Status.SERVICE_COMPLETED
        ),
    }

    return render(request, "booking/staff_booking_detail.html", context)


def _iter_booking_slots(booking, slot_minutes=30):
    """
    Menghasilkan semua slot waktu yang dipakai booking:
    contoh 08:00-09:30 -> 08:00, 08:30, 09:00
    """
    current = datetime.combine(booking.tanggal, booking.waktu_mulai)
    end = datetime.combine(booking.tanggal, booking.waktu_selesai)
    step = timedelta(minutes=slot_minutes)

    slots = []
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += step
    return slots

# Calculate size label (nanti ganti dengan defined method di model pet)
def _get_pet_size_label(pet):
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


def _is_customer(user) -> bool:
    return user.is_authenticated and user.role == User.Role.CUSTOMER


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@login_required
def booking_create(request):
    if not _is_customer(request.user):
        return redirect("login")

    pets = Pet.objects.filter(owner=request.user).order_by("name")

    context = {
        "pets": pets,
        "clinic_address": CLINIC_ADDRESS,
        "transport_fees": TRANSPORT_FEES,
        "min_date": timezone.localdate().isoformat(),
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
        if not is_slot_available(groomer.id, tanggal, total_durasi, service_type, waktu_mulai):
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
            waktu_selesai=calculate_end_time(waktu_mulai, total_durasi),
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
def my_bookings(request):
    if not _is_customer(request.user):
        return redirect("login")

    bookings = (
        Booking.objects.select_related("groomer", "groomer__user")
        .prefetch_related("items__pet")
        .filter(customer=request.user)
        .order_by("-tanggal", "-waktu_mulai")
    )

    return render(request, "booking/my_bookings.html", {"bookings": bookings})


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
            "message": ""
            if slots
            else "Tidak ada slot tersedia untuk groomer ini pada tanggal tersebut, silakan pilih tanggal atau groomer lain.",
        }
    )
