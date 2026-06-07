import os
import subprocess
import logging

logger = logging.getLogger(__name__)

NGINX_PATH = "/etc/nginx/conf.d"
NGINX_BIN="/usr/sbin/nginx"

def generate_nginx_config(project):
    """
    Generates nginx reverse proxy config for deployed project
    """

    server_name = f"{project.route_name}.161-118-187-130.sslip.io"

    config = f"""
server {{
    listen 80;
    server_name {server_name};

    location / {{
        proxy_pass http://127.0.0.1:{project.host_port};

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
""".strip()

    file_path = os.path.join(NGINX_PATH, f"{project.route_name}.conf")

    logger.info(f"[NGINX] Writing config: {file_path}")

    with open(file_path, "w") as f:
        f.write(config)

    return file_path


def test_nginx():
    """
    Validate nginx config before reload
    """

    logger.info("[NGINX] Testing configuration")

    result = subprocess.run(
        ["/usr/sbin/nginx", "-t"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"[NGINX ERROR] {result.stderr}")
        raise Exception(result.stderr)

    logger.info("[NGINX] Config valid")


def reload_nginx():
    """
    Reload nginx safely (zero downtime)
    """

    logger.info("[NGINX] Reloading nginx")

    result = subprocess.run(
        ["systemctl", "reload", "/usr/sbin/nginx"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"[NGINX RELOAD ERROR] {result.stderr}")
        raise Exception(result.stderr)

    logger.info("[NGINX] Reload successful")