from django.shortcuts import render, redirect
from .forms import SignupForm, ProjectForm
from django.contrib.auth.decorators import login_required
from .models import Project
import os
import subprocess
from django.shortcuts import get_object_or_404
from .utils import get_next_available_port
from .tasks import deploy_project_task
from .utils import get_next_available_port
from django.http import JsonResponse

from .monitor_utils import (
    get_container_stats,
    get_image_size,
    get_container_size,
    get_repo_size,
    heartbeat_check,
    get_container_uptime
)

from .monitor_utils import get_container_uptime

from .tasks import (
    deploy_project_task,
    delete_project_task
)

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):

    projects = Project.objects.filter(
        user=request.user
    ).exclude(
    status="DELETING"
        )

    return render(
        request,
        'dashboard.html',
        {'projects': projects}
    )

def signup_view(request):

    if request.method == 'POST':

        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')

    else:
        form = SignupForm()

    return render(request, 'signup.html', {'form': form})

@login_required
def add_project(request):
    print("VIEW CALLED")

    if request.method == 'POST':
        print("POST RECEIVED:", request.POST)
        form = ProjectForm(request.POST)

        if form.is_valid():

            project = form.save(commit=False)

            project.user = request.user

            project.host_port = get_next_available_port()

            project.save()

            return redirect('dashboard')

    else:
        form = ProjectForm()

    return render(
        request,
        'add_project.html',
        {'form': form}
    )

@login_required
def deploy_project(request, project_id):

    project = get_object_or_404(Project, id=project_id, user=request.user)
    project.deployment_logs = ""
    project.deployment_progress = 0
    project.logs = ""
    project.save()  
    deploy_project_task.delay(project.id)

    project.status = "QUEUED"
    project.deployment_progress = 0
    project.deployment_logs = ""
    project.save()
    

    return redirect("dashboard")

@login_required
def deployment_status(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id,
        user=request.user
    )

    return JsonResponse({
        "status": project.status,
        "progress": project.deployment_progress,
        "logs": project.deployment_logs,
        "url": project.deployed_url,
    })

@login_required
def delete_project(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id,
        user=request.user
    )

    project.status = "DELETING"
    project.save()

    delete_project_task.delay(project.id)

    return JsonResponse({
        "status": "ok",
        "project_id": project.id
    })



@login_required
def monitor_dashboard(request):

    projects = Project.objects.filter(
        user=request.user
    ).exclude(
        status="DELETING"
    )

    # Add extra monitoring fields
    for project in projects:

        # Deployment timestamp
        project.deployment_timestamp = (
            project.created_at.strftime("%d %b %Y %I:%M %p")
            if project.created_at else "N/A"
        )

        # Container uptime
        if project.container_name:
            project.container_uptime = get_container_uptime(
                project.container_name
            )
        else:
            project.container_uptime = "N/A"

    context = {
        "projects": projects,
        "total_projects": projects.count(),
        "running_projects": projects.filter(
            status="RUNNING"
        ).count(),
        "failed_projects": projects.filter(
            status="FAILED"
        ).count(),
        "deploying_projects": projects.filter(
            status__in=["DEPLOYING", "QUEUED"]
        ).count(),
    }

    return render(
        request,
        "monitor_dashboard.html",
        context
    )

from .monitor_utils import *

@login_required
def project_monitor_api(request, project_id):

    project = get_object_or_404(
        Project,
        id=project_id,
        user=request.user
    )

    base_path = (
        f"/root/Documents/AutoDeployer/deployments/project_{project.id}"
    )

    stats = {}

    if project.container_name:

        stats = get_container_stats(
            project.container_name
        )

    return JsonResponse({

        "name": project.name,
        "status": project.status,

        "cpu": stats.get(
            "cpu",
            "0%"
        ),

        "memory": stats.get(
            "memory",
            "0MB"
        ),

        "memory_percent": stats.get(
            "memory_percent",
            "0%"
        ),

        "repo_size": get_repo_size(base_path),

        "image_size":
            get_image_size(project.image_name)
            if project.image_name
            else "N/A",

        "container_size":
            get_container_size(project.container_name)
            if project.container_name
            else "N/A",

        "heartbeat":
            heartbeat_check(project.container_name)
            if project.container_name
            else False

    })
