from django.urls import path
from . import views

urlpatterns = [
    path('<int:group_id>/expenses/', views.expenses_list, name='expenses_list'),
    path('<int:group_id>/expenses/<int:expense_id>/', views.expense_detail, name='expense_detail'),
    path('<int:group_id>/balances/', views.group_balances, name='group_balances'),
    path('<int:group_id>/balance-breakdown/<int:user_id>/', views.balance_breakdown, name='balance_breakdown'),
    path('<int:group_id>/settlements/', views.settlements_list, name='settlements_list'),
    path('<int:group_id>/settlement-suggestions/', views.settlement_suggestions, name='settlement_suggestions'),
]