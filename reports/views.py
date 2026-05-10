from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth
from functools import wraps
from django.shortcuts import render

# SESUAIKAN IMPORT MODEL INI DENGAN PROJECT KAMU
from booking.models import Booking


def manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "Authentication required"},
                status=401
            )

        # SESUAIKAN BAGIAN ROLE INI DENGAN PROJECT KAMU
        # kalau role disimpan di request.user.role
        if getattr(request.user, "role", None) != "manager":
            return JsonResponse(
                {"detail": "Forbidden"},
                status=403
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def get_period_range(periode):
    today = timezone.now().date()

    if periode == "this_month":
        start_date = today.replace(day=1)
        end_date = today

    elif periode == "last_month":
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)

    elif periode == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today

    elif periode == "last_30_days":
        start_date = today - timedelta(days=30)
        end_date = today

    elif periode == "last_7_days":
        start_date = today - timedelta(days=7)
        end_date = today

    else:
        start_date = today.replace(day=1)
        end_date = today

    return start_date, end_date


@manager_required
def operational_dashboard(request):
    periode = request.GET.get("periode", "this_month")
    start_date, end_date = get_period_range(periode)

    bookings = Booking.objects.filter(
        tanggal__range=[start_date, end_date]
    )

    total_booking = bookings.count()

    total_layanan_selesai = bookings.filter(
        status="service_completed"
    ).count()

    total_pendapatan = bookings.filter(
        payment_status="paid"
    ).aggregate(
        total=Sum("total_harga")
    )["total"] or 0

    rata_rata_rating = bookings.aggregate(
        avg_rating=Avg("review__rating")
    )["avg_rating"] or 0

    service_distribution_query = (
        bookings
        .values("service_type")
        .annotate(total=Count("id"))
        .order_by("service_type")
    )

    service_distribution = [
        {
            "service_type": item["service_type"] or "Unknown",
            "total": item["total"]
        }
        for item in service_distribution_query
    ]

    top_performer_query = (
        bookings
        .filter(status="service_completed")
        .values("groomer__id", "groomer__user__full_name")
        .annotate(
            total_layanan=Count("id"),
            rata_rata_rating=Avg("review__rating")
        )
        .order_by("-total_layanan", "-rata_rata_rating")
        .first()
    )

    top_performer_groomer = None

    if top_performer_query:
        top_performer_groomer = {
            "groomer_id": top_performer_query["groomer__id"],
            "groomer_name": top_performer_query["groomer__user__full_name"],
            "total_layanan": top_performer_query["total_layanan"],
            "rata_rata_rating": round(
                top_performer_query["rata_rata_rating"] or 0,
                1
            )
        }

    response_data = {
        "periode": periode,
        "start_date": start_date,
        "end_date": end_date,
        "kpi_cards": {
            "total_booking": total_booking,
            "total_layanan_selesai": total_layanan_selesai,
            "total_pendapatan": total_pendapatan,
            "rata_rata_rating": round(rata_rata_rating, 1),
        },
        "service_distribution": service_distribution,
        "top_performer_groomer": top_performer_groomer
    }

    return JsonResponse(response_data, status=200)


@manager_required
def operational_dashboard_page(request):
    return render(request, 'reports/operational_dashboard.html')


@manager_required
def report_trend(request):
    periode = request.GET.get("periode", "this_month")
    start_date, end_date = get_period_range(periode)

    trend_query = (
        Booking.objects
        .filter(tanggal__range=[start_date, end_date])
        .annotate(month=TruncMonth("tanggal"))
        .values("month")
        .annotate(
            total_booking=Count("id"),
            total_layanan_selesai=Count(
                "id",
                filter=Q(status="service_completed")
            )
        )
        .order_by("month")
    )

    trend_data = [
        {
            "month": item["month"].strftime("%b %Y"),
            "total_booking": item["total_booking"],
            "total_layanan_selesai": item["total_layanan_selesai"]
        }
        for item in trend_query
    ]

    if not trend_data:
        trend_data = [
            {
                "month": "No Data",
                "total_booking": 0,
                "total_layanan_selesai": 0
            }
        ]

    response_data = {
        "periode": periode,
        "start_date": start_date,
        "end_date": end_date,
        "trend": trend_data
    }

    return JsonResponse(response_data, status=200)