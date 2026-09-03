#!/usr/bin/env python3
"""
Overseer Control Plane Lifecycle & Bootstrap Orchestrator
Provides a deep, unified interface for full-stack service initialization,
dependency-aware healthchecks, automated database migrations, pluggable SEAL/UNSEAL profiles,
port exposure branching, external network bootstrapping, and manual/auto key management.
"""

import os
import sys
import time
import shutil
import subprocess
import argparse
import base64
import secrets
import string
from pathlib import Path
from typing import NamedTuple, List

class CheckResult(NamedTuple):
    category: str
    item: str
    passed: bool
    detail: str
    remediation: str

ROOT_DIR = Path(__file__).resolve().parent.parent

def read_env_file(include_comments: bool = False) -> dict:
    """Parses .env file into a dictionary of key-value pairs."""
    env_file = ROOT_DIR / ".env"
    env_vars = {}
    if not env_file.exists():
        return env_vars
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if include_comments:
                stripped_comment = line.lstrip("#").strip()
                if "=" in stripped_comment:
                    k, v = stripped_comment.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars

def get_configured_data_dir():
    """Reads DATA_DIR from .env or defaults to /data."""
    val = read_env_file().get("DATA_DIR")
    if val:
        return Path(val).resolve() if not val.startswith("/") else Path(val)
    return Path("/data")

def get_configured_seal_type():
    """Reads SEAL_TYPE from os.environ or .env, defaulting to 'local'."""
    if os.getenv("SEAL_TYPE"):
        return os.getenv("SEAL_TYPE").strip().lower()
    val = read_env_file().get("SEAL_TYPE")
    if val:
        return val.strip().lower()
    return "local"

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

def ensure_backend_network():
    """Ensures the external 'backend' Docker network exists."""
    res = subprocess.run("docker network inspect backend", shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"{CYAN}[*] External Docker network 'backend' not found. Creating 'backend'...{RESET}")
        run_cmd("docker network create backend", check=True)
        print(f"{GREEN}[+] Docker network 'backend' successfully created.{RESET}")
    else:
        print(f"{GREEN}[+] Docker external network 'backend' is ready.{RESET}")

