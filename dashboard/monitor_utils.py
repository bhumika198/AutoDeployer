import subprocess
import json
import os


# -----------------------------
# RUN SHELL COMMAND
# -----------------------------
def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


# -----------------------------
# CONTAINER CPU + RAM
# -----------------------------
def get_container_stats(container_name):
    """
    Uses docker stats (single snapshot)
    """

    cmd = [
        "docker", "stats",
        container_name,
        "--no-stream",
        "--format",
        "{{json .}}"
    ]

    out, err = run_cmd(cmd)

    if not out:
        return {
            "cpu": "0%",
            "memory": "0MB",
            "memory_percent": "0%"
        }

    try:
        data = json.loads(out)

        return {
            "cpu": data.get("CPUPerc", "0%"),
            "memory": data.get("MemUsage", "0").split("/")[0].strip(),
            "memory_percent": data.get("MemPerc", "0%")
        }

    except Exception:
        return {
            "cpu": "0%",
            "memory": "0MB",
            "memory_percent": "0%"
        }


# -----------------------------
# IMAGE SIZE
# -----------------------------
def get_image_size(image_name):
    cmd = [
        "docker", "images",
        image_name,
        "--format",
        "{{.Size}}"
    ]

    out, _ = run_cmd(cmd)

    return out if out else "Unknown"


# -----------------------------
# CONTAINER SIZE (RW layer)
# -----------------------------
def get_container_size(container_name):
    cmd = [
        "docker", "ps",
        "-s",
        "--filter",
        f"name={container_name}",
        "--format",
        "{{.Size}}"
    ]

    out, _ = run_cmd(cmd)

    return out if out else "Unknown"


# -----------------------------
# REPO SIZE
# -----------------------------
def get_repo_size(project_path):
    try:
        cmd = ["du", "-sh", project_path]
        out, _ = run_cmd(cmd)
        return out.split()[0] if out else "Unknown"
    except:
        return "Unknown"


# -----------------------------
# HEARTBEAT CHECK
# -----------------------------
def heartbeat_check(container_name):
    cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]

    out, _ = run_cmd(cmd)

    return out.strip() == "true"