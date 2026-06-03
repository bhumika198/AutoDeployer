import os
import re
import socket


def get_next_available_port(start_port=8001, end_port=9000):

    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port

    raise Exception("No available ports found")


def detect_container_port(project_path):

    dockerfile_path = os.path.join(project_path, "Dockerfile")

    if os.path.exists(dockerfile_path):

        with open(dockerfile_path, "r") as f:
            content = f.read()

        expose_match = re.findall(
            r"EXPOSE\s+(\d+)",
            content,
            re.IGNORECASE
        )

        if expose_match:
            return int(expose_match[-1])

    # Nginx static site
    if os.path.exists(os.path.join(project_path, "nginx.conf")):
        return 80

    # Laravel / PHP
    if os.path.exists(os.path.join(project_path, "artisan")):
        return 8000

    # Django
    if os.path.exists(os.path.join(project_path, "manage.py")):
        return 8000

    # Node
    if os.path.exists(os.path.join(project_path, "package.json")):
        return 3000

    # Fallback
    return 8000
    