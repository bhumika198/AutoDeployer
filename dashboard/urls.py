from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path(
        "signup/",
        views.signup_view,
        name="signup"
    ),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-project/', views.add_project, name='add_project'),
    path('deploy/<int:project_id>/', views.deploy_project, name='deploy_project'),
    path('deployment-status/<int:project_id>/',views.deployment_status,name='deployment_status'),
    path('delete-project/<int:project_id>/',views.delete_project,name='delete_project'),
    path('monitor/',views.monitor_dashboard,name='monitor_dashboard'),
    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp"
    ),
    path(
        'monitor-api/<int:project_id>/',
        views.project_monitor_api,
        name='project_monitor_api'
    ),
  
]