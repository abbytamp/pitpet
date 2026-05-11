from datetime import timedelta, datetime, date
import calendar
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
            return JsonResponse({"detail": "Authentication required"}, status=401)

        # SESUAIKAN BAGIAN ROLE INI DENGAN PROJECT KAMU
        if getattr(request.user, "role", None) != "manager":
            return JsonResponse({"detail": "Forbidden"}, status=403)

        return view_func(request, *args, **kwargs)

    return wrapper


def get_period_range(periode):
    today = timezone.now().date()

    if periode == "this_day":
        start_date = today
        end_date = today

    elif periode == "this_month":
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


def parse_custom_range(request):
    """Parse optional `start` and `end` query params in YYYY-MM-DD format.
    Returns (start_date, end_date) or (None, None) if not provided/invalid.
    """
    s = request.GET.get("start")
    e = request.GET.get("end")
    if not s or not e:
        return None, None
    try:
        start_date = datetime.strptime(s, "%Y-%m-%d").date()
        end_date = datetime.strptime(e, "%Y-%m-%d").date()
        if start_date > end_date:
            return None, None
        return start_date, end_date
    except Exception:
        return None, None


def build_buckets(start_date: date, end_date: date, granularity: str):
    """Return list of buckets where each bucket is (label, bucket_start, bucket_end).
    bucket_end is inclusive date for day/week/month, and for hour granularity bucket_start/ end are ints (hour).
    """
    buckets = []
    if granularity == "hour":
        # fixed hours 09..17
        for h in range(9, 18):
            label = f"{h:02d}:00"
            buckets.append((label, h, h))
        return buckets

    if granularity == "day":
        cur = start_date
        while cur <= end_date:
            label = cur.strftime("%d %b")
            buckets.append((label, cur, cur))
            cur += timedelta(days=1)
        return buckets

    if granularity == "week":
        cur = start_date
        week_idx = 1
        # weeks of 7 days
        while cur <= end_date:
            week_start = cur
            week_end = min(cur + timedelta(days=6), end_date)
            label = f"W{week_idx}"
            buckets.append((label, week_start, week_end))
            cur = week_end + timedelta(days=1)
            week_idx += 1
        return buckets

    if granularity == "month":
        cur = start_date.replace(day=1)
        month_idx = 1
        while cur <= end_date:
            last_day = calendar.monthrange(cur.year, cur.month)[1]
            month_start = cur
            month_end = date(cur.year, cur.month, last_day)
            label = cur.strftime("%b %Y")
            buckets.append((label, month_start, month_end))
            # move to first day of next month
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1, day=1)
            else:
                cur = cur.replace(month=cur.month + 1, day=1)
            month_idx += 1
        return buckets

    return buckets


@manager_required
def operational_dashboard(request):
    periode = request.GET.get("periode", "this_month")
    start_date, end_date = get_period_range(periode)

    bookings = Booking.objects.filter(tanggal__range=[start_date, end_date])

    total_booking = bookings.count()

    total_layanan_selesai = bookings.filter(status="service_completed").count()

    total_pendapatan = bookings.filter(payment_status="paid").aggregate(total=Sum("total_harga"))["total"] or 0

    rata_rata_rating = bookings.aggregate(avg_rating=Avg("review__rating"))["avg_rating"] or 0

    service_distribution_query = (
        bookings.values("service_type").annotate(total=Count("id")).order_by("service_type")
    )

    service_distribution = [
        {"service_type": item["service_type"] or "Unknown", "total": item["total"]}
        for item in service_distribution_query
    ]

    top_performer_query = (
        bookings.filter(status="service_completed").values("groomer__id", "groomer__user__full_name").annotate(
            total_layanan=Count("id"), rata_rata_rating=Avg("review__rating")
        ).order_by("-total_layanan", "-rata_rata_rating").first()
    )

    top_performer_groomer = None
    if top_performer_query:
        top_performer_groomer = {
            "groomer_id": top_performer_query["groomer__id"],
            "groomer_name": top_performer_query["groomer__user__full_name"],
            "total_layanan": top_performer_query["total_layanan"],
            "rata_rata_rating": round(top_performer_query["rata_rata_rating"] or 0, 1),
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
        "top_performer_groomer": top_performer_groomer,
    }

    return JsonResponse(response_data, status=200)


@manager_required
def operational_dashboard_page(request):
    return render(request, "reports/operational_dashboard.html")


@manager_required
def report_trend(request):
    # legacy endpoint kept for compatibility (returns per-month aggregation)
    periode = request.GET.get("periode", "this_month")
    start_date, end_date = get_period_range(periode)

    trend_query = (
        Booking.objects
        .filter(tanggal__range=[start_date, end_date])
        .annotate(month=TruncMonth("tanggal"))
        .values("month")
        .annotate(
            total_booking=Count("id"),
            total_layanan_selesai=Count("id", filter=Q(status="service_completed"))
        )
        .order_by("month")
    )

    trend_data = [
        {"month": item["month"].strftime("%b %Y"), "total_booking": item["total_booking"], "total_layanan_selesai": item["total_layanan_selesai"]}
        for item in trend_query
    ]

    if not trend_data:
        trend_data = [{"month": "No Data", "total_booking": 0, "total_layanan_selesai": 0}]

    response_data = {"periode": periode, "start_date": start_date, "end_date": end_date, "trend": trend_data}

    return JsonResponse(response_data, status=200)


@manager_required
def report_trend_api(request):
    """API endpoint: /reports/api/trend

    Query params:
    - periode: same as operational filters (this_day, this_month, last_7_days, last_30_days, this_year, last_month)
    - start, end: optional YYYY-MM-DD for custom range (use periode=custom or omit)
    - jenis_data: 'booking' or 'layanan_selesai' (default 'booking')
    - granularity: optional override ['hour','day','week','month']

    Returns JSON: { periode, start_date, end_date, granularity, data: [{label,value}, ...] }
    """
    periode = request.GET.get("periode", "this_month")
    jenis_data = request.GET.get("jenis_data", "booking")
    granularity_param = request.GET.get("granularity")

    if jenis_data not in ("booking", "layanan_selesai"):
        return JsonResponse({"detail": "invalid jenis_data"}, status=400)

    # parse custom range if provided
    custom_start, custom_end = parse_custom_range(request)
    if custom_start and custom_end:
        start_date, end_date = custom_start, custom_end
    else:
        start_date, end_date = get_period_range(periode)

    # auto-detect granularity if not provided
    if granularity_param in ("hour", "day", "week", "month"):
        granularity = granularity_param
    else:
        if start_date == end_date:
            granularity = "hour"
        else:
            diff_days = (end_date - start_date).days
            if diff_days < 14:
                granularity = "day"
            elif 14 <= diff_days <= 90:
                granularity = "week"
            else:
                granularity = "month"

    buckets = build_buckets(start_date, end_date, granularity)

    data = []

    for label, a, b in buckets:
        if granularity == "hour":
            hour = a
            count_qs = Booking.objects.filter(tanggal=start_date, waktu_mulai__hour=hour)
        else:
            bucket_start = a
            bucket_end = b
            count_qs = Booking.objects.filter(tanggal__range=[bucket_start, bucket_end])

        if jenis_data == "booking":
            cnt = count_qs.count()
        else:
            cnt = count_qs.filter(status="service_completed").count()

        data.append({"label": label, "value": cnt})

    # ensure zero values for empty buckets already handled by iteration

    response = {
        "periode": periode,
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "jenis_data": jenis_data,
        "data": data,
    }

    return JsonResponse(response, status=200)
