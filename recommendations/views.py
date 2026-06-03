from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from packages.models import Package
from pet.models import Pet
from booking.models import Booking, BookingItem
from django.db import models

ACTIVE_BOOKING_STATUSES = [
    Booking.Status.SCHEDULED,
    Booking.Status.SERVICE_STARTED,
]

def _get_blocked_pet_ids(user):
    return set(
        BookingItem.objects.filter(
            booking__customer=user,
        )
        .filter(
            models.Q(booking__status__in=ACTIVE_BOOKING_STATUSES)
            | models.Q(
                booking__status=Booking.Status.SERVICE_COMPLETED,
                booking__payment_status=Booking.PaymentStatus.UNPAID,
            )
        )
        .values_list("pet_id", flat=True)
        .distinct()
    )

from .forms import (
    ADDITIONAL_CONDITION_CHOICES,
    FUR_CONDITION_CHOICES,
    SKIN_CONDITION_CHOICES,
)
from .utils import get_recommended_packages


CONDITION_LABELS = {
    "thick_long_fur": "Bulu tebal/panjang",
    "dull_shedding_fur": "Bulu rontok/kusam",
    "matted_fur": "Bulu kusut/gimbal",
    "fleas": "Berkutu",
    "fungus_irritation": "Berjamur/iritasi",
    "long_nails": "Kuku panjang",
    "dirty_ears": "Telinga kotor",
    "styling": "Ingin styling/potong model",
}


def _get_pet_animal_type(pet):
    jenis = (pet.jenis or "").strip().lower()

    if jenis == "dog":
        return "dog"

    if jenis == "cat":
        return "cat"

    return jenis


def _get_pet_size_label(pet):
    if _get_pet_animal_type(pet) != "dog":
        return ""

    weight = pet.berat or 0

    if 2 <= weight <= 10:
        return "S"
    if 11 <= weight <= 25:
        return "M"
    if 26 <= weight <= 45:
        return "L"

    return "XL"


def _get_conditions_from_post(request, pet_id):
    fur_conditions = request.POST.getlist(f"fur_conditions_{pet_id}")
    skin_conditions = request.POST.getlist(f"skin_conditions_{pet_id}")
    additional_conditions = request.POST.getlist(f"additional_conditions_{pet_id}")

    return fur_conditions + skin_conditions + additional_conditions


def _build_condition_label_list(conditions):
    return [
        CONDITION_LABELS.get(condition, condition)
        for condition in conditions
    ]


def _get_session_items(request):
    recommendation_input = request.session.get("recommendation_input") or {}
    return recommendation_input.get("items", [])


def _build_form_context(request, errors=None):
    errors = errors or {}

    pets = Pet.objects.filter(owner=request.user).order_by("name")
    session_items = _get_session_items(request)
    blocked_pet_ids = _get_blocked_pet_ids(request.user)

    selected_pet_ids = [
        int(item["pet_id"])
        for item in session_items
        if item.get("pet_id")
    ]

    conditions_by_pet = {
        int(item["pet_id"]): item.get("conditions", [])
        for item in session_items
        if item.get("pet_id")
    }

    pet_form_items = []
    for pet in pets:
        pet_form_items.append({
            "pet": pet,
            "conditions": conditions_by_pet.get(pet.id, []),
            "is_selected": pet.id in selected_pet_ids,
            "error": errors.get(f"conditions_{pet.id}"),
        })

    return {
        "pets": pets,
        "pet_form_items": pet_form_items,
        "selected_pet_ids": selected_pet_ids,
        "blocked_pet_ids": blocked_pet_ids,
        "fur_condition_choices": FUR_CONDITION_CHOICES,
        "skin_condition_choices": SKIN_CONDITION_CHOICES,
        "additional_condition_choices": ADDITIONAL_CONDITION_CHOICES,
        "errors": errors,
    }


@login_required(login_url="login")
def recommendation_start(request):
    if request.user.role != "customer":
        return HttpResponseForbidden("403 Forbidden")

    request.session.pop("recommendation_input", None)
    return redirect("recommendations:recommendation_form")


