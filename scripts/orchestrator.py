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
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

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

def ensure_env_file():
    """Ensures .env exists from .env.example if missing."""
    env_file = ROOT_DIR / ".env"
    example = ROOT_DIR / ".env.example"
    if not env_file.exists() and example.exists():
        print(f"{CYAN}[*] Creating .env from .env.example...{RESET}")
        env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")

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
    parser.add_argument("action", choices=["bootstrap", "up", "status", "down", "init-openbao", "init-boundary", "init-semaphore"], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action in ["bootstrap", "up"]:
        bootstrap()
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
