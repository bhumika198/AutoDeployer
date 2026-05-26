from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):

    STATUS_CHOICES = [
        ('NOT_DEPLOYED', 'Not Deployed'),
        ('DEPLOYING', 'Deploying'),
        ('RUNNING', 'Running'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=100)

    github_url = models.URLField()

    branch = models.CharField(
        max_length=100,
        default='main'
    )

    container_port = models.IntegerField(
        default=8000
    )

    deployed_url = models.URLField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NOT_DEPLOYED'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name