@login_required(login_url="login")
def recommendation_form(request):
    if request.user.role != "customer":
        return HttpResponseForbidden("403 Forbidden")

    if request.method == "GET":
        return render(
            request,
            "recommendations/recommendation_form.html",
            _build_form_context(request),
        )

    selected_pet_ids = [
        int(pet_id)
        for pet_id in request.POST.getlist("selected_pet_ids")
        if str(pet_id).isdigit()
    ]

    errors = {}

    if not selected_pet_ids:
        errors["selected_pet_ids"] = "Pilih minimal satu hewan"

    pets = list(
        Pet.objects.filter(
            owner=request.user,
            id__in=selected_pet_ids,
        ).order_by("name")
    )

    if selected_pet_ids and len(pets) != len(set(selected_pet_ids)):
        errors["selected_pet_ids"] = "Hewan yang dipilih tidak valid"

    recommendation_items = []

    for pet in pets:
        conditions = _get_conditions_from_post(request, pet.id)

        if not conditions:
            errors[f"conditions_{pet.id}"] = f"Pilih minimal satu kondisi untuk {pet.name}"
            continue

        recommendation_items.append(
            {
                "pet_id": pet.id,
                "animal_type": _get_pet_animal_type(pet),
                "conditions": conditions,
            }
        )

    if errors:
        request.session["recommendation_input"] = {
            "items": [
                {
                    "pet_id": pet_id,
                    "animal_type": _get_pet_animal_type(
                        Pet.objects.filter(owner=request.user, id=pet_id).first()
                    ) if Pet.objects.filter(owner=request.user, id=pet_id).exists() else "",
                    "conditions": _get_conditions_from_post(request, pet_id),
                }
                for pet_id in selected_pet_ids
            ]
        }

        return render(
            request,
            "recommendations/recommendation_form.html",
            _build_form_context(request, errors=errors),
            status=400,
        )

    request.session["recommendation_input"] = {
        "items": recommendation_items
    }

    return redirect("recommendations:recommendation_result")


@login_required(login_url="login")
def recommendation_result(request):
    if request.user.role != "customer":
        return HttpResponseForbidden("403 Forbidden")

    session_items = _get_session_items(request)

    if not session_items:
        return HttpResponseForbidden("403 Forbidden")

    pet_ids = [
        item.get("pet_id")
        for item in session_items
        if item.get("pet_id")
    ]

    pets_by_id = {
        pet.id: pet
        for pet in Pet.objects.filter(owner=request.user, id__in=pet_ids)
    }
    
    blocked_pet_ids = _get_blocked_pet_ids(request.user)

    recommendation_results = []
    has_additional_recommendation = False

    for item in session_items:
        pet_id = item.get("pet_id")
        pet = pets_by_id.get(pet_id)

        if not pet:
            continue

        animal_type = item.get("animal_type") or _get_pet_animal_type(pet)
        selected_conditions = item.get("conditions", [])

        if not animal_type or not selected_conditions:
            continue

        recommended_packages = get_recommended_packages(
            animal_type=animal_type,
            selected_conditions=selected_conditions,
        )

        grooming_packages = [
            package for package in recommended_packages
            if package.package_type == Package.PackageType.GROOMING
        ]

        additional_packages = [
            package for package in recommended_packages
            if package.package_type == Package.PackageType.ADDITIONAL
        ]

        if additional_packages:
            has_additional_recommendation = True

        recommendation_results.append(
            {
                "pet": pet,
                "animal_type": animal_type,
                "pet_size": _get_pet_size_label(pet),
                "is_blocked": pet.id in blocked_pet_ids,
                "selected_conditions": selected_conditions,
                "selected_condition_labels": _build_condition_label_list(selected_conditions),
                "recommended_packages": recommended_packages,
                "grooming_packages": grooming_packages,
                "additional_packages": additional_packages,
            }
        )

    if not recommendation_results:
        return HttpResponseForbidden("403 Forbidden")

    is_multiple_pets = len(recommendation_results) > 1
    
    has_bookable_pet = any(
        not result["is_blocked"]
        for result in recommendation_results
    )

    return render(
        request,
        "recommendations/recommendation_result.html",
        {
            "recommendation_results": recommendation_results,
            "is_multiple_pets": is_multiple_pets,
            "has_bookable_pet": has_bookable_pet,
            "has_additional_recommendation": has_additional_recommendation,
            "errors": {},
        },
    )


