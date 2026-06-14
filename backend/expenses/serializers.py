from rest_framework import serializers
from .models import Expense, ExpenseSplit, Settlement
from users.serializers import UserSerializer
from groups.serializers import GroupSerializer


class ExpenseSplitSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ExpenseSplit
        fields = ['id', 'user', 'amount_owed', 'percentage', 'shares']


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by = UserSerializer(read_only=True)
    splits = ExpenseSplitSerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'group', 'description', 'amount', 'currency',
            'amount_inr', 'paid_by', 'date', 'split_type',
            'notes', 'is_deleted', 'splits', 'created_at'
        ]


class CreateExpenseSerializer(serializers.ModelSerializer):
    split_details = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Expense
        fields = [
            'group', 'description', 'amount', 'currency',
            'paid_by', 'date', 'split_type', 'notes', 'split_details'
        ]


class SettlementSerializer(serializers.ModelSerializer):
    paid_by = UserSerializer(read_only=True)
    paid_to = UserSerializer(read_only=True)

    class Meta:
        model = Settlement
        fields = ['id', 'group', 'paid_by', 'paid_to', 'amount', 'currency', 'date', 'notes', 'created_at']


class CreateSettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ['group', 'paid_by', 'paid_to', 'amount', 'currency', 'date', 'notes']