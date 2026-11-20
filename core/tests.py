from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from core import services as s
from core.models import CalendarDay, DayType, Department, Employee, WorkDay, WorkStatus


class CalcTests(TestCase):
    def setUp(self):
        d = Department.objects.create(name="Отдел")
        self.emp = Employee.objects.create(last_name="Ф", first_name="М", department=d, monthly_salary=50400)
        CalendarDay.objects.create(date=date(2026, 11, 3), day_type=DayType.WORK, norm_hours=8)
        CalendarDay.objects.create(date=date(2026, 11, 4), day_type=DayType.HOLIDAY, norm_hours=0)

    def test_overtime_8_to_19(self):
        wd = WorkDay.objects.create(employee=self.emp, date=date(2026, 11, 3),
                                    time_in=time(8), time_out=time(19), status=WorkStatus.WORKED)
        self.assertEqual(s.day_hours(wd), Decimal(10))
        self.assertEqual(s.day_overtime(wd), Decimal(2))

    def test_missing_out_defaults_to_norm(self):
        wd = WorkDay.objects.create(employee=self.emp, date=date(2026, 11, 3),
                                    time_in=time(8), status=WorkStatus.WORKED)
        self.assertEqual(s.day_hours(wd), Decimal(8))
        self.assertEqual(s.day_overtime(wd), Decimal(0))

    def test_vacation_zero(self):
        wd = WorkDay.objects.create(employee=self.emp, date=date(2026, 11, 3), status=WorkStatus.VACATION)
        self.assertEqual(s.day_hours(wd), Decimal(0))

    def test_holiday_norm_zero(self):
        self.assertEqual(s.day_norm(date(2026, 11, 4)), Decimal(0))