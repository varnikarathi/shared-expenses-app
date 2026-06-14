import csv
import io
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ImportSession, ImportAnomaly
from expenses.models import Expense, ExpenseSplit, Settlement
from groups.models import Group, GroupMembership
from users.models import User

USD_TO_INR = Decimal('83.5')

KNOWN_MEMBERS = {
    'aisha': None,
    'rohan': None,
    'priya': None,
    'meera': None,
    'dev': None,
    'sam': None,
}

MEERA_LEFT = date(2026, 3, 31)
SAM_JOINED = date(2026, 4, 15)


def parse_date(raw):
    raw = raw.strip()
    formats = [
        '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y',
        '%m/%d/%Y', '%d-%b-%Y', '%b-%d',
    ]
    for fmt in formats:
        try:
            d = datetime.strptime(raw, fmt)
            if d.year == 1900:
                d = d.replace(year=2026)
            return d.date(), None
        except ValueError:
            continue
    return None, f"Cannot parse date: '{raw}'"


def normalize_name(name):
    if not name:
        return None
    name = name.strip().lower()
    for known in KNOWN_MEMBERS:
        if name == known or name.startswith(known):
            return known.capitalize()
    return None


def fuzzy_match_name(name):
    if not name:
        return None
    name = name.strip().lower()
    for known in KNOWN_MEMBERS:
        if known in name or name in known:
            return known.capitalize()
    return None


def parse_amount(raw):
    if not raw:
        return None, "Amount is missing"
    raw = str(raw).strip().replace(',', '').replace('₹', '').replace('$', '').strip()
    try:
        val = Decimal(raw)
        return val, None
    except InvalidOperation:
        return None, f"Cannot parse amount: '{raw}'"


