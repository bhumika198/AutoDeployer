import os
import re
import socket


from .models import Project


def get_next_available_port():

    START_PORT = 8100

    used_ports = set(
        Project.objects.exclude(
            host_port__isnull=True
        ).values_list(
            "host_port",
            flat=True
        )
    )

    port = START_PORT

    while port in used_ports:
        port += 1

    return port


def detect_container_ports(project_path):

    dockerfile_path = os.path.join(project_path, "Dockerfile")

    framework = "unknown"
    primary_port = 8000
    secondary_ports = []

    if os.path.exists(dockerfile_path):

        with open(dockerfile_path, "r") as f:
            content = f.read()

        expose_ports = re.findall(
            r"EXPOSE\s+(\d+)",
            content,
            re.IGNORECASE
        )

        if expose_ports:

            primary_port = int(expose_ports[0])

            if len(expose_ports) > 1:
                secondary_ports = [
                    int(p) for p in expose_ports[1:]
                ]

            return {
                "framework": "dockerfile-expose",
                "primary_port": primary_port,
                "secondary_ports": secondary_ports,
            }

    # Laravel / PHP

    if os.path.exists(os.path.join(project_path, "artisan")):

        framework = "laravel"

        return {
            "framework": framework,
            "primary_port": 8000,
            "secondary_ports": [80]
        }

    # Django

    if os.path.exists(os.path.join(project_path, "manage.py")):

        framework = "django"

        return {
            "framework": framework,
            "primary_port": 8000,
            "secondary_ports": []
        }

    # Node

    if os.path.exists(os.path.join(project_path, "package.json")):

        framework = "nodejs"

        return {
            "framework": framework,
            "primary_port": 3000,
            "secondary_ports": []
        }

    # Static nginx

    if os.path.exists(os.path.join(project_path, "nginx.conf")):

        framework = "nginx"

        return {
            "framework": framework,
            "primary_port": 80,
            "secondary_ports": []
        }

    return {
        "framework": framework,
        "primary_port": 8000,
        "secondary_ports": []
    }