from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Project

class SignupForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project

        fields = [
            'name',
            'github_url',
            'branch',
            'container_port'
        ]