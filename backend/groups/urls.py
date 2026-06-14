from django.urls import path
from . import views

urlpatterns = [
    path('', views.groups_list, name='groups_list'),
    path('<int:group_id>/', views.group_detail, name='group_detail'),
    path('<int:group_id>/add-member/', views.add_member, name='add_member'),
    path('<int:group_id>/remove-member/', views.remove_member, name='remove_member'),
]