from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Iterable

from django.db.models import QuerySet
from django.utils import timezone

from booking.models import Booking


WORK_START = time(8, 0)
WORK_END = time(17, 0)
OFF_DAY = 0  # Monday
SLOT_MINUTES = 30
HOME_BUFFER_MINUTES = 30
MAX_BOOKING_DAYS = 7
CLINIC_ADDRESS = "PitPet Clinic - Jl. PitPet No. 123, Jakarta"
TRANSPORT_FEES = [
    {"range": "0-10 km", "fee": 0},
    {"range": "11-20 km", "fee": 25000},
    {"range": "21-30 km", "fee": 35000},
    {"range": "31-40 km", "fee": 60000},
    {"range": "41-50 km", "fee": 80000},
]


@dataclass
class BookingWindow:
    start: datetime
    end: datetime


def get_pet_animal_type(pet) -> str:
    return "cat" if str(pet.jenis).lower() == "cat" else "dog"


def get_dog_size(weight: float) -> str:
    if 2 <= weight <= 10:
        return "S"
    if 11 <= weight <= 25:
        return "M"
    if 26 <= weight <= 45:
        return "L"
    return "XL"


def round_up_to_next_slot(dt: datetime) -> datetime:
    minute = dt.minute
    remainder = minute % SLOT_MINUTES
    if remainder == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt.replace(second=0, microsecond=0)

    add_minutes = SLOT_MINUTES - remainder
    rounded = dt + timedelta(minutes=add_minutes)
    return rounded.replace(second=0, microsecond=0)


def get_package_price_for_pet(package, pet) -> Decimal:
    animal_type = get_pet_animal_type(pet)
    if animal_type == "cat":
        return Decimal(package.cat_price or 0)

    size = get_dog_size(float(pet.berat))
    price = package.get_price_by_size(size)
    return Decimal(price or 0)


def _as_datetime(date_obj, time_obj) -> datetime:
    return datetime.combine(date_obj, time_obj)


def _with_buffer(start_dt: datetime, end_dt: datetime, service_type: str) -> BookingWindow:
    if service_type == Booking.ServiceType.HOME:
        gap = timedelta(minutes=HOME_BUFFER_MINUTES)
        return BookingWindow(start=start_dt - gap, end=end_dt + gap)
    return BookingWindow(start=start_dt, end=end_dt)


def _windows_overlap(a: BookingWindow, b: BookingWindow) -> bool:
    return a.start < b.end and a.end > b.start


def booking_to_window(booking: Booking) -> BookingWindow:
    start_dt = _as_datetime(booking.tanggal, booking.waktu_mulai)
    end_dt = _as_datetime(booking.tanggal, booking.waktu_selesai)
    return _with_buffer(start_dt, end_dt, booking.service_type)


def can_fit_in_working_hours(date_obj, start_time: time, duration_minutes: int, service_type: str) -> bool:
    start_dt = _as_datetime(date_obj, start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    visible_start = _as_datetime(date_obj, WORK_START)
    visible_end = _as_datetime(date_obj, WORK_END)
    if start_dt < visible_start or end_dt > visible_end:
        return False

    # For home service, keep the hidden travel buffer inside working hours too.
    buffered = _with_buffer(start_dt, end_dt, service_type)
    return buffered.start >= visible_start and buffered.end <= visible_end


def calculate_end_time(start_time: time, duration_minutes: int) -> time:
    end_dt = _as_datetime(timezone.localdate(), start_time) + timedelta(minutes=duration_minutes)
    return end_dt.time()


def _iter_candidate_starts(date_obj, duration_minutes: int, service_type: str) -> Iterable[datetime]:
    work_start_dt = _as_datetime(date_obj, WORK_START)
    work_end_dt = _as_datetime(date_obj, WORK_END)

    earliest_dt = work_start_dt
    today = timezone.localdate()
    if date_obj == today:
        min_dt = round_up_to_next_slot(timezone.localtime() + timedelta(hours=2))
        earliest_dt = max(work_start_dt, _as_datetime(date_obj, min_dt.time()))

    if earliest_dt >= work_end_dt:
        return []

    current = earliest_dt
    step = timedelta(minutes=SLOT_MINUTES)
    candidates = []
    while True:
        visible_end = current + timedelta(minutes=duration_minutes)
        if visible_end > work_end_dt:
            break

        if can_fit_in_working_hours(date_obj, current.time(), duration_minutes, service_type):
            candidates.append(current)

        current += step

    return candidates


def _active_booking_qs(groomer_id: int, date_obj) -> QuerySet[Booking]:
    return (
        Booking.objects.filter(groomer_id=groomer_id, tanggal=date_obj)
        .exclude(status=Booking.Status.CANCELLED)
        .only("id", "tanggal", "waktu_mulai", "waktu_selesai", "service_type", "status")
    )


def is_slot_available(groomer_id: int, date_obj, duration_minutes: int, service_type: str, start_time: time) -> bool:
    if date_obj.weekday() == OFF_DAY:
        return False

    if duration_minutes <= 0:
        return False

    if not can_fit_in_working_hours(date_obj, start_time, duration_minutes, service_type):
        return False

    requested_start = _as_datetime(date_obj, start_time)
    requested_end = requested_start + timedelta(minutes=duration_minutes)
    requested_window = _with_buffer(requested_start, requested_end, service_type)

    for booking in _active_booking_qs(groomer_id, date_obj):
        if _windows_overlap(requested_window, booking_to_window(booking)):
            return False

    return True


def get_available_slots(groomer_id: int, date_obj, duration_minutes: int, service_type: str) -> list[dict[str, str]]:
    if date_obj.weekday() == OFF_DAY:
        return []

    if duration_minutes <= 0:
        return []

    slots = []
    for start_dt in _iter_candidate_starts(date_obj, duration_minutes, service_type):
        start_time = start_dt.time()
        if not is_slot_available(groomer_id, date_obj, duration_minutes, service_type, start_time):
            continue

        end_time = (start_dt + timedelta(minutes=duration_minutes)).time()
        slots.append(
            {
                "start": start_time.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
                "label": f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
            }
        )

    return slots
