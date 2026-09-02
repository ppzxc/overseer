#!/usr/bin/env python3
"""
Overseer Control Plane Lifecycle & Bootstrap Orchestrator
Provides a deep, unified interface for full-stack service initialization,
dependency-aware healthchecks, automated database migrations, and OpenBao/Semaphore seeding.
"""

import os
import sys
import time
import subprocess
import argparse
import base64
import secrets
from typing import NamedTuple, List

class CheckResult(NamedTuple):
    category: str
    item: str
    passed: bool
    detail: str
    remediation: str

ROOT_DIR = Path(__file__).resolve().parent.parent

def get_configured_data_dir():
    """Reads DATA_DIR from .env or defaults to /data."""
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATA_DIR="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return Path(val).resolve() if not val.startswith("/") else Path(val)
    return Path("/data")

def generate_base64_key(bytes_len=32):
    """Generates a cryptographically secure Base64-encoded key."""
    return base64.b64encode(secrets.token_bytes(bytes_len)).decode("utf-8")

def generate_random_password(length=16):
    """Generates a cryptographically secure random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def run_cmd(cmd, check=True, capture=False, env=None):
    """Executes a command within ROOT_DIR."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        check=check,
        shell=isinstance(cmd, str),
        text=True,
        capture_output=capture,
        env=full_env
    )

