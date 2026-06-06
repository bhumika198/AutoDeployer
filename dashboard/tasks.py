import os
import shutil
import subprocess
import logging

from celery import shared_task
from django.utils.text import slugify

from .models import Project
from .utils import detect_container_ports, get_next_available_port

from .nginx_utils import (
    generate_nginx_config,
    test_nginx,
    reload_nginx
)

logger = logging.getLogger(__name__)

def update_deployment(project, message, progress=None):

    logger.info(message)

    project.deployment_logs += f"{message}\n"

    if progress is not None:
        project.deployment_progress = progress

    project.save()


@shared_task
def deploy_project_task(project_id):

    logger.info(f"[DEPLOY START] Project ID: {project_id}")

    project = Project.objects.get(id=project_id)

    # -----------------------------
    # PREVENT DOUBLE DEPLOYMENT
    # -----------------------------
    if project.status == "DEPLOYING":
        logger.warning(f"[SKIP] Project {project.id} already deploying")
        return

    try:
        # -----------------------------
        # MARK QUEUED -> DEPLOYING
        # -----------------------------
        logger.info(f"[STATUS UPDATE] QUEUED → DEPLOYING (Project {project.id})")
        project.status = "DEPLOYING"
        project.deployment_logs = ""
        project.deployment_progress = 0
        project.logs = ""
        project.save()

        update_deployment(
            project,
            "[STATUS] Deployment Started",
            5
        )

        # -----------------------------
        # SETUP PATHS
        # -----------------------------
        base_path = "/root/Documents/AutoDeployer/deployments"
        project_path = os.path.join(base_path, f"project_{project.id}")

        logger.info(f"[PATH] Deployment folder: {project_path}")

        if os.path.exists(project_path):
            logger.info(f"[CLEANUP] Removing old deployment for Project {project.id}")
            shutil.rmtree(project_path)

        # -----------------------------
        # CLONE REPOSITORY
        # -----------------------------
        logger.info(f"[GIT] Cloning repo: {project.github_url} (branch: {project.branch})")

        clone_result = subprocess.run(
            [
                "/usr/bin/git",
                "clone",
                "-b",
                project.branch,
                project.github_url,
                project_path
            ],
            capture_output=True,
            text=True
        )

        if clone_result.returncode != 0:
            logger.error(f"[GIT ERROR] {clone_result.stderr}")
            project.status = "FAILED"
            project.logs = clone_result.stderr
            project.deployment_logs += (
                "\n[GIT ERROR]\n" +
                clone_result.stderr
            )
            project.save()
            return

        logger.info("[GIT] Clone successful")

        update_deployment(
            project,
            "[GIT] Repository cloned successfully",
            20
        )

        # -----------------------------
        # DETECT CONTAINER PORTS
        # -----------------------------
        port_info = detect_container_ports(project_path)

        framework = port_info["framework"]
        container_port = port_info["primary_port"]

        logger.info(f"[DETECT] Framework: {framework}")
        logger.info(f"[DETECT] Container Port: {container_port}")
        logger.info(f"[DETECT] Secondary Ports: {port_info['secondary_ports']}")
        update_deployment(
            project,
            f"[DETECT] Container Port: {container_port}",
            30
        )
        # -----------------------------
        # GENERATE ROUTE NAME
        # -----------------------------
        base_route = slugify(project.name)
        project.route_name = f"{base_route}-{project.id}"

        logger.info(f"[ROUTE] Generated route_name: {project.route_name}")

        # -----------------------------
        # ASSIGN HOST PORT
        # -----------------------------

        project.host_port = get_next_available_port()

        logger.info(
                    f"[PORT] Assigned host port: {project.host_port}"
            )
        logger.info(f"[PORT] Assigned new host port: {project.host_port}")
        
    
        project.save()

        logger.info(
            f"[PORT MAP] host_port={project.host_port} → container_port={container_port}"
        )

        # -----------------------------
        # BUILD DOCKER IMAGE
        # -----------------------------      

        image_name = f"project_{project.id}"
        container_name = f"container_{project.id}"

        logger.info(f"[DOCKER] Building image: {image_name}")
        update_deployment(
            project,
            "[DOCKER] Building image",
            40
        )
        build_result = subprocess.run(
            ["docker", "build", "-t", image_name, project_path],
            capture_output=True,
            text=True
        )

        # Combine both outputs (VERY IMPORTANT for docker)
        logs = (build_result.stdout or "") + "\n" + (build_result.stderr or "")

        if build_result.returncode != 0:
            logger.error("[DOCKER BUILD FAILED]")
            logger.error(logs)

            project.status = "FAILED"
            project.logs = logs[-8000:]  # avoid DB overflow

            project.deployment_logs += (
                "\n[DOCKER BUILD FAILED]\n" +
                logs[-8000:]
            )
            project.save()

            raise Exception(f"Docker build failed:\n{logs}")

        logger.info("[DOCKER] Image build successful")
        update_deployment(
            project,
            "[DOCKER] Image build successful",
            60
        )

        logger.debug(logs)

        # -----------------------------
        # STOP OLD CONTAINER (IF ANY)
        # -----------------------------
        logger.info(f"[DOCKER] Stopping old container if exists: {container_name}")

        subprocess.run(["docker", "stop", container_name], capture_output=True)
        subprocess.run(["docker", "rm", container_name], capture_output=True)

        # -----------------------------
        # RUN NEW CONTAINER
        # -----------------------------
        logger.info("[DOCKER] Starting container")

        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{project.host_port}:{container_port}",
            image_name
        ]

        logger.info(f"[DOCKER RUN] {' '.join(run_cmd)}")

        run_result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True
        )

        if run_result.returncode != 0:
            logger.error(f"[DOCKER RUN ERROR] {run_result.stderr}")
            project.status = "FAILED"
            project.logs = run_result.stderr
            project.save()
            return

        logger.info(f"[DOCKER] Container started: {container_name}")
        update_deployment(
            project,
            "[DOCKER] Container started",
            80
        )
        
        # -----------------------------
        # MARK SUCCESS
        # -----------------------------
        project.status = "RUNNING"
        project.image_name = image_name
        project.container_name = container_name

        # -----------------------------
        # BUILD DEPLOYMENT URL (for future nginx)
        # -----------------------------
        project.deployed_url = (
                f"http://{project.route_name}.161-118-187-130.sslip.io"
            )

        project.save()

        logger.info(f"[SUCCESS] Deployment completed for Project {project.id}")
        logger.info(f"[URL] {project.deployed_url}")

        # -----------------------------
        # NGINX ROUTING SETUP
        # -----------------------------
        update_deployment(
            project,
            "[NGINX] Configuring routing",
            90
        )
        logger.info("[NGINX] Generating reverse proxy config")

        try:
            config_path = generate_nginx_config(project)
            logger.info(f"[NGINX] Config created at {config_path}")

            test_nginx()

            reload_nginx()

            logger.info("[NGINX] Routing activated successfully")
            update_deployment(
                project,
                "[SUCCESS] Deployment completed",
                100
            )

        except Exception as e:
            logger.error(f"[NGINX ERROR] {str(e)}")
            project.logs = f"{project.logs}\nNGINX ERROR: {str(e)}"
            project.save()

    except Exception as e:
        logger.error(f"[EXCEPTION] {str(e)}")
        project.status = "FAILED"
        project.logs = str(e)
        project.save()