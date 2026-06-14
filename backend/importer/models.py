from django.db import models
from users.models import User


class ImportSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    filename = models.CharField(max_length=255)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    report = models.JSONField(default=dict)

    def __str__(self):
        return f"Import {self.filename} - {self.status}"


class ImportAnomaly(models.Model):
    ACTION_CHOICES = [
        ('auto_fixed', 'Auto Fixed'),
        ('skipped', 'Skipped'),
        ('requires_approval', 'Requires Approval'),
        ('rejected', 'Rejected'),
    ]
    session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name='anomalies')
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    anomaly_type = models.CharField(max_length=50)
    description = models.TextField()
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resolution = models.TextField(blank=True, null=True)
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Row {self.row_number} - {self.anomaly_type}"