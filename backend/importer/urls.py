from django.urls import path
from . import views

urlpatterns = [
    path('', views.import_csv, name='import_csv'),
    path('report/<int:session_id>/', views.import_report, name='import_report'),
]