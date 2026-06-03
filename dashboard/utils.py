import os
import re
import socket


def get_next_available_port(start_port=8001, end_port=9000):

    for port in range(start_port, end_port):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port

    raise Exception("No available ports found")


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