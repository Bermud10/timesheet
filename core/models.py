from django.db import models


class TimeStampedModel(models.Model):
    """Базовая модель с метками времени (наше правило аудита)."""
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("обновлено", auto_now=True)

    class Meta:
        abstract = True


class Department(TimeStampedModel):
    name = models.CharField("название", max_length=100, unique=True)
    is_deleted = models.BooleanField("удалён", default=False)  # мягкое удаление

    class Meta:
        verbose_name = "отдел"
        verbose_name_plural = "отделы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(TimeStampedModel):
    last_name = models.CharField("фамилия", max_length=50)
    first_name = models.CharField("имя", max_length=50)
    patronymic = models.CharField("отчество", max_length=50, blank=True)
    position = models.CharField("должность", max_length=100, blank=True)
    monthly_salary = models.DecimalField(
        "оклад", max_digits=10, decimal_places=2, default=0
    )
    avg_trip_hourly_rate = models.DecimalField(
        "средняя часовая (командировки)",
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    department = models.ForeignKey(
        Department, verbose_name="отдел",
        on_delete=models.PROTECT, related_name="employees",
    )
    is_active = models.BooleanField("активен", default=True)  # уволен = скрыт, история жива

    class Meta:
        verbose_name = "сотрудник"
        verbose_name_plural = "сотрудники"
        ordering = ["last_name", "first_name"]

    @property
    def short_name(self):
        """Вид как в Excel: Фигурин М. В."""
        parts = [self.last_name]
        if self.first_name:
            parts.append(self.first_name[0] + ".")
        if self.patronymic:
            parts.append(self.patronymic[0] + ".")
        return " ".join(parts)

    def __str__(self):
        return self.short_name


class Product(TimeStampedModel):
    """Глобальный справочник изделий/работ, расценка за 1 шт."""
    name = models.CharField("название", max_length=100)
    code = models.CharField("код", max_length=20, unique=True)
    price_per_unit = models.DecimalField("расценка за шт.", max_digits=10, decimal_places=2)
    is_deleted = models.BooleanField("удалён", default=False)

    class Meta:
        verbose_name = "изделие"
        verbose_name_plural = "изделия"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DayType(models.TextChoices):
    WORK = "work", "Рабочий"
    WEEKEND = "weekend", "Выходной"
    HOLIDAY = "holiday", "Праздник"
    SHORTENED = "shortened", "Укороченный"


class CalendarDay(models.Model):
    """Производственный календарь: тип дня + норма часов."""
    date = models.DateField("дата", unique=True)
    day_type = models.CharField(
        "тип дня", max_length=10, choices=DayType.choices, default=DayType.WORK
    )
    norm_hours = models.DecimalField("норма часов", max_digits=4, decimal_places=1, default=8)

    class Meta:
        verbose_name = "день календаря"
        verbose_name_plural = "календарь"
        ordering = ["date"]

    def __str__(self):
        return f"{self.date:%d.%m.%Y} ({self.get_day_type_display()})"


class WorkStatus(models.TextChoices):
    WORKED = "worked", "Отработан"
    SICK = "sick", "Больничный"
    VACATION = "vacation", "Отпуск"
    TRIP = "trip", "Командировка"
    DAY_OFF = "day_off", "Отгул"


class WorkDay(TimeStampedModel):
    """Одна запись = один день одного сотрудника."""
    employee = models.ForeignKey(
        Employee, verbose_name="сотрудник",
        on_delete=models.PROTECT, related_name="work_days",
    )
    date = models.DateField("дата")
    time_in = models.TimeField("пришёл", null=True, blank=True)
    time_out = models.TimeField("ушёл", null=True, blank=True)
    status = models.CharField(
        "статус", max_length=10, choices=WorkStatus.choices, default=WorkStatus.WORKED
    )
    trip_rate_applied = models.DecimalField(
        "применённая средняя ставка",
        max_digits=10, decimal_places=2, null=True, blank=True,
    )  # заморозка ставки на день командировки

    class Meta:
        verbose_name = "рабочий день"
        verbose_name_plural = "рабочие дни"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="uniq_employee_date")
        ]

    def __str__(self):
        return f"{self.employee} — {self.date:%d.%m.%Y}"


class OrderItem(TimeStampedModel):
    """Одна строка выполненных работ = позиция заказа."""
    work_day = models.ForeignKey(
        WorkDay, verbose_name="день",
        on_delete=models.CASCADE, related_name="order_items",
    )
    order_number = models.CharField("№ заказа", max_length=30, db_index=True)
    product = models.ForeignKey(
        Product, verbose_name="изделие",
        on_delete=models.PROTECT, related_name="order_items",
    )
    quantity = models.PositiveIntegerField("количество", default=1)
    fixed_price = models.DecimalField("зафиксированная цена", max_digits=10, decimal_places=2)
    notes = models.TextField("заметки", blank=True)
    is_deleted = models.BooleanField("удалён", default=False)

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказов"
        ordering = ["-created_at"]

    def __str__(self):
        return f"№{self.order_number} {self.product} ×{self.quantity}"

    @property
    def total(self):
        return self.quantity * self.fixed_price