def get_user(name):
    return User.objects.filter(username__iexact=name).first()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_csv(request):
    if 'file' not in request.FILES:
        return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

    group_id = request.data.get('group_id')
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    for membership in GroupMembership.objects.filter(group=group):
        uname = membership.user.username.lower()
        KNOWN_MEMBERS[uname] = membership.user

    csv_file = request.FILES['file']
    decoded = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)

    session = ImportSession.objects.create(
        filename=csv_file.name,
        imported_by=request.user,
        status='pending',
        total_rows=len(rows)
    )

    anomalies = []
    imported = []
    skipped = []
    seen_expenses = {}

    def log_anomaly(row_num, raw, atype, desc, action, resolution, requires_approval=False):
        anomalies.append({
            'row': row_num,
            'raw': raw,
            'type': atype,
            'description': desc,
            'action': action,
            'resolution': resolution,
            'requires_approval': requires_approval
        })
        ImportAnomaly.objects.create(
            session=session,
            row_number=row_num,
            raw_data=raw,
            anomaly_type=atype,
            description=desc,
            action_taken=action,
            resolution=resolution,
            requires_approval=requires_approval
        )

    for i, row in enumerate(rows, start=2):
        raw = dict(row)

        # Skip blank rows
        if all(not v.strip() for v in row.values() if v):
            log_anomaly(i, raw, 'BLANK_ROW', 'Row is completely empty', 'skipped', 'Skipped silently')
            skipped.append(i)
            continue

        # DATE
        raw_date = row.get('date', '').strip()
        parsed_date, date_error = parse_date(raw_date)
        if date_error:
            log_anomaly(i, raw, 'DATE_FORMAT', date_error, 'skipped', 'Could not parse date, row skipped')
            skipped.append(i)
            continue

        # DESCRIPTION
        description = row.get('description', '').strip()
        if not description:
            description = 'Unnamed expense'
            log_anomaly(i, raw, 'MISSING_DESCRIPTION', 'Description is blank', 'auto_fixed', 'Set to "Unnamed expense"')

        # SETTLEMENT DETECTION
        notes = row.get('notes', '').strip().lower()
        desc_lower = description.lower()
        settlement_keywords = ['settlement', 'paid back', 'paid aisha back', 'deposit share']
        if any(kw in desc_lower or kw in notes for kw in settlement_keywords):
            log_anomaly(i, raw, 'SETTLEMENT_AS_EXPENSE',
                f'Row "{description}" appears to be a settlement, not an expense',
                'auto_fixed', 'Reclassified as settlement')

            payer_name = normalize_name(row.get('paid_by', '')) or fuzzy_match_name(row.get('paid_by', ''))
            split_with = row.get('split_with', '')
            payee_name = None
            if split_with:
                parts = [p.strip() for p in split_with.replace(';', ',').split(',')]
                for p in parts:
                    n = normalize_name(p) or fuzzy_match_name(p)
                    if n and n != payer_name:
                        payee_name = n
                        break

            amount, amt_err = parse_amount(row.get('amount', ''))
            if not amt_err and payer_name and payee_name:
                payer = get_user(payer_name)
                payee = get_user(payee_name)
                if payer and payee:
                    Settlement.objects.create(
                        group=group,
                        paid_by=payer,
                        paid_to=payee,
                        amount=amount,
                        currency=row.get('currency', 'INR').strip() or 'INR',
                        date=parsed_date,
                        notes=row.get('notes', '')
                    )
            imported.append(i)
            continue

        # AMOUNT
        raw_amount = row.get('amount', '').strip()
        amount, amt_error = parse_amount(raw_amount)
        if amt_error:
            log_anomaly(i, raw, 'MISSING_AMOUNT', amt_error, 'skipped', 'Row skipped due to missing/invalid amount')
            skipped.append(i)
            continue

        if amount == 0:
            log_anomaly(i, raw, 'ZERO_AMOUNT', f'Amount is 0 for "{description}"', 'skipped', 'Skipped - likely a correction placeholder')
            skipped.append(i)
            continue

        if amount < 0:
            log_anomaly(i, raw, 'NEGATIVE_AMOUNT', f'Negative amount {amount} for "{description}"', 'auto_fixed', 'Treated as refund (negative expense)')

        rounded = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if rounded != amount:
            log_anomaly(i, raw, 'PRECISION', f'Amount {amount} has >2 decimal places', 'auto_fixed', f'Rounded to {rounded}')
            amount = rounded

        # CURRENCY
        currency = row.get('currency', '').strip().upper()
        if not currency:
            currency = 'INR'
            log_anomaly(i, raw, 'MISSING_CURRENCY', 'Currency field is blank', 'auto_fixed', 'Defaulted to INR')
        if currency not in ['INR', 'USD']:
            currency = 'INR'
            log_anomaly(i, raw, 'INVALID_CURRENCY', 'Unknown currency, defaulting to INR', 'auto_fixed', 'Set to INR')

        amount_inr = amount
        if currency == 'USD':
            amount_inr = (amount * USD_TO_INR).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            log_anomaly(i, raw, 'USD_CONVERSION', f'USD amount {amount} converted to INR', 'auto_fixed', f'Converted at rate 83.5: ₹{amount_inr}')

        # PAID BY
        raw_paid_by = row.get('paid_by', '').strip()
        paid_by_name = normalize_name(raw_paid_by)
        if not paid_by_name:
            paid_by_name = fuzzy_match_name(raw_paid_by)
            if paid_by_name:
                log_anomaly(i, raw, 'NAME_CASE', f'paid_by "{raw_paid_by}" normalized to "{paid_by_name}"', 'auto_fixed', 'Normalized name')
            else:
                log_anomaly(i, raw, 'MISSING_PAYER', f'paid_by "{raw_paid_by}" is unknown', 'skipped', 'Row skipped - cannot identify payer')
                skipped.append(i)
                continue

        paid_by_user = get_user(paid_by_name)
        if not paid_by_user:
            log_anomaly(i, raw, 'USER_NOT_FOUND', f'User "{paid_by_name}" not in database', 'skipped', 'Row skipped')
            skipped.append(i)
            continue

        # SPLIT TYPE
        split_type_raw = row.get('split_type', '').strip().lower()
        split_type_map = {
            'equal': 'equal', 'equally': 'equal',
            'unequal': 'unequal', 'exact': 'unequal',
            'percentage': 'percentage', 'percent': 'percentage',
            'share': 'share', 'shares': 'share',
        }
        split_type = split_type_map.get(split_type_raw, 'equal')
        if not split_type_raw:
            log_anomaly(i, raw, 'MISSING_SPLIT_TYPE', 'split_type is blank', 'auto_fixed', 'Defaulted to equal split')

        # SPLIT WITH
        split_with_raw = row.get('split_with', '').strip()
        split_members = []
        if split_with_raw:
            parts = [p.strip() for p in split_with_raw.replace(';', ',').split(',')]
            for p in parts:
                name = normalize_name(p) or fuzzy_match_name(p)
                if name:
                    u = get_user(name)
                    if u:
                        split_members.append(u)
                else:
                    log_anomaly(i, raw, 'UNKNOWN_MEMBER', f'"{p}" is not a known member', 'auto_fixed', f'Excluded "{p}" from split')

        if not split_members:
            memberships = GroupMembership.objects.filter(group=group, is_active=True)
            split_members = [m.user for m in memberships]

        # MEMBERSHIP DATE CHECKS
        final_members = []
        for member in split_members:
            uname = member.username.lower()
            if uname == 'meera' and parsed_date > MEERA_LEFT:
                log_anomaly(i, raw, 'MEMBER_AFTER_LEAVING',
                    f'Meera is in split but expense date {parsed_date} is after she left ({MEERA_LEFT})',
                    'auto_fixed', 'Removed Meera from split')
                continue
            if uname == 'sam' and parsed_date < SAM_JOINED:
                log_anomaly(i, raw, 'MEMBER_BEFORE_JOINING',
                    f'Sam is in split but expense date {parsed_date} is before he joined ({SAM_JOINED})',
                    'auto_fixed', 'Removed Sam from split')
                continue
            final_members.append(member)

        if not final_members:
            final_members = [paid_by_user]

        # PERCENTAGE VALIDATION
        split_details_raw = row.get('split_details', '').strip()
        split_details = {}
        if split_type == 'percentage' and split_details_raw:
            try:
                parts = [p.strip() for p in split_details_raw.split(',')]
                total_pct = Decimal('0')
                for p in parts:
                    name, pct = p.split(':')
                    total_pct += Decimal(pct.strip())
                    u = normalize_name(name) or fuzzy_match_name(name)
                    if u:
                        user = get_user(u)
                        if user:
                            split_details[str(user.id)] = pct.strip()
                if abs(total_pct - 100) > Decimal('0.01'):
                    log_anomaly(i, raw, 'PERCENT_SUM_INVALID',
                        f'Percentages sum to {total_pct}, not 100%',
                        'skipped', 'Row skipped - percentages must sum to 100')
                    skipped.append(i)
                    continue
            except Exception:
                split_type = 'equal'

        # DUPLICATE DETECTION
        dup_key = (str(parsed_date), description.lower().strip(), str(amount))
        if dup_key in seen_expenses:
            log_anomaly(i, raw, 'DUPLICATE',
                f'Possible duplicate of row {seen_expenses[dup_key]}: same date, description, amount',
                'requires_approval', 'Flagged for user review - skipped for now',
                requires_approval=True)
            skipped.append(i)
            continue
        seen_expenses[dup_key] = i

        fuzzy_key = (str(parsed_date), description.lower()[:15])
        if fuzzy_key in seen_expenses:
            log_anomaly(i, raw, 'FUZZY_DUPLICATE',
                f'Possible duplicate of row {seen_expenses[fuzzy_key]}: same date, similar description',
                'requires_approval', 'Flagged for review',
                requires_approval=True)
        seen_expenses[fuzzy_key] = i

        # CREATE EXPENSE
        expense = Expense.objects.create(
            group=group,
            description=description,
            amount=abs(amount),
            currency=currency,
            amount_inr=abs(amount_inr),
            paid_by=paid_by_user,
            date=parsed_date,
            split_type=split_type,
            notes=row.get('notes', ''),
            import_row=i
        )

        amt_inr = abs(amount_inr)
        if split_type == 'equal' and final_members:
            share = (amt_inr / len(final_members)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            remainder = amt_inr - (share * len(final_members))
            for idx, member in enumerate(final_members):
                owed = share + remainder if idx == 0 else share
                ExpenseSplit.objects.create(expense=expense, user=member, amount_owed=owed)
        elif split_type == 'percentage' and split_details:
            for uid, pct in split_details.items():
                user = User.objects.filter(id=int(uid)).first()
                if user:
                    owed = (amt_inr * Decimal(str(pct)) / 100).quantize(Decimal('0.01'))
                    ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=owed, percentage=Decimal(str(pct)))
        else:
            if final_members:
                share = (amt_inr / len(final_members)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                for member in final_members:
                    ExpenseSplit.objects.create(expense=expense, user=member, amount_owed=share)

        imported.append(i)

    session.status = 'completed'
    session.imported_rows = len(imported)
    session.skipped_rows = len(skipped)
    session.report = {
        'imported': imported,
        'skipped': skipped,
        'anomalies': anomalies
    }
    session.save()

    return Response({
        'session_id': session.id,
        'total_rows': len(rows),
        'imported': len(imported),
        'skipped': len(skipped),
        'anomaly_count': len(anomalies),
        'anomalies': anomalies
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def import_report(request, session_id):
    try:
        session = ImportSession.objects.get(id=session_id)
    except ImportSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    anomalies = ImportAnomaly.objects.filter(session=session)
    anomaly_data = [{
        'row': a.row_number,
        'type': a.anomaly_type,
        'description': a.description,
        'action': a.action_taken,
        'resolution': a.resolution,
        'requires_approval': a.requires_approval
    } for a in anomalies]

    return Response({
        'session_id': session.id,
        'filename': session.filename,
        'imported_at': session.imported_at,
        'status': session.status,
        'total_rows': session.total_rows,
        'imported_rows': session.imported_rows,
        'skipped_rows': session.skipped_rows,
        'anomalies': anomaly_data
    })