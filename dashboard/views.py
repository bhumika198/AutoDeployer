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
import random

from django.core.mail import send_mail

from .models import EmailOTP

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
    show_otp_modal = False
    if request.method == 'POST':

        form = SignupForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]

            request.session["register_data"] = {
                "email": email,
                "username": username,
                "password": password,
            }
            User = get_user_model()

            if User.objects.filter(email=email).exists():

                form.add_error(
                    "email",
                    "An account with this email already exists."
                )

                return render(
                    request,
                    "signup.html",
                    {
                        "form": form
                    }
                )
            send_otp(email)

            show_otp_modal = True

    else:
        form = SignupForm()

    return render(
        request,
        "signup.html",
        {
            "form": form,
            "show_otp_modal": show_otp_modal
        }
    )          

from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

def verify_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get("otp")

        data = request.session.get("register_data")

        if not data:

            messages.error(
                request,
                "Session expired. Please register again."
            )

            return redirect("signup")

        email = data["email"]

        otp_record = EmailOTP.objects.filter(
            email=email,
            otp=entered_otp
        ).first()

        if otp_record:

            User.objects.create_user(
                username=data["username"],
                email=email,
                password=data["password"]
            )

            otp_record.delete()

            request.session.pop(
                "register_data",
                None
            )

            messages.success(
                request,
                "Registration successful."
            )

            return redirect("login")

        messages.error(
            request,
            "Invalid OTP"
        )

        return redirect("signup")

    return redirect("signup")
    

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

def send_otp(email):

    otp = str(random.randint(100000, 999999))

    EmailOTP.objects.update_or_create(
        email=email,
        defaults={
            "otp": otp
        }
    )

    send_mail(
        subject="AutoDeployr Email Verification",
        message=f"Your OTP is {otp}",
        from_email=None,
        recipient_list=[email]
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
