import os
from .models import Project


NGINX_PATH = "/etc/nginx/autodeployr/"


def generate_nginx_config(project: Project, container_port: int):
    """
    Generate reverse proxy config per project
    """

    config = f"""
server {{
    listen 80;

    location /project/{project.id}/ {{

        proxy_pass http://127.0.0.1:{project.host_port};

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""

    file_path = os.path.join(NGINX_PATH, f"project_{project.id}.conf")

    with open(file_path, "w") as f:
        f.write(config)

    return file_path