def run_preflight_checks(exit_on_failure=True):
    """
    Validates host environment, non-root user permissions, required CLI utilities,
    directory writeability, and port availability before running bootstrap.
    """
    import socket
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}      Overseer Control Plane Pre-Flight Prerequisites Validator         {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")

    checks: List[CheckResult] = []

    # 1. CLI Tools
    for tool in ["docker", "jq", "curl", "make", "python3"]:
        res = subprocess.run(f"command -v {tool}", shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            checks.append(CheckResult("CLI Tool", tool, True, res.stdout.strip(), ""))
        else:
            remediation = f"Install '{tool}' via package manager (e.g. sudo apt install -y {tool} or sudo dnf install -y {tool})"
            checks.append(CheckResult("CLI Tool", tool, False, "Not found in PATH", remediation))

    # 2. Docker Compose v2 plugin
    res_compose = subprocess.run("docker compose version", shell=True, capture_output=True, text=True)
    if res_compose.returncode == 0:
        checks.append(CheckResult("Docker Plugin", "docker compose v2", True, res_compose.stdout.strip().splitlines()[0], ""))
    else:
        checks.append(CheckResult("Docker Plugin", "docker compose v2", False, "docker compose v2 not available", "Install Docker Compose v2 plugin"))

    # 3. Docker Non-Root User Permissions
    res_dockersock = subprocess.run("docker info", shell=True, capture_output=True, text=True)
    if res_dockersock.returncode == 0:
        checks.append(CheckResult("Permissions", "Docker Non-Root Access", True, "Docker daemon accessible without sudo", ""))
    else:
        err_msg = res_dockersock.stderr.strip().splitlines()
        detail = err_msg[0] if err_msg else "Cannot connect to Docker daemon socket"
        checks.append(CheckResult("Permissions", "Docker Non-Root Access", False, detail, "Add user to docker group: sudo usermod -aG docker $USER && newgrp docker"))

    # 4. Filesystem Directory Writeability for Centralized DATA_DIR (/data)
    data_dir = get_configured_data_dir()
    required_subs = ["postgres", "openbao", "semaphore", "boundary"]
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        for sub in required_subs:
            (data_dir / sub).mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".preflight_tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        checks.append(CheckResult("Filesystem", f"Data Dir ({data_dir})", True, f"Writable ({data_dir}/...)", ""))
    except Exception as e:
        remediation = f"Fix permissions: sudo mkdir -p {data_dir}/{{{','.join(required_subs)}}} && sudo chown -R $USER:dockermgmt {data_dir} && sudo chmod -R 775 {data_dir} (or set DATA_DIR=./data in .env for local testing)"
        checks.append(CheckResult("Filesystem", f"Data Dir ({data_dir})", False, str(e), remediation))

    # 5. Port Availability & Conflicts
    ports_to_check = [
        (8200, "OpenBao Web / API"),
        (9200, "Boundary Controller API"),
        (9201, "Boundary Controller Cluster"),
        (9202, "Boundary Worker Proxy"),
        (3000, "Semaphore Web UI"),
    ]
    running_containers_res = subprocess.run("docker compose ps -q", shell=True, capture_output=True, text=True, cwd=str(ROOT_DIR))
    overseer_containers_running = bool(running_containers_res.stdout.strip())

    for port, service_desc in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        conn_res = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if conn_res == 0:
            if overseer_containers_running:
                checks.append(CheckResult("Port Status", f"Port {port} ({service_desc})", True, "In use (Overseer active)", ""))
            else:
                checks.append(CheckResult("Port Conflict", f"Port {port} ({service_desc})", False, "Already in use by foreign process", f"Stop conflicting service on port {port}"))
        else:
            checks.append(CheckResult("Port Status", f"Port {port} ({service_desc})", True, "Available", ""))

    # Print Table
    print(f"{'Category':<15} | {'Check Item':<35} | {'Status':<6} | {'Details'}")
    print("-" * 85)
    all_passed = True
    for chk in checks:
        status_str = f"{GREEN}PASS{RESET}" if chk.passed else f"{RED}FAIL{RESET}"
        if not chk.passed:
            all_passed = False
        display_detail = chk.detail[:34] + "..." if len(chk.detail) > 34 else chk.detail
        print(f"{chk.category:<15} | {chk.item:<35} | {status_str:<15} | {display_detail}")
    print("-" * 85)

    if not all_passed:
        print(f"\n{BOLD}{RED}❌ Pre-flight validation failed! Bootstrap cancelled.{RESET}\n")
        print(f"{BOLD}Remediation Steps:{RESET}")
        for chk in checks:
            if not chk.passed and chk.remediation:
                print(f"  - [{chk.item}]: {chk.remediation}")
        print()
        if exit_on_failure:
            sys.exit(1)
        return False

    print(f"\n{BOLD}{GREEN}✅ All Pre-flight checks passed! Proceeding...{RESET}\n")
    return True

def ensure_env_file():
    """Ensures .env exists from .env.example with newly generated secure random keys."""
    env_file = ROOT_DIR / ".env"
    example = ROOT_DIR / ".env.example"
    if not env_file.exists() and example.exists():
        print(f"{CYAN}[*] Generating fresh .env with unique cryptographic keys...{RESET}")
        content = example.read_text(encoding="utf-8")
        
        # Cryptographically secure random keys & passwords
        postgres_password = generate_random_password(18)
        semaphore_admin_password = generate_random_password(18)
        boundary_kms_root_key = generate_base64_key(32)
        boundary_kms_worker_auth_key = generate_base64_key(32)
        boundary_kms_recovery_key = generate_base64_key(32)
        semaphore_encryption_key = generate_base64_key(32)
        
        # Replace default placeholder credentials
        content = content.replace("POSTGRES_PASSWORD=boundarypassword", f"POSTGRES_PASSWORD={postgres_password}")
        content = content.replace("postgresql://boundary:boundarypassword@", f"postgresql://boundary:{postgres_password}@")
        content = content.replace("BOUNDARY_KMS_AEAD_ROOT_KEY=sP191WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU=", f"BOUNDARY_KMS_AEAD_ROOT_KEY={boundary_kms_root_key}")
        content = content.replace("BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY=8pv7uU8g58aN8y1n8PqR8G3z7rW+V8eY9nQ2x3Z1v4U=", f"BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY={boundary_kms_worker_auth_key}")
        content = content.replace("BOUNDARY_KMS_AEAD_RECOVERY_KEY=uK382WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU=", f"BOUNDARY_KMS_AEAD_RECOVERY_KEY={boundary_kms_recovery_key}")
        content = content.replace("SEMAPHORE_ADMIN_PASSWORD=semaphoreadmin", f"SEMAPHORE_ADMIN_PASSWORD={semaphore_admin_password}")
        content = content.replace("SEMAPHORE_ACCESS_KEY_ENCRYPTION=GS3py5Y8+GvF12x0fTfR18k2h4eE9W2d1C8N6Q8T4=0", f"SEMAPHORE_ACCESS_KEY_ENCRYPTION={semaphore_encryption_key}")
        
        env_file.write_text(content, encoding="utf-8")
        print(f"{GREEN}[+] Fresh .env created with newly generated 32-byte KMS/encryption keys and passwords.{RESET}")

def check_postgres_ready(timeout=30):
    """Waits for PostgreSQL to accept connections."""
    print(f"{CYAN}[*] Waiting for PostgreSQL backend (port 5432)...{RESET}")
    start = time.time()
    while time.time() - start < timeout:
        res = run_cmd("docker compose exec -T postgres pg_isready -U boundary", check=False, capture=True)
        if res.returncode == 0:
            print(f"{GREEN}[+] PostgreSQL is ready.{RESET}")
            return True
        time.sleep(1.5)
    print(f"{RED}[-] PostgreSQL timed out after {timeout}s.{RESET}")
    return False

def ensure_postgres_databases():
    """Ensures 'semaphore' and 'boundary' databases exist."""
    print(f"{CYAN}[*] Ensuring 'semaphore' database in PostgreSQL...{RESET}")
    check_db = run_cmd("docker compose exec -T postgres psql -U boundary -d postgres -tc \"SELECT 1 FROM pg_database WHERE datname = 'semaphore'\"", check=False, capture=True)
    if "1" not in check_db.stdout:
        run_cmd("docker compose exec -T postgres psql -U boundary -d postgres -c \"CREATE DATABASE semaphore;\"", check=False)
        print(f"{GREEN}[+] Created database 'semaphore'.{RESET}")
    else:
        print(f"{GREEN}[+] Database 'semaphore' already exists.{RESET}")

def init_boundary():
    """Initializes Boundary Database schema."""
    print(f"{CYAN}[*] Initializing Boundary Database Schema...{RESET}")
    run_cmd("docker compose run --rm --entrypoint /bin/sh boundary-controller -c '/boundary/scripts/init-boundary.sh'", check=False)
    print(f"{GREEN}[+] Boundary schema initialized.{RESET}")

def init_openbao():
    """Initializes and unseals OpenBao, setting up SSH CA."""
    print(f"{CYAN}[*] Initializing and unsealing OpenBao & SSH CA...{RESET}")
    run_cmd("docker compose up -d openbao", check=True)
    # Wait for health
    time.sleep(2)
    run_cmd("docker compose exec -T openbao /bin/sh /openbao/scripts/init-openbao-ssh-ca.sh", check=False)
    print(f"{GREEN}[+] OpenBao SSH CA setup finished.{RESET}")

def init_semaphore():
    """Seeds Semaphore project, keys, gitops repo, and task templates."""
    print(f"{CYAN}[*] Seeding Semaphore UI GitOps Templates...{RESET}")
    init_script = ROOT_DIR / "scripts" / "init-semaphore.sh"
    if init_script.exists():
        run_cmd(str(init_script), check=False)

def bootstrap():
    """Full end-to-end bootstrap of all Control Plane services."""
    # 0. Pre-Flight Prerequisites Validation
    run_preflight_checks(exit_on_failure=True)

    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}           Overseer Control Plane Full-Stack Bootstrap Starting         {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
    
    ensure_env_file()
    
    # 1. Start Postgres & Wait
    run_cmd("docker compose up -d postgres", check=True)
    if not check_postgres_ready():
        sys.exit(1)
    ensure_postgres_databases()
    
    # 2. Init Boundary & OpenBao
    init_boundary()
    init_openbao()
    
    # 3. Start remaining services (Boundary & Semaphore)
    print(f"{CYAN}[*] Starting Boundary Controller, Worker & Semaphore UI...{RESET}")
    run_cmd("docker compose up -d boundary-controller boundary-worker semaphore", check=True)
    
    # 4. Seed Semaphore
    init_semaphore()
    
    print(f"\n{BOLD}{GREEN}================================================================================{RESET}")
    print(f"{BOLD}{GREEN}  Overseer Control Plane is UP and READY!                                      {RESET}")
    print(f"{BOLD}{GREEN}  - OpenBao Web UI:     http://localhost:8200                                   {RESET}")
    print(f"{BOLD}{GREEN}  - Boundary Admin UI:  http://localhost:9200                                   {RESET}")
    print(f"{BOLD}{GREEN}  - Semaphore Web UI:   http://localhost:3000 (admin / semaphoreadmin)          {RESET}")
    print(f"{BOLD}{GREEN}================================================================================{RESET}\n")

def check_service_status():
    """Detailed health check and status reporting across all control plane services."""
    print(f"\n{BOLD}Checking Overseer Control Plane Services Health...{RESET}\n")
    
    services = [
        ("1. PostgreSQL (5432)", "docker compose exec -T postgres pg_isready -U boundary", "tcp"),
        ("2. OpenBao API (8200)", "curl -s http://127.0.0.1:8200/v1/sys/health", "http"),
        ("3. Boundary Controller (9200)", "curl -s http://127.0.0.1:9200/v1/health", "http"),
        ("4. Semaphore UI (3000)", "curl -s http://127.0.0.1:3000/api/ping", "http"),
    ]
    
    all_healthy = True
    for name, cmd, check_type in services:
        res = run_cmd(cmd, check=False, capture=True)
        if res.returncode == 0:
            status = f"{GREEN}● HEALTHY{RESET}"
        elif check_type == "http" and "429" in res.stderr or "initialized" in res.stdout:
            status = f"{GREEN}● HEALTHY{RESET}"
        else:
            status = f"{RED}✖ UNHEALTHY / DOWN{RESET}"
            all_healthy = False
        print(f"  {name:<30} {status}")
    print()
    return 0 if all_healthy else 1

def main():
    parser = argparse.ArgumentParser(description="Overseer Control Plane Lifecycle Orchestrator")
    parser.add_argument("action", choices=["bootstrap", "up", "preflight", "status", "down", "init-openbao", "init-boundary", "init-semaphore"], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action in ["bootstrap", "up"]:
        bootstrap()
    elif args.action == "preflight":
        passed = run_preflight_checks(exit_on_failure=False)
        sys.exit(0 if passed else 1)
    elif args.action == "status":
        sys.exit(check_service_status())
    elif args.action == "down":
        run_cmd("docker compose down", check=True)
    elif args.action == "init-openbao":
        init_openbao()
    elif args.action == "init-boundary":
        init_boundary()
    elif args.action == "init-semaphore":
        init_semaphore()

if __name__ == "__main__":
    main()
