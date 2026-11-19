from django.contrib import admin
from .models import Department, Employee, Product, CalendarDay, WorkDay, OrderItem

admin.site.site_header = "Табель — панель управления"
admin.site.index_title = "Настройки и справочник"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "is_deleted", "created_at")
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("short_name", "department", "position",
                    "monthly_salary", "avg_trip_hourly_rate", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("last_name", "first_name", "patronymic")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_per_unit", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("name", "code")


@admin.register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ("date", "day_type", "norm_hours")
    list_filter = ("day_type",)
    date_hierarchy = "date"


class OrderItemInline(admin.TabularInline):
    """Позиции заказов редактируются прямо внутри дня — как в нашем UI."""
    model = OrderItem
    extra = 0
    fields = ("order_number", "product", "quantity", "fixed_price", "notes", "is_deleted")


@admin.register(WorkDay)
class WorkDayAdmin(admin.ModelAdmin):
    list_display = ("date", "employee", "status", "time_in", "time_out")
    list_filter = ("status", "employee__department")
    search_fields = ("employee__last_name",)
    date_hierarchy = "date"
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order_number", "product", "quantity", "fixed_price", "work_day", "is_deleted")
    list_filter = ("product", "is_deleted")
    search_fields = ("order_number", "product__name")