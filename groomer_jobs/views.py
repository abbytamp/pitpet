from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render


@login_required
def daily_job_list(request):
    user = request.user

    if getattr(user, "role", None) != "groomer":
        return HttpResponseForbidden(
            "403 Forbidden: hanya groomer yang dapat mengakses halaman ini."
        )

    # TODO: butuh data groomer profile:
    # - nama groomer
    # - no hp
    # - jenis layanan (home / clinic)
    groomer_name = getattr(user, "full_name", None) or getattr(user, "username", "Groomer")
    groomer_phone = getattr(user, "phone_number", "-")
    groomer_service_type = "-"

    # TODO: butuh data booking hari ini milik groomer yang login
    # Kriteria query nantinya:
    # - hanya booking milik groomer yang sedang login
    # - tanggal layanan = hari ini
    # - status cancelled tidak ditampilkan
    # - scheduled & service_started masuk "today_tasks"
    # - service_completed masuk "today_history"
    today_tasks = []
    today_history = []

    # Contoh struktur data booking yang nanti dibutuhkan template:
    # today_tasks = [
    #     {
    #         "id": 1,
    #         "time_range": "11:00 - 11:30",
    #         "owner_name": "Isa",
    #         "pet_names": "Mochi (Cat), Buddy (Dog)",
    #         "service_type_label": "Home Service",
    #         "status": "service_started",
    #         "status_label": "Service Started",
    #     }
    # ]

    context = {
        "page_title": "Daftar Pekerjaan Hari Ini",
        "today": date.today(),
        "groomer_name": groomer_name,
        "groomer_phone": groomer_phone,
        "groomer_service_type": groomer_service_type,
        "unfinished_count": len(today_tasks),
        "completed_count": len(today_history),
        "today_tasks": today_tasks,
        "today_history": today_history,
    }
    return render(request, "groomer_jobs/daily_job_list.html", context)