from datetime import date, timedelta
from decimal import Decimal

import requests
from django.core.management.base import BaseCommand

from core.models import CalendarDay, DayType

# Федеральные праздники РФ (месяц, день)
FEDERAL_HOLIDAYS = {
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
    (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4),
}


class Command(BaseCommand):
    help = "Заполняет производственный календарь на год (идемпотентно)"

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument(
            "--fetch", action="store_true",
            help="загрузить точный календарь с isdayoff.ru (учитывает переносы)",
        )

    def handle(self, *args, **options):
        year = options["year"]
        days = self._fetch(year) if options["fetch"] else self._compute(year)

        created = updated = 0
        for d, day_type, norm in days:
            _, was_created = CalendarDay.objects.update_or_create(
                date=d, defaults={"day_type": day_type, "norm_hours": norm},
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"{year}: создано {created}, обновлено {updated}"
        ))

    def _compute(self, year):
        """Офлайн-режим: выходные + праздники + предпраздничные 7ч.
        Не учитывает правительственные переносы — для точности используй --fetch."""
        d = date(year, 1, 1)
        while d.year == year:
            md = (d.month, d.day)
            if md in FEDERAL_HOLIDAYS:
                yield d, DayType.HOLIDAY, Decimal("0")
            elif d.weekday() >= 5:
                yield d, DayType.WEEKEND, Decimal("0")
            elif (d + timedelta(days=1)).month * 100 + (d + timedelta(days=1)).day in {
                m * 100 + dd for m, dd in FEDERAL_HOLIDAYS
            }:
                yield d, DayType.SHORTENED, Decimal("7")
            else:
                yield d, DayType.WORK, Decimal("8")
            d += timedelta(days=1)

    def _fetch(self, year):
        """Точный календарь с isdayoff.ru: 0=рабочий, 1=выходной/праздник, 2=укороченный."""
        resp = requests.get(
            f"https://isdayoff.ru/api/getdata?year={year}&cc=ru&pre=1", timeout=30
        )
        resp.raise_for_status()
        data = resp.text.strip()

        expected = (date(year + 1, 1, 1) - date(year, 1, 1)).days
        if len(data) != expected:
            raise ValueError(f"Ожидал {expected} дней, получил {len(data)}")

        d = date(year, 1, 1)
        for digit in data:
            if digit == "0":
                yield d, DayType.WORK, Decimal("8")
            elif digit == "2":
                yield d, DayType.SHORTENED, Decimal("7")
            else:  # 1
                kind = DayType.HOLIDAY if (d.month, d.day) in FEDERAL_HOLIDAYS else DayType.WEEKEND
                yield d, kind, Decimal("0")
            d += timedelta(days=1)