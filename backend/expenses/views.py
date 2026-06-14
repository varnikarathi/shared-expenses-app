from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal, ROUND_HALF_UP
from .models import Expense, ExpenseSplit, Settlement
from .serializers import (
    ExpenseSerializer, CreateExpenseSerializer,
    SettlementSerializer, CreateSettlementSerializer
)
from groups.models import Group, GroupMembership
from users.models import User


USD_TO_INR = Decimal('83.5')


def calculate_splits(expense, split_details, members):
    ExpenseSplit.objects.filter(expense=expense).delete()
    amount = Decimal(str(expense.amount_inr or expense.amount))

    if expense.split_type == 'equal':
        share = (amount / len(members)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        remainder = amount - (share * len(members))
        for i, user in enumerate(members):
            amt = share + remainder if i == 0 else share
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=amt)

    elif expense.split_type == 'unequal':
        for user_id, amt in split_details.items():
            user = User.objects.get(id=int(user_id))
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=Decimal(str(amt)))

    elif expense.split_type == 'percentage':
        for user_id, pct in split_details.items():
            user = User.objects.get(id=int(user_id))
            amt = (amount * Decimal(str(pct)) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=amt, percentage=Decimal(str(pct)))

    elif expense.split_type == 'share':
        total_shares = sum(int(v) for v in split_details.values())
        for user_id, shares in split_details.items():
            user = User.objects.get(id=int(user_id))
            amt = (amount * Decimal(str(shares)) / Decimal(str(total_shares))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=amt, shares=int(shares))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def expenses_list(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        expenses = Expense.objects.filter(group=group, is_deleted=False).order_by('-date')
        return Response(ExpenseSerializer(expenses, many=True).data)

    if request.method == 'POST':
        data = request.data.copy()
        data['group'] = group_id
        serializer = CreateExpenseSerializer(data=data)
        if serializer.is_valid():
            split_details = serializer.validated_data.pop('split_details', {})
            expense = serializer.save()

            if expense.currency == 'USD':
                expense.amount_inr = (Decimal(str(expense.amount)) * USD_TO_INR).quantize(Decimal('0.01'))
            else:
                expense.amount_inr = expense.amount
            expense.save()

            if expense.split_type == 'equal':
                active_members = GroupMembership.objects.filter(
                    group=group, is_active=True,
                    joined_at__lte=expense.date
                )
                members = []
                for m in active_members:
                    if m.left_at is None or m.left_at >= expense.date:
                        members.append(m.user)
                if not members:
                    members = [expense.paid_by]
                calculate_splits(expense, {}, members)
            else:
                calculate_splits(expense, split_details, [])

            return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def expense_detail(request, group_id, expense_id):
    try:
        expense = Expense.objects.get(id=expense_id, group_id=group_id)
    except Expense.DoesNotExist:
        return Response({'error': 'Expense not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(ExpenseSerializer(expense).data)

    if request.method == 'PUT':
        serializer = CreateExpenseSerializer(expense, data=request.data, partial=True)
        if serializer.is_valid():
            split_details = serializer.validated_data.pop('split_details', {})
            expense = serializer.save()
            if split_details:
                calculate_splits(expense, split_details, [])
            return Response(ExpenseSerializer(expense).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        expense.is_deleted = True
        expense.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_balances(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    expenses = Expense.objects.filter(group=group, is_deleted=False)
    settlements = Settlement.objects.filter(group=group)

    balances = {}

    for expense in expenses:
        paid_by_id = expense.paid_by_id
        if paid_by_id not in balances:
            balances[paid_by_id] = {'user_id': paid_by_id, 'username': expense.paid_by.username, 'balance': Decimal('0')}
        amount = expense.amount_inr or expense.amount
        balances[paid_by_id]['balance'] += Decimal(str(amount))

        for split in expense.splits.all():
            uid = split.user_id
            if uid not in balances:
                balances[uid] = {'user_id': uid, 'username': split.user.username, 'balance': Decimal('0')}
            balances[uid]['balance'] -= split.amount_owed

    for settlement in settlements:
        paid_by_id = settlement.paid_by_id
        paid_to_id = settlement.paid_to_id
        if paid_by_id not in balances:
            balances[paid_by_id] = {'user_id': paid_by_id, 'username': settlement.paid_by.username, 'balance': Decimal('0')}
        if paid_to_id not in balances:
            balances[paid_to_id] = {'user_id': paid_to_id, 'username': settlement.paid_to.username, 'balance': Decimal('0')}
        balances[paid_by_id]['balance'] += settlement.amount
        balances[paid_to_id]['balance'] -= settlement.amount

    result = list(balances.values())
    for r in result:
        r['balance'] = float(r['balance'])

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def settlement_suggestions(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    expenses = Expense.objects.filter(group=group, is_deleted=False)
    settlements = Settlement.objects.filter(group=group)

    balances = {}

    for expense in expenses:
        paid_by_id = expense.paid_by_id
        amount = float(expense.amount_inr or expense.amount)
        balances[paid_by_id] = balances.get(paid_by_id, 0) + amount
        for split in expense.splits.all():
            balances[split.user_id] = balances.get(split.user_id, 0) - float(split.amount_owed)

    for s in settlements:
        balances[s.paid_by_id] = balances.get(s.paid_by_id, 0) + float(s.amount)
        balances[s.paid_to_id] = balances.get(s.paid_to_id, 0) - float(s.amount)

    creditors = sorted([(uid, bal) for uid, bal in balances.items() if bal > 0], key=lambda x: -x[1])
    debtors = sorted([(uid, -bal) for uid, bal in balances.items() if bal < 0], key=lambda x: -x[1])

    suggestions = []
    i, j = 0, 0
    creditors = list(creditors)
    debtors = list(debtors)

    while i < len(creditors) and j < len(debtors):
        cred_id, cred_amt = creditors[i]
        debt_id, debt_amt = debtors[j]
        amount = min(cred_amt, debt_amt)

        cred_user = User.objects.get(id=cred_id)
        debt_user = User.objects.get(id=debt_id)

        suggestions.append({
            'from': debt_user.username,
            'from_id': debt_id,
            'to': cred_user.username,
            'to_id': cred_id,
            'amount': round(amount, 2)
        })

        creditors[i] = (cred_id, cred_amt - amount)
        debtors[j] = (debt_id, debt_amt - amount)

        if creditors[i][1] < 0.01:
            i += 1
        if debtors[j][1] < 0.01:
            j += 1

    return Response(suggestions)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def settlements_list(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        settlements = Settlement.objects.filter(group=group).order_by('-date')
        return Response(SettlementSerializer(settlements, many=True).data)

    if request.method == 'POST':
        data = request.data.copy()
        data['group'] = group_id
        serializer = CreateSettlementSerializer(data=data)
        if serializer.is_valid():
            settlement = serializer.save()
            return Response(SettlementSerializer(settlement).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)