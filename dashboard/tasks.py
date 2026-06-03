import os
import shutil
import subprocess
import logging

from celery import shared_task
from .models import Project
from .utils import detect_container_ports


logger = logging.getLogger(__name__)

def get_next_available_port(start=8001, end=9000):
    """
    Simple port allocator for host machine
    """

    used_ports = set(
        Project.objects.exclude(host_port=None).values_list("host_port", flat=True)
    )

    for port in range(start, end):
        if port not in used_ports:
            return port

    raise Exception("NO FREE PORTS AVAILABLE")

import os
import shutil
import subprocess
import logging

from celery import shared_task
from .models import Project
from .utils import detect_container_ports
from .utils import get_next_available_port

logger = logging.getLogger(__name__)


@shared_task
def deploy_project_task(project_id):

    project = Project.objects.get(id=project_id)

    try:
        logger.info(f"CELERY STARTED FOR PROJECT {project.id}")
        logger.info(f"PROJECT FOUND: {project.name}")

        project.status = "DEPLOYING"
        project.save()

        base_path = "/root/Documents/AutoDeployer/deployments"
        project_path = os.path.join(base_path, f"project_{project.id}")

        logger.info(f"PROJECT PATH: {project_path}")

        if os.path.exists(project_path):
            logger.info("REMOVING OLD PROJECT")
            shutil.rmtree(project_path)

        # -------------------------
        # CLONE
        # -------------------------
        logger.info("CLONING REPOSITORY")

        clone_result = subprocess.run(
            ["git", "clone", "-b", project.branch, project.github_url, project_path],
            capture_output=True,
            text=True
        )

        if clone_result.returncode != 0:
            project.status = "FAILED"
            project.logs = clone_result.stderr
            project.save()
            return

        logger.info("CLONE SUCCESS")

        # -------------------------
        # DETECT PORTS
        # -------------------------
        port_info = detect_container_ports(project_path)

        logger.info(f"FRAMEWORK DETECTED: {port_info['framework']}")
        logger.info(f"PRIMARY PORT: {port_info['primary_port']}")
        logger.info(f"SECONDARY PORTS: {port_info['secondary_ports']}")

        # -------------------------
        # BUILD IMAGE
        # -------------------------
        image_name = f"project_{project.id}"
        container_name = f"container_{project.id}"

        logger.info(f"IMAGE: {image_name}")
        logger.info(f"CONTAINER: {container_name}")

        build_result = subprocess.run(
            ["docker", "build", "-t", image_name, project_path],
            capture_output=True,
            text=True
        )

        if build_result.returncode != 0:
            project.status = "FAILED"
            project.logs = build_result.stderr
            project.save()
            return

        logger.info("BUILD SUCCESS")

        # -------------------------
        # STOP OLD CONTAINER
        # -------------------------
        subprocess.run(["docker", "stop", container_name], capture_output=True)
        subprocess.run(["docker", "rm", container_name], capture_output=True)

        # -------------------------
        # RUN CONTAINER
        # -------------------------
        primary_port = port_info["primary_port"]

        

        if not project.host_port:

            project.host_port = get_next_available_port()

            project.save()

        logger.info(f"HOST PORT: {project.host_port}")
        logger.info(f"CONTAINER PORT: {primary_port}")
        
        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{project.host_port}:{primary_port}",
            image_name
        ]

        logger.info(f"RUN COMMAND: {' '.join(run_cmd)}")

        run_result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True
        )

        if run_result.returncode != 0:
            logger.error(run_result.stderr)
            project.status = "FAILED"
            project.logs = run_result.stderr
            project.save()
            return

        logger.info("CONTAINER STARTED")
        project.status = "RUNNING"
        project.save()

        logger.info("DEPLOYMENT COMPLETE")

    except Exception as e:
        logger.error(str(e))
        project.status = "FAILED"
        project.logs = str(e)
        project.save()