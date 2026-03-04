from django.shortcuts import render, redirect, get_object_or_404
from .decorators import staff_required
from .models import Package, PackagePrice
from django.contrib import messages
from django.db import transaction 
from django.http import HttpResponseBadRequest
from .forms import PackageForm

# Ketentuan edit paket
def _has_scheduled_booking(package: Package) -> bool:
    # return package.bookings.filter(status="scheduled").exists()
    return False

# Create your views here.
@staff_required
def package_list(request):
    # if request.method == "POST":
    #     return package_store(request)
    
    # Prefetch prices biar gak N+1
    packages = (
        Package.objects
        .filter(is_deleted=False)
        .prefetch_related("prices")
        .order_by("animal_type", "name")
    )

    cat_packages = [p for p in packages if p.animal_type == "cat"]
    dog_packages = [p for p in packages if p.animal_type == "dog"]

    return render(request, "packages/package_list.html", {
        "cat_packages": cat_packages,
        "dog_packages": dog_packages,
    })
  
@staff_required
def package_create(request):
    form = PackageForm()
    return render(request, "packages/package_form.html", {"form": form, "mode": "create"})

@staff_required
def package_store(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Bad Request")

    form = PackageForm(request.POST)
    if not form.is_valid():
        return render(request, "packages/package_form.html", {"form": form, "mode": "create"}, status=400)

    data = form.cleaned_data

    with transaction.atomic():
        pkg = Package.objects.create(
            name=data["name"],
            animal_type=data["animal_type"],
            description=data["description"],
            duration_min=int(data["duration_min"]),
            is_deleted=False,
        )

        if data["animal_type"] == "cat":
            PackagePrice.objects.create(
                package=pkg,
                size=None,
                price=int(data["price_cat"]),
            )
        else:
            PackagePrice.objects.bulk_create([
                PackagePrice(package=pkg, size="S", price=int(data["price_s"])),
                PackagePrice(package=pkg, size="M", price=int(data["price_m"])),
                PackagePrice(package=pkg, size="L", price=int(data["price_l"])),
                PackagePrice(package=pkg, size="XL", price=int(data["price_xl"])),
            ])

    messages.success(request, "Paket berhasil ditambahkan")
    return redirect("package_list")


@staff_required
def package_edit(request, package_id: int):
    pkg = get_object_or_404(Package.objects.prefetch_related("prices"), id=package_id, is_deleted=False)

    initial = {
        "name": pkg.name,
        "animal_type": pkg.animal_type,
        "description": pkg.description,
        "duration_min": str(pkg.duration_min),
        "price_cat": pkg.cat_price if pkg.animal_type == "cat" else None,
        "price_s": pkg.price_s if pkg.animal_type == "dog" else None,
        "price_m": pkg.price_m if pkg.animal_type == "dog" else None,
        "price_l": pkg.price_l if pkg.animal_type == "dog" else None,
        "price_xl": pkg.price_xl if pkg.animal_type == "dog" else None,
    }

    form = PackageForm(initial=initial, locked_animal_type=pkg.animal_type)

    return render(request, "packages/package_form.html", {
        "form": form,
        "mode": "edit",
        "pkg": pkg,
    })

@staff_required
def package_update(request, package_id: int):
    if request.method != "POST":
        return HttpResponseBadRequest("Bad Request")

    pkg = get_object_or_404(Package.objects.prefetch_related("prices"), id=package_id, is_deleted=False)

    if _has_scheduled_booking(pkg):
        # 409 Conflict
        return render(request, "packages/package_form.html", {
            "form": PackageForm(initial={}, locked_animal_type=pkg.animal_type),
            "mode": "edit",
            "pkg": pkg,
            "conflict": True,
        }, status=409)

    form = PackageForm(request.POST, locked_animal_type=pkg.animal_type)
    if not form.is_valid():
        return render(request, "packages/package_form.html", {
            "form": form,
            "mode": "edit",
            "pkg": pkg,
        }, status=400)

    data = form.cleaned_data

    with transaction.atomic():
        # update table packages
        pkg.name = data["name"]
        pkg.description = data["description"]
        pkg.duration_min = int(data["duration_min"])
        # animal_type tidak diubah
        pkg.save()

        # update prices
        if pkg.animal_type == "cat":
            # upsert cat price (size NULL)
            PackagePrice.objects.update_or_create(
                package=pkg,
                size=None,
                defaults={"price": int(data["price_cat"])},
            )
            # safety: kalau sebelumnya ada dog prices (harusnya nggak), hapus
            PackagePrice.objects.filter(package=pkg).exclude(size__isnull=True).delete()

        else:  
            # dog
            # safety: hapus cat price kalau ada
            PackagePrice.objects.filter(package=pkg, size__isnull=True).delete()

            for size_key, field in [("S", "price_s"), ("M", "price_m"), ("L", "price_l"), ("XL", "price_xl")]:
                PackagePrice.objects.update_or_create(
                    package=pkg,
                    size=size_key,
                    defaults={"price": int(data[field])},
                )

    messages.success(request, "Paket berhasil diperbarui")
    return redirect("package_list")


@staff_required
def package_delete(request, package_id: int):
    if request.method != "POST":
        return HttpResponseBadRequest("Bad Request")

    pkg = get_object_or_404(Package, id=package_id, is_deleted=False)

    if _has_scheduled_booking(pkg):
        messages.error(request, "Paket tidak bisa dihapus karena masih ada booking yang terjadwal.")
        return redirect("package_list")

    pkg.soft_delete()
    messages.success(request, f'Paket "{pkg.name}" berhasil dihapus.')
    return redirect("package_list")


def package_catalog(request):
    """Customer: lihat katalog paket grooming (read-only, hanya paket aktif)."""
    if not request.user.is_authenticated:
        return redirect("login")

    packages = (
        Package.objects
        .filter(is_deleted=False)
        .prefetch_related("prices")
        .order_by("animal_type", "name")
    )

    cat_packages = [p for p in packages if p.animal_type == "cat"]
    dog_packages = [p for p in packages if p.animal_type == "dog"]

    return render(request, "packages/catalog.html", {
        "cat_packages": cat_packages,
        "dog_packages": dog_packages,
    })
