from packages.models import Package

LIGHT_CAT_CONDITIONS = {"long_nails", "dirty_ears"}

SKIN_CONDITIONS = {"fleas", "fungus_irritation"}

RECOMMENDATION_RULES = {
    "cat": {
        # Kondisi bulu
        "thick_long_fur": {
            "include": ["daily grooming", "full package", "premium shampoo", "lion cut", "styling", "potong", "model"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },
        "dull_shedding_fur": {
            "include": ["daily grooming", "full package", "degreaser", "premium shampoo"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },
        "matted_fur": {
            "include": ["full package","premium shampoo", "styling", "potong", "model"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },

        # Kondisi kulit
        "fleas": {
            "include": ["kutu", "flea", "tick"],
            "exclude_if_single": ["jamur", "fungal", "anti fungal", "iritasi"],
        },
        "fungus_irritation": {
            "include": ["jamur", "fungal", "anti fungal", "iritasi"],
            "exclude_if_single": ["kutu", "flea", "tick"],
        },

        # Kondisi lainnya
        "long_nails": {
            "include": ["nail", "kuku", "dry grooming", "daily grooming", "full package"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },
        "dirty_ears": {
            "include": ["ear", "telinga", "dry grooming", "daily grooming", "full package"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },
        "styling": {
            "include": ["full package", "styling", "lion cut", "potong", "model"],
        },
    },

    "dog": {
        # Kondisi bulu
        "thick_long_fur": {
            "include": ["dry grooming", "hair trimming", "full package", "pitpet styling", "coat styling", "premium shampoo"],
        },
        "dull_shedding_fur": {
            "include": ["full package", "premium shampoo", "deep cleansing", "final touch"],
        },
        "matted_fur": {
            "include": ["dry grooming", "hair trimming", "full package", "pitpet styling", "coat styling", "styling"],
        },

        # Kondisi kulit
        "fleas": {
            "include": ["kutu", "flea", "tick"],
            "exclude_if_single": ["jamur", "fungal", "anti fungal", "iritasi"],
        },
        "fungus_irritation": {
            "include": ["jamur", "fungal", "anti fungal", "iritasi"],
            "exclude_if_single": ["kutu", "flea", "tick"],
        },

        # Kondisi lainnya
        "long_nails": {
            "include": ["nail", "kuku", "dry grooming", "full package"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },
        "dirty_ears": {
            "include": ["ear", "telinga", "dry grooming", "full package"],
            "exclude": ["kutu", "flea", "tick", "jamur", "fungal", "anti fungal"],
        },
        "styling": {
            "include": ["full package", "pitpet styling", "coat styling", "cukur", "styling"],
        },
    },
}


COMBINATION_RULES = {
    ("fleas", "fungus_irritation"): {
        "include_all_groups": [
            ["kutu", "flea", "tick"],
            ["jamur", "fungal", "anti fungal", "iritasi"],
        ],
    }
}


FALLBACK_RULES = {
    "cat": ["full package", "daily grooming"],
    "dog": ["full package", "dry grooming"],
}


def _package_text(package):
    return f"{package.name} {package.description}".lower()


def _contains_any(text, keywords):
    return any(keyword.lower() in text for keyword in keywords)


def _contains_all_keyword_groups(text, keyword_groups):
    return all(_contains_any(text, group) for group in keyword_groups)


def _add_package(package, recommended, recommended_ids):
    if package.id not in recommended_ids:
        recommended.append(package)
        recommended_ids.add(package.id)


def _find_fallback_grooming_package(packages, animal_type):
    fallback_keywords = FALLBACK_RULES.get(animal_type, [])

    grooming_packages = [
        package for package in packages
        if package.package_type == Package.PackageType.GROOMING
    ]

    for keyword in fallback_keywords:
        for package in grooming_packages:
            if keyword in _package_text(package):
                return package

    return grooming_packages[0] if grooming_packages else None

def skip_cat_light_condition(animal_type, condition, selected_conditions_set):
    """
    Untuk kucing:
    - Jika hanya pilih kuku panjang dan/atau telinga kotor,
      Dry Grooming/Daily Grooming/Full Package tetap direkomendasikan.
    - Jika kuku/telinga dipilih bersama kondisi lain, rule kuku/telinga dilewati
      karena paket dari kondisi lain biasanya sudah mencakup nail trimming/ear cleaning.
    """
    if animal_type != "cat":
        return False

    if condition not in LIGHT_CAT_CONDITIONS:
        return False

    return not selected_conditions_set.issubset(LIGHT_CAT_CONDITIONS)

def skip_general_grooming_when_skin_selected(package, condition, has_skin_condition):
    """
    Jika ada kondisi kulit, paket grooming umum dari kondisi non-skin tidak perlu ditampilkan
    """
    if not has_skin_condition:
        return False

    if condition in SKIN_CONDITIONS:
        return False

    return package.package_type == Package.PackageType.GROOMING

def get_recommended_packages(animal_type, selected_conditions):
    """
    Hybrid rule-based recommendation:
    - membaca keyword dari nama paket + deskripsi paket.
    - menggunakan include rule untuk mencari paket yang relevan.
    - menggunakan exclude rule agar rekomendasi tidak overlap.
    - jika ada kondisi kulit, paket grooming umum dari kondisi non-skin tidak ikut muncul, tapi paket additional/styling tetap muncul.
    - khusus fleas + fungus_irritation, sistem mencari paket yang mengandung keyword kutu dan jamur sekaligus.
    - hanya mengambil paket aktif dan sesuai jenis hewan.
    - additional package tidak boleh menjadi satu-satunya rekomendasi.
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

    animal_rules = RECOMMENDATION_RULES.get(animal_type, {})
    has_skin_condition = bool(selected_conditions_set.intersection(SKIN_CONDITIONS))

    # Special rule:
    # Jika customer memilih Berkutu + Berjamur/Iritasi,
    # prioritaskan paket yang mengandung keyword kutu dan jamur sekaligus.
    skip_individual_skin_treatment = False

    for condition_combo, combo_rule in COMBINATION_RULES.items():
        if set(condition_combo).issubset(selected_conditions_set):
            skip_individual_skin_treatment = True

            for package in packages:
                text = _package_text(package)

                if _contains_all_keyword_groups(text, combo_rule["include_all_groups"]):
                    _add_package(package, recommended, recommended_ids)

    # Rule per kondisi
    for condition in selected_conditions:
        # Jika sudah ada combo kutu+jamur, tidak pakai Mandi Kutu dan Mandi Jamur secara terpisah.
        if skip_individual_skin_treatment and condition in SKIN_CONDITIONS:
            continue
        
        # Untuk kucing, skip rule kuku/telinga jika customer juga memilih kondisi bulu/kulit lain.
        if skip_cat_light_condition(
            animal_type=animal_type,
            condition=condition,
            selected_conditions_set=selected_conditions_set,
        ):
            continue

        rule = animal_rules.get(condition)

        if not rule:
            continue

        include_keywords = rule.get("include", [])
        exclude_keywords = rule.get("exclude", [])
        exclude_if_single_keywords = rule.get("exclude_if_single", [])

        for package in packages:
            text = _package_text(package)

            if not _contains_any(text, include_keywords):
                continue

            if exclude_keywords and _contains_any(text, exclude_keywords):
                continue

            # Exclusion khusus untuk kondisi kulit tunggal:
            # - Berkutu saja tidak boleh menarik paket jamur.
            # - Jamur saja tidak boleh menarik paket kutu.
            if condition in ["fleas", "fungus_irritation"]:
                if exclude_if_single_keywords and _contains_any(text, exclude_if_single_keywords):
                    continue
                
            # Jika ada kutu/jamur, skip grooming umum dari kondisi non-skin.
            if skip_general_grooming_when_skin_selected(
                package=package,
                condition=condition,
                has_skin_condition=has_skin_condition,
            ):
                continue

            _add_package(package, recommended, recommended_ids)

    fallback_grooming = _find_fallback_grooming_package(packages, animal_type)

    # Jika tidak ada hasil spesifik, tampilkan paket grooming umum.
    if not recommended and fallback_grooming:
        _add_package(fallback_grooming, recommended, recommended_ids)

    # Paket additional tidak boleh menjadi satu-satunya rekomendasi.
    has_grooming_package = any(
        package.package_type == Package.PackageType.GROOMING
        for package in recommended
    )

    if recommended and not has_grooming_package and fallback_grooming:
        if fallback_grooming.id not in recommended_ids:
            recommended.insert(0, fallback_grooming)

    return recommended