@login_required(login_url="login")
@require_POST
def recommendation_book(request):
    if request.user.role != "customer":
        return HttpResponseForbidden("403 Forbidden")

    session_items = _get_session_items(request)

    if not session_items:
        return HttpResponseForbidden("403 Forbidden")

    pet_ids_from_session = {
        int(item["pet_id"])
        for item in session_items
        if item.get("pet_id")
    }

    prefill_items = []
    errors = {}

    blocked_pet_ids = _get_blocked_pet_ids(request.user)
    bookable_pet_ids = pet_ids_from_session - blocked_pet_ids

    if not bookable_pet_ids:
        errors["booking"] = (
            "Semua hewan yang dipilih sedang memiliki booking aktif atau booking selesai yang belum dibayar. "
            "Selesaikan atau bayar booking aktif terlebih dahulu sebelum membuat booking baru."
        )
        return _render_result_with_errors(request, errors)

    if len(pet_ids_from_session) == 1:
        pet_id = next(iter(pet_ids_from_session))

        if pet_id in blocked_pet_ids:
            errors["booking"] = (
                "Hewan ini sedang memiliki booking aktif atau booking selesai yang belum dibayar, "
                "sehingga belum dapat dibuatkan booking baru."
            )
            return _render_result_with_errors(request, errors)

        package_id = request.POST.get("package_id")

        if not package_id:
            errors["booking"] = "Pilih paket grooming terlebih dahulu."
        else:
            prefill_items.append(
                {
                    "pet_id": pet_id,
                    "package_id": int(package_id),
                    "additional_ids": [],
                }
            )

    else:
        for pet_id in bookable_pet_ids:
            package_id = request.POST.get(f"package_id_{pet_id}")

            if not package_id:
                errors["booking"] = "Pilih satu paket grooming untuk setiap hewan yang dapat dibooking."
                continue

            prefill_items.append(
                {
                    "pet_id": pet_id,
                    "package_id": int(package_id),
                    "additional_ids": [],
                }
            )

    if errors:
        return _render_result_with_errors(request, errors)

    pet_ids = [item["pet_id"] for item in prefill_items]
    package_ids = [item["package_id"] for item in prefill_items]

    pets = {
        pet.id: pet
        for pet in Pet.objects.filter(owner=request.user, id__in=pet_ids)
    }

    packages = {
        package.id: package
        for package in Package.objects.filter(
            id__in=package_ids,
            is_deleted=False,
            package_type=Package.PackageType.GROOMING,
        )
    }

    for item in prefill_items:
        pet = pets.get(item["pet_id"])
        package = packages.get(item["package_id"])

        if not pet or not package:
            errors["booking"] = "Paket atau hewan yang dipilih tidak valid."
            break

        if package.animal_type != _get_pet_animal_type(pet):
            errors["booking"] = "Paket tidak sesuai dengan jenis hewan."
            break

    if errors:
        return _render_result_with_errors(request, errors)

    request.session["booking_prefill_from_recommendations"] = {
        "items": prefill_items
    }
    request.session.modified = True

    return redirect("booking:create")


def _render_result_with_errors(request, errors):
    session_items = _get_session_items(request)

    if not session_items:
        return HttpResponseForbidden("403 Forbidden")

    pet_ids = [
        item.get("pet_id")
        for item in session_items
        if item.get("pet_id")
    ]

    pets_by_id = {
        pet.id: pet
        for pet in Pet.objects.filter(owner=request.user, id__in=pet_ids)
    }
    
    blocked_pet_ids = _get_blocked_pet_ids(request.user)

    recommendation_results = []
    has_additional_recommendation = False

    for item in session_items:
        pet = pets_by_id.get(item.get("pet_id"))

        if not pet:
            continue

        animal_type = item.get("animal_type") or _get_pet_animal_type(pet)
        selected_conditions = item.get("conditions", [])

        recommended_packages = get_recommended_packages(
            animal_type=animal_type,
            selected_conditions=selected_conditions,
        )

        grooming_packages = [
            package for package in recommended_packages
            if package.package_type == Package.PackageType.GROOMING
        ]

        additional_packages = [
            package for package in recommended_packages
            if package.package_type == Package.PackageType.ADDITIONAL
        ]

        if additional_packages:
            has_additional_recommendation = True

        recommendation_results.append(
            {
                "pet": pet,
                "animal_type": animal_type,
                "pet_size": _get_pet_size_label(pet),
                "is_blocked": pet.id in blocked_pet_ids,
                "selected_conditions": selected_conditions,
                "selected_condition_labels": _build_condition_label_list(selected_conditions),
                "recommended_packages": recommended_packages,
                "grooming_packages": grooming_packages,
                "additional_packages": additional_packages,
            }
        )

    has_bookable_pet = any(
        not result["is_blocked"]
        for result in recommendation_results
    )

    return render(
        request,
        "recommendations/recommendation_result.html",
        {
            "recommendation_results": recommendation_results,
            "is_multiple_pets": len(recommendation_results) > 1,
            "has_bookable_pet": has_bookable_pet,
            "has_additional_recommendation": has_additional_recommendation,
            "errors": errors,
        },
        status=400,
    )