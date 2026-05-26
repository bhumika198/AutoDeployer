from django.shortcuts import render, redirect
from .forms import SignupForm, ProjectForm
from django.contrib.auth.decorators import login_required
from .models import Project


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

            project.save()

            return redirect('dashboard')

    else:
        form = ProjectForm()

    return render(
        request,
        'add_project.html',
        {'form': form}
    )