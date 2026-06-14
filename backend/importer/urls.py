from django.urls import path
from . import views

urlpatterns = [
    path('', views.import_csv, name='import_csv'),
    path('sessions/', views.import_sessions_list, name='import_sessions_list'),
    path('report/<int:session_id>/', views.import_report, name='import_report'),
    path('anomaly/<int:anomaly_id>/approve/', views.approve_anomaly, name='approve_anomaly'),
    path('anomaly/<int:anomaly_id>/reject/', views.reject_anomaly, name='reject_anomaly'),
]