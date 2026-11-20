from calendar import monthrange
from datetime import date, time
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from datetime import date, time, timedelta

from .models import CalendarDay, DayType, Employee, WorkDay, WorkStatus
from . import services as s

MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _month_ctx(y, m):
    prev = (date(y, m, 1) - __import__("datetime").timedelta(days=1))
    nxt = (date(y, m, monthrange(y, m)[1]) + __import__("datetime").timedelta(days=1))
    return {"year": y, "month": m, "month_label": f"{MONTHS_RU[m-1]} {y}",
            "prev": {"y": prev.year, "m": prev.month},
            "next": {"y": nxt.year, "m": nxt.month},
            "month_start": date(y, m, 1), "month_end": date(y, m, monthrange(y, m)[1])}


def _get_month(request):
    today = date.today()
    return int(request.GET.get("year", today.year)), int(request.GET.get("month", today.month))


def _row(emp, d, cal, wd):
    hours = s.day_hours(wd)
    ot = s.day_overtime(wd)
    if cal and cal.day_type == DayType.WEEKEND:
        css = "weekend"
    elif cal and cal.day_type == DayType.HOLIDAY:
        css = "holiday"
    elif ot > 0:
        css = "overtime"
    else:
        css = ""
    return {"date": d, "weekday": WEEKDAYS_RU[d.weekday()],
            "type_label": cal.get_day_type_display() if cal else ("Выходной" if d.weekday() >= 5 else "Рабочий"),
            "status": wd.status if wd else WorkStatus.WORKED,
            "time_in": wd.time_in if wd else None,
            "time_out": wd.time_out if wd else None,
            "hours": hours, "overtime": ot, "css": css}


def dashboard(request):
    y, m = _get_month(request)
    cards = [{"emp": e, "sum": s.month_summary(e, y, m)}
             for e in Employee.objects.filter(is_active=True).select_related("department")]
    return render(request, "core/dashboard.html", {**_month_ctx(y, m), "cards": cards})


def employee_month(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    y, m = _get_month(request)
    cals = {c.date: c for c in CalendarDay.objects.filter(date__year=y, date__month=m)}
    wds = {w.date: w for w in WorkDay.objects.filter(employee=emp, date__year=y, date__month=m)}
    rows = [_row(emp, date(y, m, d), cals.get(date(y, m, d)), wds.get(date(y, m, d)))
            for d in range(1, monthrange(y, m)[1] + 1)]
    return render(request, "core/employee_month.html",
                  {**_month_ctx(y, m), "employee": emp, "rows": rows,
                   "sum": s.month_summary(emp, y, m), "statuses": WorkStatus.choices})


def save_day(request, pk, date):
    emp = get_object_or_404(Employee, pk=pk)
    d = date.fromisoformat(date)
    wd, _ = WorkDay.objects.get_or_create(employee=emp, date=d)
    wd.status = request.POST.get("status") or WorkStatus.WORKED
    tin = request.POST.get("time_in")
    tout = request.POST.get("time_out")
    wd.time_in = time.fromisoformat(tin) if tin else None
    wd.time_out = time.fromisoformat(tout) if tout else None
    if wd.status == WorkStatus.TRIP and wd.trip_rate_applied is None:
        wd.trip_rate_applied = emp.avg_trip_hourly_rate
    wd.save()
    cal = CalendarDay.objects.filter(date=d).first()
    return render(request, "core/_day_row.html",
                  {"row": _row(emp, d, cal, wd), "employee": emp, "statuses": WorkStatus.choices})


def bulk_fill(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    y = int(request.POST.get("year")); m = int(request.POST.get("month"))
    start = date.fromisoformat(request.POST["start"])
    end = date.fromisoformat(request.POST["end"])
    created = 0
    d = start
    from datetime import timedelta
    while d <= end:
        cal = CalendarDay.objects.filter(date=d).first()
        if cal and cal.norm_hours > 0 and cal.day_type in (DayType.WORK, DayType.SHORTENED):
            _, was_new = WorkDay.objects.get_or_create(
                employee=emp, date=d,
                defaults={"time_in": s.DEFAULT_IN, "time_out": s.DEFAULT_OUT, "status": WorkStatus.WORKED})
            created += was_new
        d += timedelta(days=1)
    messages.success(request, f"Заполнено дней: {created} (выходные и праздники пропущены)")
    return redirect(f"{reverse('core:employee_month', args=[pk])}?year={y}&month={m}")