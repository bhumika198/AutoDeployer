from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):

    STATUS_CHOICES = [
        ('NOT_DEPLOYED', 'Not Deployed'),
        ('QUEUED', 'Queued'),
        ('DEPLOYING', 'Deploying'),
        ('RUNNING', 'Running'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=100
    )

    github_url = models.URLField()

    branch = models.CharField(
        max_length=100,
        default='main'
    )

    route_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    deployed_url = models.URLField(
        blank=True,
        null=True
    )

    host_port = models.IntegerField(
        blank=True,
        null=True
    )

    container_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    image_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    logs = models.TextField(
        blank=True,
        null=True
    )
    
    last_deployed_at = models.DateTimeField(
    null=True,
    blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NOT_DEPLOYED'
    )
    
    deployment_logs = models.TextField(
    blank=True,
    default=""
    )
 
    deployment_progress = models.IntegerField(
    default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name