def run_preflight_checks(exit_on_failure=True):
    """
    Validates host environment, non-root user permissions, required CLI utilities,
    directory writeability, backend network presence, and port availability.
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
    required_subs = ["postgres", "openbao", "semaphore", "boundary", "credentials"]
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

    # 5. External Network Check & Auto-Creation
    try:
        ensure_backend_network()
        checks.append(CheckResult("Network", "External Docker Network 'backend'", True, "Ready", ""))
    except Exception as e:
        checks.append(CheckResult("Network", "External Docker Network 'backend'", False, str(e), "Run: docker network create backend"))

    # 6. Port Availability & Conflicts (if EXPOSE_PORTS is not false)
    expose_ports = os.getenv("EXPOSE_PORTS", "true").lower() != "false"
    if expose_ports:
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

def ensure_env_file(interactive=True):
    """
    Ensures .env exists from .env.example with newly generated secure random keys.
    If generated in an interactive session, prompts the user to open and edit .env with $EDITOR (default vim).
    """
    env_file = ROOT_DIR / ".env"
    example = ROOT_DIR / ".env.example"
    is_fresh = False
    if not env_file.exists() and example.exists():
        print(f"{CYAN}[*] Generating fresh .env with unique cryptographic keys...{RESET}")
        content = example.read_text(encoding="utf-8")
        
        boundary_db_password = generate_random_password(18)
        semaphore_db_password = generate_random_password(18)
        semaphore_admin_password = generate_random_password(18)
        boundary_kms_root_key = generate_base64_key(32)
        boundary_kms_worker_auth_key = generate_base64_key(32)
        boundary_kms_recovery_key = generate_base64_key(32)
        semaphore_encryption_key = generate_base64_key(32)
        
        content = content.replace("BOUNDARY_DATABASE_PASSWORD=boundarypassword", f"BOUNDARY_DATABASE_PASSWORD={boundary_db_password}")
        content = content.replace("SEMAPHORE_DATABASE_PASSWORD=semaphorepassword", f"SEMAPHORE_DATABASE_PASSWORD={semaphore_db_password}")
        content = content.replace("BOUNDARY_KMS_AEAD_ROOT_KEY=sP191WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU=", f"BOUNDARY_KMS_AEAD_ROOT_KEY={boundary_kms_root_key}")
        content = content.replace("BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY=8pv7uU8g58aN8y1n8PqR8G3z7rW+V8eY9nQ2x3Z1v4U=", f"BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY={boundary_kms_worker_auth_key}")
        content = content.replace("BOUNDARY_KMS_AEAD_RECOVERY_KEY=uK382WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU=", f"BOUNDARY_KMS_AEAD_RECOVERY_KEY={boundary_kms_recovery_key}")
        content = content.replace("SEMAPHORE_ADMIN_PASSWORD=semaphoreadmin", f"SEMAPHORE_ADMIN_PASSWORD={semaphore_admin_password}")
        content = content.replace("SEMAPHORE_ACCESS_KEY_ENCRYPTION=GS3py5Y8+GvF12x0fTfR18k2h4eE9W2d1C8N6Q8T4=0", f"SEMAPHORE_ACCESS_KEY_ENCRYPTION={semaphore_encryption_key}")
        
        env_file.write_text(content, encoding="utf-8")
        print(f"{GREEN}[+] Fresh .env created with newly generated 32-byte KMS/encryption keys and passwords.{RESET}")
        is_fresh = True

    # If interactive and TTY, offer to edit .env
    if interactive and sys.stdin.isatty() and env_file.exists():
        editor = os.getenv("EDITOR", "vim")
        prompt_msg = f"Would you like to review and edit .env using '{editor}' before proceeding? [y/N]: "
        if is_fresh:
            prompt_msg = f"A new .env file was created. Would you like to review/edit credentials in '{editor}'? [Y/n]: "
        try:
            choice = input(prompt_msg).strip().lower()
            should_edit = (choice in ["y", "yes", ""]) if is_fresh else (choice in ["y", "yes"])
            if should_edit:
                print(f"{CYAN}[*] Opening .env with {editor}...{RESET}")
                subprocess.run([editor, str(env_file)])
                print(f"{GREEN}[+] Completed editing .env.{RESET}")
        except (EOFError, KeyboardInterrupt):
            print()

def sync_env_database_url():
    """Ensures runtime environment variables match .env configuration."""
    env_vars = read_env_file()
    for k, v in env_vars.items():
        if k not in os.environ:
            os.environ[k] = v

def set_env_var(key: str, value: str = None, uncomment: bool = True):
    """
    Sets a variable in .env, either uncommented (KEY=value) or commented (# KEY=value).
    If value is None, preserves the existing value in .env while updating comment status.
    """
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    lines = env_file.read_text(encoding="utf-8").splitlines()
    new_lines = []
    found = False
    
    target_active_prefix = f"{key}="
    target_comment_prefix = f"# {key}="
    target_comment_noprefix = f"#{key}="
    
    for l in lines:
        stripped = l.strip()
        if stripped.startswith(target_active_prefix) or stripped.startswith(target_comment_prefix) or stripped.startswith(target_comment_noprefix):
            found = True
            # Determine existing value if value is not provided
            target_val = value
            if target_val is None:
                if "=" in stripped:
                    target_val = stripped.split("=", 1)[1].strip()
                else:
                    target_val = ""
            formatted_line = f"{key}={target_val}" if uncomment else f"# {key}={target_val}"
            new_lines.append(formatted_line)
            if uncomment:
                os.environ[key] = str(target_val)
        else:
            new_lines.append(l)
            
    if not found and value is not None:
        formatted_line = f"{key}={value}" if uncomment else f"# {key}={value}"
        new_lines.append(formatted_line)
        if uncomment:
            os.environ[key] = str(value)
            
    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

def configure_port_binding(expose_ports=True):
    """
    Configures port binding in Docker Compose and .env.
    - If expose_ports is True: writes compose.override.yml with port bindings referencing .env variables
      and uncomments port binding variables in .env.
    - If expose_ports is False: removes compose.override.yml so no ports are bound to the host
      (Internal only, backend network only) and comments out port binding variables in .env.
    """
    override_file = ROOT_DIR / "compose.override.yml"
    
    ports_map = {
        "OPENBAO_PORT_BINDING": "0.0.0.0:8200:8200",
        "BOUNDARY_CONTROLLER_API_PORT": "0.0.0.0:9200:9200",
        "BOUNDARY_CONTROLLER_CLUSTER_PORT": "0.0.0.0:9201:9201",
        "BOUNDARY_WORKER_PROXY_PORT": "0.0.0.0:9202:9202",
        "SEMAPHORE_PORT_BINDING": "0.0.0.0:3000:3000",
    }
    
    set_env_var("EXPOSE_PORTS", "true" if expose_ports else "false", uncomment=True)
    
    for k, default_v in ports_map.items():
        existing_val = os.getenv(k)
        val = existing_val if existing_val else default_v
        set_env_var(k, val, uncomment=expose_ports)

    if expose_ports:
        override_content = """# Auto-generated by Overseer Orchestrator for Host Port Exposure
services:
  openbao:
    ports:
      - "${OPENBAO_PORT_BINDING:-0.0.0.0:8200:8200}"

  boundary-controller:
    ports:
      - "${BOUNDARY_CONTROLLER_API_PORT:-0.0.0.0:9200:9200}"
      - "${BOUNDARY_CONTROLLER_CLUSTER_PORT:-0.0.0.0:9201:9201}"

  boundary-worker:
    ports:
      - "${BOUNDARY_WORKER_PROXY_PORT:-0.0.0.0:9202:9202}"

  semaphore:
    ports:
      - "${SEMAPHORE_PORT_BINDING:-0.0.0.0:3000:3000}"
"""
        override_file.write_text(override_content, encoding="utf-8")
        print(f"{GREEN}[+] Generated compose.override.yml (Host port binding: 0.0.0.0:<port>:<port>){RESET}")
    else:
        if override_file.exists():
            override_file.unlink()
            print(f"{YELLOW}[-] Removed compose.override.yml (Internal only, zero host port bindings){RESET}")

def prompt_and_configure_all(interactive=True):
    """
    Prompts (if interactive) and configures:
    1. Port binding exposure (Host exposed 0.0.0.0:<port>:<port> vs Internal backend only)
    2. Seal backend profile (Local vs GCP Cloud KMS)
    3. OpenBao Shamir Mode (Auto persistent vs Manual ephemeral)
    4. Boundary AEAD Mode (Auto persistent vs Manual ephemeral)
    """
    ensure_env_file(interactive=interactive)
    
    seal_type = get_configured_seal_type()
    expose_ports = os.getenv("EXPOSE_PORTS", "true").lower() != "false"
    shamir_mode = os.getenv("OPENBAO_SHAMIR_MODE", "auto").lower()
    aead_mode = os.getenv("BOUNDARY_AEAD_MODE", "auto").lower()
    
    if interactive and sys.stdin.isatty():
        print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
        print(f"{BOLD}{CYAN}              Overseer Control Plane Configuration Setup                        {RESET}")
        print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
        
        # 1. Port Exposure Question
        print(f"{BOLD}1. Host Port Exposure Mode:{RESET}")
        print("   [1] Bind ports to Host (0.0.0.0: 8200, 9200, 9201, 9202, 3000) [Default]")
        print("   [2] Internal Only (No host port binding, communication via 'backend' network)")
        try:
            port_choice = input("Select [1/2] (default 1): ").strip()
            expose_ports = False if port_choice == "2" else True
        except (EOFError, KeyboardInterrupt):
            expose_ports = True

        # 2. Seal Backend Profile Question
        print(f"\n{BOLD}2. KMS Seal/Unseal Backend Profile:{RESET}")
        print("   [1] Local (Shamir / Local AEAD KMS) [Default]")
        print("   [2] GCP Cloud KMS (Auto-Unseal & Cloud KMS)")
        try:
            seal_choice = input("Select [1/2] (default 1): ").strip()
            seal_type = "gcpkms" if seal_choice == "2" else "local"
        except (EOFError, KeyboardInterrupt):
            seal_type = "local"

        if seal_type == "local":
            # 3. OpenBao Shamir Mode Question
            print(f"\n{BOLD}3. OpenBao Shamir Key Management Mode:{RESET}")
            print("   [1] Auto (Unseal key saved to disk, automated unseal on restart) [Default]")
            print("   [2] Manual (Display key once in terminal, not saved to disk, manual input on restart)")
            try:
                shamir_choice = input("Select [1/2] (default 1): ").strip()
                shamir_mode = "manual" if shamir_choice == "2" else "auto"
            except (EOFError, KeyboardInterrupt):
                shamir_mode = "auto"

            # 4. Boundary AEAD Mode Question
            print(f"\n{BOLD}4. Boundary AEAD KMS Key Management Mode:{RESET}")
            print("   [1] Auto (AEAD keys persisted in .env) [Default]")
            print("   [2] Manual (Display keys once, clear from .env, session injection required on restart)")
            try:
                aead_choice = input("Select [1/2] (default 1): ").strip()
                aead_mode = "manual" if aead_choice == "2" else "auto"
            except (EOFError, KeyboardInterrupt):
                aead_mode = "auto"
        print("-" * 80)

    # Apply Port Binding & .env comments
    configure_port_binding(expose_ports)
    
    # Save modes to .env and os.environ
    set_env_var("SEAL_TYPE", seal_type, uncomment=True)
    set_env_var("OPENBAO_SHAMIR_MODE", shamir_mode, uncomment=True)
    set_env_var("BOUNDARY_AEAD_MODE", aead_mode, uncomment=True)
    
    # Handle GCP KMS variables comment/uncomment (preserve existing values if in .env)
    gcp_keys = [
        ("GCP_PROJECT", "overseer-gcp-project"),
        ("GCP_REGION", "asia-northeast3"),
        ("GCP_KEY_RING", "overseer-keyring"),
        ("GCP_OPENBAO_KEY", "openbao-seal-key"),
        ("GCP_BOUNDARY_ROOT_KEY", "boundary-root-key"),
        ("GCP_BOUNDARY_WORKER_AUTH_KEY", "boundary-worker-auth-key"),
        ("GCP_BOUNDARY_RECOVERY_KEY", "boundary-recovery-key"),
        ("GOOGLE_APPLICATION_CREDENTIALS", ""),
    ]
    is_gcp = (seal_type == "gcpkms")
    for k, default_v in gcp_keys:
        curr_v = os.getenv(k)
        if not curr_v and not is_gcp:
            set_env_var(k, value=None, uncomment=False)
        else:
            val_to_set = curr_v if curr_v is not None else default_v
            set_env_var(k, value=val_to_set, uncomment=is_gcp)
    
    # Read .env to memory
    env_vars = read_env_file()
                
    for k, v in env_vars.items():
        if k not in os.environ:
            os.environ[k] = v

    # Inject OpenBao config
    openbao_profile = "gcp-kms.hcl" if seal_type == "gcpkms" else "local-shamir.hcl"
    openbao_src = ROOT_DIR / "openbao" / "config" / "profiles" / openbao_profile
    openbao_dst = ROOT_DIR / "openbao" / "config" / "openbao.hcl"
    if openbao_src.exists():
        content = openbao_src.read_text(encoding="utf-8")
        for k, v in os.environ.items():
            content = content.replace(f"${{{k}}}", v)
        openbao_dst.write_text(content, encoding="utf-8")
        print(f"{GREEN}[+] Injected OpenBao profile: {openbao_profile} -> openbao/config/openbao.hcl{RESET}")

    # Inject Boundary Controller config
    bnd_ctrl_profile = "gcp-kms.hcl" if seal_type == "gcpkms" else "local-aead.hcl"
    bnd_ctrl_src = ROOT_DIR / "boundary" / "config" / "profiles" / bnd_ctrl_profile
    bnd_ctrl_dst = ROOT_DIR / "boundary" / "config" / "controller.hcl"
    if bnd_ctrl_src.exists():
        content = bnd_ctrl_src.read_text(encoding="utf-8")
        for k, v in os.environ.items():
            content = content.replace(f"${{{k}}}", v)
        bnd_ctrl_dst.write_text(content, encoding="utf-8")
        print(f"{GREEN}[+] Injected Boundary Controller profile: {bnd_ctrl_profile} -> boundary/config/controller.hcl{RESET}")

    # Inject Boundary Worker config
    bnd_worker_profile = "worker-gcp-kms.hcl" if seal_type == "gcpkms" else "worker-local-aead.hcl"
    bnd_worker_src = ROOT_DIR / "boundary" / "config" / "profiles" / bnd_worker_profile
    bnd_worker_dst = ROOT_DIR / "boundary" / "config" / "worker.hcl"
    if bnd_worker_src.exists():
        content = bnd_worker_src.read_text(encoding="utf-8")
        for k, v in os.environ.items():
            content = content.replace(f"${{{k}}}", v)
        bnd_worker_dst.write_text(content, encoding="utf-8")
        print(f"{GREEN}[+] Injected Boundary Worker profile: {bnd_worker_profile} -> boundary/config/worker.hcl{RESET}")

    # If Manual AEAD Mode is chosen, show keys and remove from .env
    if aead_mode == "manual":
        print(f"\n{BOLD}{YELLOW}================================================================================{RESET}")
        print(f"{BOLD}{YELLOW} [IMPORTANT] Boundary Initialized in MANUAL Key Management Mode!                {RESET}")
        print(f"{BOLD}{YELLOW} Please securely copy and backup your AEAD KMS keys below.                      {RESET}")
        print(f"{BOLD}{YELLOW} These keys will be removed from .env file for zero-knowledge safety.           {RESET}")
        print(f"--------------------------------------------------------------------------------")
        print(f" BOUNDARY_KMS_AEAD_ROOT_KEY        : {os.getenv('BOUNDARY_KMS_AEAD_ROOT_KEY')}")
        print(f" BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY : {os.getenv('BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY')}")
        print(f" BOUNDARY_KMS_AEAD_RECOVERY_KEY    : {os.getenv('BOUNDARY_KMS_AEAD_RECOVERY_KEY')}")
        print(f"================================================================================\n")

    return {
        "seal_type": seal_type,
        "expose_ports": expose_ports,
        "shamir_mode": shamir_mode,
        "aead_mode": aead_mode
    }

def check_postgres_ready(timeout=30):
    """Waits for PostgreSQL to accept connections."""
    print(f"{CYAN}[*] Waiting for PostgreSQL backend (service postgres)...{RESET}")
    env_vars = read_env_file()
    bnd_user = env_vars.get("BOUNDARY_DATABASE_USER", "boundary")
    start = time.time()
    while time.time() - start < timeout:
        res = run_cmd(f"docker compose exec -T postgres pg_isready -U {bnd_user}", check=False, capture=True)
        if res.returncode == 0:
            print(f"{GREEN}[+] PostgreSQL is ready.{RESET}")
            return True
        time.sleep(1.5)
    print(f"{RED}[-] PostgreSQL timed out after {timeout}s.{RESET}")
    return False

def ensure_postgres_databases():
    """Ensures dedicated 'boundary' and 'semaphore' users and databases exist with strict least-privilege isolation."""
    print(f"{CYAN}[*] Configuring separated PostgreSQL users and databases...{RESET}")
    env_vars = read_env_file()
    bnd_user = env_vars.get("BOUNDARY_DATABASE_USER", "boundary")
    bnd_pass = env_vars.get("BOUNDARY_DATABASE_PASSWORD", "boundarypassword")
    bnd_db = env_vars.get("BOUNDARY_DATABASE", "boundary")
    
    sem_user = env_vars.get("SEMAPHORE_DATABASE_USER", "semaphore")
    sem_pass = env_vars.get("SEMAPHORE_DATABASE_PASSWORD", "semaphorepassword")
    sem_db = env_vars.get("SEMAPHORE_DATABASE", "semaphore")

    # 1. Ensure Semaphore user exists
    check_user = run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -tc \"SELECT 1 FROM pg_roles WHERE rolname = '{sem_user}'\"", check=False, capture=True)
    if "1" not in check_user.stdout:
        print(f"{CYAN}[*] Creating dedicated PostgreSQL user '{sem_user}'...{RESET}")
        run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -c \"CREATE USER {sem_user} WITH PASSWORD '{sem_pass}';\"", check=False)
    else:
        # Update password if changed
        run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -c \"ALTER USER {sem_user} WITH PASSWORD '{sem_pass}';\"", check=False)

    # 2. Ensure Semaphore database exists and is owned by semaphore user
    check_db = run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -tc \"SELECT 1 FROM pg_database WHERE datname = '{sem_db}'\"", check=False, capture=True)
    if "1" not in check_db.stdout:
        print(f"{CYAN}[*] Creating dedicated PostgreSQL database '{sem_db}' owned by '{sem_user}'...{RESET}")
        run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -c \"CREATE DATABASE {sem_db} OWNER {sem_user};\"", check=False)
        run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -c \"GRANT ALL PRIVILEGES ON DATABASE {sem_db} TO {sem_user};\"", check=False)
        print(f"{GREEN}[+] Created database '{sem_db}' with isolated owner '{sem_user}'.{RESET}")
    else:
        run_cmd(f"docker compose exec -T postgres psql -U {bnd_user} -d {bnd_db} -c \"GRANT ALL PRIVILEGES ON DATABASE {sem_db} TO {sem_user};\"", check=False)
        print(f"{GREEN}[+] Database '{sem_db}' ready.{RESET}")

def init_boundary():
    """Initializes Boundary Database schema."""
    print(f"{CYAN}[*] Initializing Boundary Database Schema...{RESET}")
    run_cmd("docker compose run --rm --entrypoint /bin/sh boundary-controller -c '/boundary/scripts/init-boundary.sh'", check=False)
    print(f"{GREEN}[+] Boundary schema initialized.{RESET}")

def init_openbao():
    """Initializes and unseals OpenBao, setting up SSH CA."""
    print(f"{CYAN}[*] Initializing and unsealing OpenBao & SSH CA...{RESET}")
    run_cmd("docker compose up -d openbao", check=True)
    time.sleep(2)
    shamir_mode = os.getenv("OPENBAO_SHAMIR_MODE", "auto")
    run_cmd(f"docker compose exec -T -e OPENBAO_SHAMIR_MODE={shamir_mode} openbao /bin/sh /openbao/scripts/init-openbao-ssh-ca.sh", check=False)
    print(f"{GREEN}[+] OpenBao SSH CA setup finished.{RESET}")

def init_semaphore():
    """Seeds Semaphore project, keys, gitops repo, and task templates."""
    print(f"{CYAN}[*] Seeding Semaphore UI GitOps Templates...{RESET}")
    init_script = ROOT_DIR / "scripts" / "init-semaphore.sh"
    if init_script.exists():
        run_cmd(str(init_script), check=False)

def deploy_to_target(source_dir: Path, target_dir: Path, execute_bootstrap: bool = True):
    """
    Copies only production-critical operational files to the target deployment directory,
    excluding tests, docs, git repository, test artifacts, and caches.
    Ensures safe permissions and transitions execution to the target directory.
    """
    source_dir = Path(source_dir).resolve()
    target_dir = Path(target_dir).resolve()
    
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}      Deploying Overseer Operational Files to Target Location                   {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}")
    print(f"  Source (Git Workspace) : {source_dir}")
    print(f"  Target (Production)    : {target_dir}\n")

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Top-level essential operational files
    top_files = ["compose.yml", "Makefile", "README.md", "CONTEXT.md", ".env.example"]
    if (source_dir / ".env").exists():
        top_files.append(".env")
    if (source_dir / "compose.override.yml").exists():
        top_files.append("compose.override.yml")
    elif (target_dir / "compose.override.yml").exists():
        (target_dir / "compose.override.yml").unlink()

    for tf in top_files:
        src_f = source_dir / tf
        dst_f = target_dir / tf
        if src_f.exists():
            shutil.copy2(src_f, dst_f)
            print(f"{GREEN}[+] Copied: {tf}{RESET}")

    # 2. OpenBao configuration & scripts
    (target_dir / "openbao" / "config").mkdir(parents=True, exist_ok=True)
    (target_dir / "openbao" / "scripts").mkdir(parents=True, exist_ok=True)
    
    openbao_profiles_src = source_dir / "openbao" / "config" / "profiles"
    if openbao_profiles_src.exists():
        shutil.copytree(openbao_profiles_src, target_dir / "openbao" / "config" / "profiles", dirs_exist_ok=True)
    if (source_dir / "openbao" / "config" / "openbao.hcl").exists():
        shutil.copy2(source_dir / "openbao" / "config" / "openbao.hcl", target_dir / "openbao" / "config" / "openbao.hcl")
    if (source_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").exists():
        shutil.copy2(source_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh", target_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh")
        (target_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").chmod(0o755)

    # 3. Boundary configuration & scripts
    (target_dir / "boundary" / "config").mkdir(parents=True, exist_ok=True)
    (target_dir / "boundary" / "scripts").mkdir(parents=True, exist_ok=True)
    
    boundary_profiles_src = source_dir / "boundary" / "config" / "profiles"
    if boundary_profiles_src.exists():
        shutil.copytree(boundary_profiles_src, target_dir / "boundary" / "config" / "profiles", dirs_exist_ok=True)
    if (source_dir / "boundary" / "config" / "controller.hcl").exists():
        shutil.copy2(source_dir / "boundary" / "config" / "controller.hcl", target_dir / "boundary" / "config" / "controller.hcl")
    if (source_dir / "boundary" / "config" / "worker.hcl").exists():
        shutil.copy2(source_dir / "boundary" / "config" / "worker.hcl", target_dir / "boundary" / "config" / "worker.hcl")
    if (source_dir / "boundary" / "scripts" / "init-boundary.sh").exists():
        shutil.copy2(source_dir / "boundary" / "scripts" / "init-boundary.sh", target_dir / "boundary" / "scripts" / "init-boundary.sh")
        (target_dir / "boundary" / "scripts" / "init-boundary.sh").chmod(0o755)

    # 4. Operational Scripts
    (target_dir / "scripts").mkdir(parents=True, exist_ok=True)
    for sc in ["orchestrator.py", "init-semaphore.sh", "healthcheck.sh"]:
        src_sc = source_dir / "scripts" / sc
        dst_sc = target_dir / "scripts" / sc
        if src_sc.exists():
            shutil.copy2(src_sc, dst_sc)
            dst_sc.chmod(0o755)
            print(f"{GREEN}[+] Copied script: scripts/{sc}{RESET}")

    print(f"\n{BOLD}{GREEN}[+] Production operational files successfully deployed to {target_dir}!{RESET}\n")

    if execute_bootstrap:
        print(f"{CYAN}[*] Executing full-stack bootstrap inside target directory: {target_dir}...{RESET}\n")
        env = os.environ.copy()
        res = subprocess.run(
            ["python3", str(target_dir / "scripts" / "orchestrator.py"), "bootstrap", "--target-dir", str(target_dir)],
            cwd=str(target_dir),
            env=env
        )
        sys.exit(res.returncode)

    return True

def prompt_target_directory(interactive=True, default_target="/opt/services/overseer"):
    """Prompts for target production directory or uses default / env var."""
    if os.getenv("OVERSEER_TARGET_DIR"):
        return Path(os.getenv("OVERSEER_TARGET_DIR")).resolve()
    if not interactive or not sys.stdin.isatty():
        return Path(default_target).resolve()
    
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}           Overseer Production Installation Directory Selection                 {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
    print(f" Overseer will copy production-critical files (excluding tests/docs/git) to this directory.")
    print(f" Default installation target: {BOLD}{default_target}{RESET}\n")
    try:
        user_input = input(f"Enter target path (Press Enter for '{default_target}'): ").strip()
        chosen = user_input if user_input else default_target
        return Path(chosen).resolve()
    except (EOFError, KeyboardInterrupt):
        return Path(default_target).resolve()

def bootstrap(target_dir_param=None):
    """Full end-to-end bootstrap of all Control Plane services."""
    current_root = ROOT_DIR.resolve()
    
    # 0. Check if we should deploy to a target production directory
    target_dir = None
    if target_dir_param:
        target_dir = Path(target_dir_param).resolve()
    elif os.getenv("OVERSEER_TARGET_DIR"):
        target_dir = Path(os.getenv("OVERSEER_TARGET_DIR")).resolve()
    elif (current_root / ".git").exists() or (current_root / "tests").exists():
        # Running from source/git repository: prompt or default to /opt/services/overseer
        target_dir = prompt_target_directory(interactive=True, default_target="/opt/services/overseer")

    if target_dir and target_dir != current_root:
        deploy_to_target(source_dir=current_root, target_dir=target_dir, execute_bootstrap=True)
        return

    # 0. Pre-Flight Prerequisites Validation (including backend network)
    run_preflight_checks(exit_on_failure=True)

    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}           Overseer Control Plane Full-Stack Bootstrap Starting         {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
    
    # 0.1 Prompt and configure all modular options
    prompt_and_configure_all(interactive=True)
    
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
    env_vars = read_env_file()
    bnd_user = env_vars.get("BOUNDARY_DATABASE_USER", "boundary")
    
    services = [
        ("1. PostgreSQL (5432)", f"docker compose exec -T postgres pg_isready -U {bnd_user}", "tcp"),
        ("2. OpenBao API (8200)", "docker compose exec -T openbao bao status -address=http://127.0.0.1:8200", "cli"),
        ("3. Boundary Controller (9200)", "curl -s http://127.0.0.1:9200/v1/health || docker compose exec -T boundary-controller /bin/sh -c 'curl -s http://127.0.0.1:9200/v1/health'", "http"),
        ("4. Boundary Worker (9202)", "nc -z 127.0.0.1 9202 || docker compose exec -T boundary-worker /bin/sh -c 'nc -z 127.0.0.1 9202'", "tcp"),
        ("5. Semaphore UI (3000)", "curl -s http://127.0.0.1:3000/api/ping || docker compose exec -T semaphore /bin/sh -c 'nc -z 127.0.0.1 3000'", "http"),
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
    parser.add_argument("action", choices=["bootstrap", "up", "preflight", "status", "down", "init-postgres", "init-openbao", "init-boundary", "init-semaphore", "configure-seal", "deploy-target"], help="Action to perform")
    parser.add_argument("--target-dir", default=None, help="Target production installation directory (default: /opt/services/overseer)")
    parser.add_argument("--seal-type", choices=["local", "gcpkms"], default=None, help="Force specific seal backend")
    parser.add_argument("--expose-ports", choices=["true", "false"], default=None, help="Expose ports to host")
    parser.add_argument("--shamir-mode", choices=["auto", "manual"], default=None, help="OpenBao shamir unseal mode")
    parser.add_argument("--aead-mode", choices=["auto", "manual"], default=None, help="Boundary AEAD mode")
    
    args = parser.parse_args()
    
    if args.target_dir:
        os.environ["OVERSEER_TARGET_DIR"] = args.target_dir
    if args.seal_type:
        os.environ["SEAL_TYPE"] = args.seal_type
    if args.expose_ports:
        os.environ["EXPOSE_PORTS"] = args.expose_ports
    if args.shamir_mode:
        os.environ["OPENBAO_SHAMIR_MODE"] = args.shamir_mode
    if args.aead_mode:
        os.environ["BOUNDARY_AEAD_MODE"] = args.aead_mode

    if args.action in ["bootstrap", "up"]:
        bootstrap(target_dir_param=args.target_dir)
    elif args.action == "deploy-target":
        target = Path(args.target_dir if args.target_dir else "/opt/services/overseer").resolve()
        deploy_to_target(source_dir=ROOT_DIR, target_dir=target, execute_bootstrap=False)
    elif args.action == "preflight":
        passed = run_preflight_checks(exit_on_failure=False)
        sys.exit(0 if passed else 1)
    elif args.action == "configure-seal":
        prompt_and_configure_all(interactive=False)
    elif args.action == "status":
        sys.exit(check_service_status())
    elif args.action == "down":
        run_cmd("docker compose down", check=True)
    elif args.action == "init-postgres":
        ensure_postgres_databases()
    elif args.action == "init-openbao":
        init_openbao()
    elif args.action == "init-boundary":
        init_boundary()
    elif args.action == "init-semaphore":
        init_semaphore()

if __name__ == "__main__":
    main()
