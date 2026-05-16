from datetime import timedelta, datetime, date
import calendar
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth
from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages

# SESUAIKAN IMPORT MODEL INI DENGAN PROJECT KAMU
from booking.models import Booking


def manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_api_request = request.path.startswith('/api/') or request.path.startswith('/manager/api/')
        wants_json = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('Accept', '')
        )

        if not request.user.is_authenticated:
            if is_api_request or wants_json:
                return JsonResponse({"detail": "Authentication required"}, status=401)
            messages.error(request, "Silakan login terlebih dahulu")
            return redirect('login')

        if getattr(request.user, "role", None) not in ["manager", "superadmin"]:
            if is_api_request or wants_json:
                return JsonResponse({"detail": "Forbidden"}, status=403)
            messages.error(request, "Anda tidak memiliki akses ke halaman ini")
            return redirect('login')

        return view_func(request, *args, **kwargs)

    return wrapper


BULAN_INDONESIA = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

HARI_SINGKAT = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


def get_fixed_range(periode):
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


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_period_range(request):
    periode = request.GET.get("periode", "bulanan")
    valid_periods = {
        "harian", "mingguan", "bulanan", "rentang_tanggal",
        "this_day", "this_month", "last_month", "this_year", "last_30_days", "last_7_days",
    }

    if periode not in valid_periods:
        return None, None, None, "Periode tidak valid"

    start_date = parse_date(request.GET.get("start_date"))
    end_date = parse_date(request.GET.get("end_date"))

    if periode == "rentang_tanggal":
        if not start_date or not end_date:
            return None, None, None, "Tanggal mulai harus sebelum tanggal akhir"

    elif periode == "harian":
        if start_date and not end_date:
            end_date = start_date
        if end_date and not start_date:
            start_date = end_date
        if not start_date:
            start_date = timezone.now().date()
            end_date = start_date

    elif periode == "mingguan":
        if start_date and not end_date:
            end_date = start_date + timedelta(days=6)
        if not start_date:
            today = timezone.now().date()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)

    elif periode == "bulanan":
        if not start_date:
            today = timezone.now().date()
            start_date = today.replace(day=1)
        if not end_date:
            last_day = calendar.monthrange(start_date.year, start_date.month)[1]
            end_date = date(start_date.year, start_date.month, last_day)

    else:
        start_date, end_date = get_fixed_range(periode)

    if start_date is None or end_date is None:
        return None, None, None, "Periode tidak valid"

    if start_date > end_date:
        return None, None, None, "Tanggal mulai harus sebelum tanggal akhir"

    return periode, start_date, end_date, None


def format_period_label(periode, start_date, end_date):
    if not start_date or not end_date:
        return ""

    def format_indonesia(dt):
        day = str(dt.day)
        month = BULAN_INDONESIA[dt.month - 1]
        return f"{day} {month} {dt.year}"

    if periode == "harian":
        return format_indonesia(start_date)

    if periode == "mingguan":
        week_number = ((start_date.day - 1) // 7) + 1
        month_label = BULAN_INDONESIA[start_date.month - 1]
        return f"Minggu {week_number} {month_label} {start_date.year}"

    if periode == "bulanan":
        month_label = BULAN_INDONESIA[start_date.month - 1]
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        if start_date.day == 1 and end_date.day == last_day and end_date.month == start_date.month:
            return f"{month_label} {start_date.year}"
        return f"{format_indonesia(start_date)} - {format_indonesia(end_date)}"

    return f"{format_indonesia(start_date)} - {format_indonesia(end_date)}"


def build_buckets(start_date: date, end_date: date, granularity: str, periode: str | None = None):
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
            if periode == "mingguan":
                label = HARI_SINGKAT[cur.weekday()]
            else:
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
            label = f"M{week_idx}"
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
    periode, start_date, end_date, error = parse_period_range(request)
    if error:
        return JsonResponse({"detail": error}, status=400)

    bookings = Booking.objects.exclude(status='cancelled').filter(tanggal__range=[start_date, end_date])

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

    top_groomers_query = (
        bookings.filter(status="service_completed")
        .values("groomer__id", "groomer__user__full_name")
        .annotate(total_layanan=Count("id"))
        .order_by("-total_layanan")[:3]
    )

    top_groomers = []
    for idx, g in enumerate(top_groomers_query, start=1):
        top_groomers.append({
            "rank": idx,
            "groomer_id": g["groomer__id"],
            "groomer_name": g["groomer__user__full_name"],
            "total_layanan": g["total_layanan"],
        })

    response_data = {
        "periode": periode,
        "periode_label": format_period_label(periode, start_date, end_date),
        "start_date": start_date,
        "end_date": end_date,
        "kpi_cards": {
            "total_booking": total_booking,
            "total_layanan_selesai": total_layanan_selesai,
            "total_pendapatan": total_pendapatan,
            "rata_rata_rating": round(rata_rata_rating, 1),
        },
        "service_distribution": service_distribution,
        "top_groomers": top_groomers,
    }

    return JsonResponse(response_data, status=200)


@manager_required
def operational_dashboard_page(request):
    return render(request, "operational_dashboard.html")


@manager_required
def report_trend(request):
    # legacy endpoint kept for compatibility (returns per-month aggregation)
    periode, start_date, end_date, error = parse_period_range(request)
    if error:
        return JsonResponse({"detail": error}, status=400)

    trend_query = (
        Booking.objects
        .exclude(status='cancelled')
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
    """API endpoint: /manager/api/reports/trend

    Query params:
    - periode: same as operational filters (harian, mingguan, bulanan, rentang_tanggal, or legacy values)
    - start_date, end_date: optional YYYY-MM-DD for range and period selection
    - jenis_data: 'booking' or 'layanan_selesai' (default 'booking')
    - granularity: optional override ['hour','day','week','month']

    Returns JSON: { periode, start_date, end_date, granularity, data: [{label,value}, ...] }
    """
    periode, start_date, end_date, error = parse_period_range(request)
    if error:
        return JsonResponse({"detail": error}, status=400)

    jenis_data = request.GET.get("jenis_data", "booking")
    granularity_param = request.GET.get("granularity")

    if jenis_data not in ("booking", "layanan_selesai"):
        return JsonResponse({"detail": "invalid jenis_data"}, status=400)

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

    buckets = build_buckets(start_date, end_date, granularity, periode)

    data = []

    for label, a, b in buckets:
        if granularity == "hour":
            hour = a
            count_qs = Booking.objects.exclude(status='cancelled').filter(tanggal=start_date, waktu_mulai__hour=hour)
        else:
            bucket_start = a
            bucket_end = b
            count_qs = Booking.objects.exclude(status='cancelled').filter(tanggal__range=[bucket_start, bucket_end])

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
