from packages.models import Package


LIGHT_CONDITIONS = {"long_nails", "dirty_ears"}
SKIN_CONDITIONS = {"fleas", "fungus_irritation"}

FALLBACK_RULES = {
    "cat": ["full package", "daily grooming"],
    "dog": ["full package", "dry grooming"],
}


def _package_text(package):
    return f"{package.name} {package.description}".lower()


def _is_dry_grooming(package):
    return "dry grooming" in _package_text(package)


def _is_daily_grooming(package):
    return "daily grooming" in _package_text(package)


def _is_full_package(package):
    return "full package" in _package_text(package)


def _add_package(package, recommended, recommended_ids):
    if package.id not in recommended_ids:
        recommended.append(package)
        recommended_ids.add(package.id)


def _selected_only_light_conditions(selected_conditions_set):
    """
    True jika customer hanya memilih: kuku panjang, telinga kotor, kuku panjang + telinga kotor
    """
    return bool(selected_conditions_set) and selected_conditions_set.issubset(LIGHT_CONDITIONS)


def _find_fallback_grooming_package(packages, animal_type, selected_conditions_set):
    fallback_keywords = FALLBACK_RULES.get(animal_type, [])

    grooming_packages = [
        package for package in packages
        if package.package_type == Package.PackageType.GROOMING
    ]

    for keyword in fallback_keywords:
        for package in grooming_packages:
            if keyword in _package_text(package):
                # Dry Grooming hanya boleh fallback kalau kondisi hanya kuku/telinga.
                if _is_dry_grooming(package) and not _selected_only_light_conditions(selected_conditions_set):
                    continue

                return package

    for package in grooming_packages:
        if _is_dry_grooming(package) and not _selected_only_light_conditions(selected_conditions_set):
            continue

        return package

    return None


def _get_effective_matched_tags(package_tags, selected_conditions_set):
    """
    Ambil tag yang cocok dengan kondisi customer.
    - Jika customer memilih kondisi lain selain kuku/telinga, tag kuku/telinga diabaikan agar paket seperti
      Dry Grooming tidak ikut muncul hanya karena ada nail trimming / ear cleaning.
    """
    matched_tags = package_tags.intersection(selected_conditions_set)

    if not matched_tags:
        return set()

    if not _selected_only_light_conditions(selected_conditions_set):
        matched_tags = matched_tags - LIGHT_CONDITIONS

    return matched_tags


def _has_exact_skin_match(package_tags, selected_conditions_set):
    """
    Jika kondisi berkutu + jamur, hanya paket yang punya kedua tag yang muncul.
    """
    selected_skin_conditions = selected_conditions_set.intersection(SKIN_CONDITIONS)
    package_skin_tags = package_tags.intersection(SKIN_CONDITIONS)

    if not selected_skin_conditions:
        return True

    if not package_skin_tags:
        return True

    # Jika user pilih kutu + jamur, paket skin harus punya dua-duanya.
    if selected_skin_conditions == SKIN_CONDITIONS:
        return SKIN_CONDITIONS.issubset(package_skin_tags)

    # Jika user hanya pilih salah satu skin condition, paket skin tidak boleh punya tag skin lain.
    return package_skin_tags == selected_skin_conditions


def _should_skip_grooming_when_skin_selected(package, matched_tags, selected_conditions_set):
    """
    Jika ada kondisi kulit, paket grooming umum yang hanya match kondisi non-skin tidak ikut muncul.
    """
    selected_skin_conditions = selected_conditions_set.intersection(SKIN_CONDITIONS)

    if not selected_skin_conditions:
        return False

    if package.package_type != Package.PackageType.GROOMING:
        return False

    has_skin_tag_match = bool(matched_tags.intersection(SKIN_CONDITIONS))

    return not has_skin_tag_match


def _should_skip_dry_grooming(package, selected_conditions_set):
    """
    Dry Grooming hanya muncul jika kondisi yang dipilih hanya: kuku panjang, telinga kotor, kuku panjang + telinga kotor
    Jika ada kondisi lain seperti bulu tebal, bulu kusut, kutu, jamur, atau styling, Dry Grooming tidak ikut direkomendasikan.
    """
    if not _is_dry_grooming(package):
        return False

    return not _selected_only_light_conditions(selected_conditions_set)


def _recommendation_priority(package, selected_conditions_set):
    """
    - Untuk kondisi kuku/telinga, Dry Grooming ditampilkan paling awal, lalu Daily Grooming, dan Full Package.
    - Paket additional selalu paling akhir.
    """
    is_additional = package.package_type == Package.PackageType.ADDITIONAL

    if is_additional:
        return 100

    if _selected_only_light_conditions(selected_conditions_set):
        if _is_dry_grooming(package):
            return 0
        if _is_daily_grooming(package):
            return 1
        if _is_full_package(package):
            return 2

    return 10


def get_recommended_packages(animal_type, selected_conditions):
    """
    - Paket dipilih berdasarkan recommendation_tags yang dipilih oleh staff.
    - Hanya mengambil paket aktif dan sesuai jenis hewan.
    - Paket muncul jika recommendation tag cocok dengan kondisi customer.
    - Kuku panjang / telinga kotor hanya menarik paket jika dipilih sendiri atau berdua saja.
    - Dry Grooming hanya muncul untuk kondisi kuku panjang/telinga kotor saja.
    - Jika kondisi berkutu + jamur, hanya muncul paket yang punya kedua tag saja.
    - Jika ada kondisi kulit, grooming umum yang hanya match kondisi non-kulit tidak muncul.
    - Paket additional tidak boleh menjadi satu-satunya rekomendasi.
    - Jika tidak ada rekomendasi spesifik, tampilkan grooming umum sebagai fallback.
    - Additional selalu ditampilkan paling akhir.
    """

    selected_conditions = selected_conditions or []
    selected_conditions_set = set(selected_conditions)

    packages = list(
        Package.objects
        .filter(is_deleted=False, animal_type=animal_type)
        .prefetch_related("prices")
        .order_by("package_type", "name")
    )

    recommended = []
    recommended_ids = set()

    for package in packages:
        package_tags = set(package.recommendation_tags or [])

        if _should_skip_dry_grooming(package, selected_conditions_set):
            continue

        matched_tags = _get_effective_matched_tags(
            package_tags=package_tags,
            selected_conditions_set=selected_conditions_set,
        )

        if not matched_tags:
            continue

        if not _has_exact_skin_match(package_tags, selected_conditions_set):
            continue

        if _should_skip_grooming_when_skin_selected(
            package=package,
            matched_tags=matched_tags,
            selected_conditions_set=selected_conditions_set,
        ):
            continue

        _add_package(package, recommended, recommended_ids)

    fallback_grooming = _find_fallback_grooming_package(
        packages=packages,
        animal_type=animal_type,
        selected_conditions_set=selected_conditions_set,
    )

    # Jika tidak ada hasil spesifik, tampilkan grooming umum.
    if not recommended and fallback_grooming:
        _add_package(fallback_grooming, recommended, recommended_ids)

    # Paket additional tidak boleh menjadi satu-satunya rekomendasi.
    has_grooming_package = any(
        package.package_type == Package.PackageType.GROOMING
        for package in recommended
    )

    if recommended and not has_grooming_package and fallback_grooming:
        _add_package(fallback_grooming, recommended, recommended_ids)

    recommended.sort(
        key=lambda package: (
            _recommendation_priority(package, selected_conditions_set),
            package.name.lower(),
        )
    )

    return recommended