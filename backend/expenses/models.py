from django.db import models
from users.models import User
from groups.models import Group


class Expense(models.Model):
    CURRENCY_CHOICES = [('INR', 'INR'), ('USD', 'USD')]
    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal'),
        ('unequal', 'Unequal'),
        ('percentage', 'Percentage'),
        ('share', 'Share'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    amount_inr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='expenses_paid')
    date = models.DateField()
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPE_CHOICES, default='equal')
    notes = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    import_row = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency}"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_splits')
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    shares = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} owes {self.amount_owed} for {self.expense.description}"


class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements_paid')
    paid_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paid_by.email} paid {self.paid_to.email} {self.amount}"