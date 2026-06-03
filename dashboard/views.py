from django.shortcuts import render, redirect
from .forms import SignupForm, ProjectForm
from django.contrib.auth.decorators import login_required
from .models import Project
import os
import subprocess
from django.shortcuts import get_object_or_404
from .utils import get_next_available_port

def home(request):
    return render(request, 'home.html')

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
def dashboard(request):

    projects = Project.objects.filter(
        user=request.user
    )

    return render(
        request,
        'dashboard.html',
        {'projects': projects}
    )

@login_required
def add_project(request):

    if request.method == 'POST':

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

from .tasks import deploy_project_task
from .utils import get_next_available_port


@login_required
def deploy_project(request, project_id):

    project = get_object_or_404(Project, id=project_id, user=request.user)

    deploy_project_task.delay(project.id)

    project.status = "QUEUED"
    project.save()

    return redirect("dashboard")