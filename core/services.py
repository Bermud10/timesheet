from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum

from .models import CalendarDay, DayType, WorkDay, WorkStatus

DEFAULT_IN = time(8, 0)
DEFAULT_OUT = time(17, 0)


def day_norm(d):
    cal = CalendarDay.objects.filter(date=d).first()
    if cal:
        return cal.norm_hours
    return Decimal(8) if d.weekday() < 5 else Decimal(0)


def day_hours(wd):
    """Часы дня по статусу (наше правило get_day_hours)."""
    if wd is None:
        return Decimal(0)
    if wd.status in (WorkStatus.VACATION, WorkStatus.DAY_OFF):
        return Decimal(0)
    if wd.status == WorkStatus.SICK:
        return day_norm(wd.date)
    tin = wd.time_in or DEFAULT_IN
    tout = wd.time_out or DEFAULT_OUT
    delta = datetime.combine(wd.date, tout) - datetime.combine(wd.date, tin)
    hours = Decimal(delta.total_seconds()) / 3600 - Decimal(settings.LUNCH_MINUTES) / 60
    return max(Decimal(0), hours)


def day_overtime(wd):
    if wd is None or wd.status not in (WorkStatus.WORKED, WorkStatus.TRIP):
        return Decimal(0)
    if wd.status == WorkStatus.TRIP and not settings.TRIP_OVERTIME_ENABLED:
        return Decimal(0)
    return max(Decimal(0), day_hours(wd) - day_norm(wd.date))


def month_norm(y, m):
    total = CalendarDay.objects.filter(date__year=y, date__month=m).aggregate(s=Sum("norm_hours"))["s"]
    if total is not None:
        return total
    # запасной вариант, если календарь не заполнен
    from calendar import monthrange
    days = monthrange(y, m)[1]
    return Decimal(8) * sum(1 for i in range(1, days + 1) if datetime(y, m, i).weekday() < 5)


def month_summary(employee, y, m):
    hours = ot = trip_ot = Decimal(0)
    days = 0
    for wd in WorkDay.objects.filter(employee=employee, date__year=y, date__month=m):
        h = day_hours(wd)
        o = day_overtime(wd)
        hours += h
        if wd.status == WorkStatus.WORKED:
            ot += o
            if h > 0:
                days += 1
        elif wd.status == WorkStatus.TRIP:
            trip_ot += o
    return {"hours": hours, "overtime": ot, "trip_overtime": trip_ot,
            "days": days, "norm": month_norm(y, m)}