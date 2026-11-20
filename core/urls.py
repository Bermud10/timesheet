from django.urls import path
from . import views

app_name = "core"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("employee/<int:pk>/", views.employee_month, name="employee_month"),
    path("employee/<int:pk>/save/<str:date>/", views.save_day, name="save_day"),
    path("employee/<int:pk>/bulk/", views.bulk_fill, name="bulk_fill"),
]