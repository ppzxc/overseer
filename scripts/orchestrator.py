#!/usr/bin/env python3
"""
Overseer Control Plane Lifecycle & Bootstrap Orchestrator
Provides unified initialization for OpenBao and Semaphore, health checks,
pluggable OpenBao seal profiles, port exposure, network bootstrapping, and key management.
"""

import os
import sys
import time
import shutil
import subprocess
import argparse
import base64
import json
import secrets
import string
import shlex
from pathlib import Path
from typing import NamedTuple, List

class CheckResult(NamedTuple):
    category: str
    item: str
    passed: bool
    detail: str
    remediation: str

ROOT_DIR = Path(__file__).resolve().parent.parent

if hasattr(os, "getuid") and hasattr(os, "getgid"):
    os.environ.setdefault("CURRENT_UID", str(os.getuid()))
    os.environ.setdefault("CURRENT_GID", str(os.getgid()))
else:
    os.environ.setdefault("CURRENT_UID", "1000")
    os.environ.setdefault("CURRENT_GID", "1000")

def read_env_file(include_comments: bool = False, path=None) -> dict:
    """Parses .env file into a dictionary of key-value pairs."""
    env_file = Path(path) if path else ROOT_DIR / ".env"
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

def compose_command(service: str, *arguments: str) -> str:
    """Build a Compose command for one independently managed service."""
    compose_file = ROOT_DIR / service / "compose.yml"
    if service not in {"openbao", "semaphore"} or not compose_file.exists():
        raise ValueError(f"Unknown or missing Compose service: {service}")

    command = [
        "docker", "compose",
        "--project-directory", str(ROOT_DIR),
        "--env-file", str(ROOT_DIR / ".env"),
        "-f", str(compose_file),
    ]
    override_file = ROOT_DIR / service / "compose.override.yml"
    if override_file.exists():
        command.extend(["-f", str(override_file)])
    command.extend(arguments)
    return shlex.join(command)

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
    required_subs = ["openbao", "semaphore", "semaphore-db", "credentials"]
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
        ports_to_check = [(3000, "Semaphore Web UI")]
        for port, service_desc in ports_to_check:
            service = "openbao" if port == 8200 else "semaphore"
            running_containers_res = run_cmd(compose_command(service, "ps", "-q", service), check=False, capture=True)
            service_running = bool(running_containers_res.stdout.strip())
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            conn_res = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if conn_res == 0:
                if service_running:
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

def ensure_env_file(interactive=False):
    """
    Ensures .env exists from .env.example with newly generated secure random keys.
    Also guarantees the Semaphore admin password and encryption key are generated.
    """
    env_file = ROOT_DIR / ".env"
    example = ROOT_DIR / ".env.example"
    
    if env_file.exists() and interactive and sys.stdin.isatty():
        print(f"\n{BOLD}{YELLOW}================================================================================{RESET}")
        print(f"{BOLD}{YELLOW}               Existing .env File Detected                                      {RESET}")
        print(f"{BOLD}{YELLOW}================================================================================{RESET}\n")
        print(f" An existing {BOLD}.env{RESET} file was found.")
        print(f" Resetting will regenerate fresh random credentials from the latest {BOLD}.env.example{RESET} template.")
        try:
            choice = input("Reset and regenerate .env to latest template? [y/N]: ").strip().lower()
            if choice in ["y", "yes"]:
                env_file.unlink()
                print(f"{GREEN}[+] Removed existing .env file. Regenerating from .env.example...{RESET}")
        except (EOFError, KeyboardInterrupt):
            pass

    if not env_file.exists() and example.exists():
        print(f"{CYAN}[*] Generating fresh .env with unique cryptographic keys...{RESET}")
        shutil.copy2(example, env_file)
        
    if env_file.exists():
        env_vars = read_env_file(include_comments=False)
        
        # 1. Generate the administrator password if default or empty
        if env_vars.get("SEMAPHORE_ADMIN_PASSWORD") in [None, "", "semaphoreadmin"]:
            set_env_var("SEMAPHORE_ADMIN_PASSWORD", generate_random_password(18), uncomment=True)
            
        # 2. Generate 32-byte cryptographic keys if empty or dummy
        dummy_keys = [
            "sP191WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU=",
            "8pv7uU8g58aN8y1n8PqR8G3z7rW+V8eY9nQ2x3Z1v4U=",
            "uK382WKGvgcuEmhdREQBPBG5nhAAda4e+bQQnFRinCU=",
            "GS3py5Y8+GvF12x0fTfR18k2h4eE9W2d1C8N6Q8T4=0",
        ]
        if env_vars.get("SEMAPHORE_ACCESS_KEY_ENCRYPTION") in [None, ""] + dummy_keys:
            set_env_var("SEMAPHORE_ACCESS_KEY_ENCRYPTION", generate_base64_key(32), uncomment=True)
            
        # Reload into os.environ only if not already present in environment
        # (Exclude mode selector flags so dynamic/interactive selection is respected)
        control_flags = {"KEY_MANAGEMENT_PROFILE", "SEAL_TYPE", "OPENBAO_SHAMIR_MODE", "EXPOSE_PORTS"}
        fresh_vars = read_env_file(include_comments=False)
        for k, v in fresh_vars.items():
            if k not in os.environ and k not in control_flags:
                os.environ[k] = v

def prompt_edit_env_file(interactive=True):
    """
    Offers to open and edit .env with $EDITOR (default vim) right before starting containers.
    """
    env_file = ROOT_DIR / ".env"
    if interactive and sys.stdin.isatty() and env_file.exists():
        editor = os.getenv("EDITOR", "vim")
        print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
        print(f"{BOLD}{CYAN}                    Final .env Review & Customization                           {RESET}")
        print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
        print(f" All configuration and credentials have been written to {BOLD}.env{RESET}.")
        try:
            choice = input(f"Would you like to review and edit .env using '{editor}' before starting containers? [y/N]: ").strip().lower()
            if choice in ["y", "yes"]:
                print(f"{CYAN}[*] Opening .env with {editor}...{RESET}")
                subprocess.run([editor, str(env_file)])
                print(f"{GREEN}[+] Completed editing .env.{RESET}")
                # Reload env vars to process environment in case of edits
                env_vars = read_env_file()
                for k, v in env_vars.items():
                    os.environ[k] = v
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
            if uncomment and target_val != "":
                os.environ[key] = str(target_val)
        else:
            new_lines.append(l)
            
    if not found and value is not None:
        formatted_line = f"{key}={value}" if uncomment else f"# {key}={value}"
        new_lines.append(formatted_line)
        if uncomment and value != "":
            os.environ[key] = str(value)
            
    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

def render_semaphore_port_override() -> str:
    """Return the optional host binding for Semaphore; OpenBao stays internal."""
    return (
        "# Auto-generated by Overseer Orchestrator for Semaphore host port exposure\n"
        "services:\n  semaphore:\n    ports:\n"
        '      - "${SEMAPHORE_PORT_BINDING:-0.0.0.0:3000:3000}"\n'
    )

def configure_port_binding(expose_ports=True):
    """
    Configures port binding in Docker Compose and .env.
    - If expose_ports is True: writes one service override per Compose project.
    - If expose_ports is False: removes both service overrides so no host ports are bound
      (Internal only, backend network only) and comments out port binding variables in .env.
    """
    ports_map = {"SEMAPHORE_PORT_BINDING": "0.0.0.0:3000:3000"}
    
    set_env_var("EXPOSE_PORTS", "true" if expose_ports else "false", uncomment=True)
    
    for k, default_v in ports_map.items():
        existing_val = os.getenv(k)
        val = existing_val if existing_val else default_v
        set_env_var(k, val, uncomment=expose_ports)

    if expose_ports:
        openbao_override = ROOT_DIR / "openbao" / "compose.override.yml"
        if openbao_override.exists():
            openbao_override.unlink()
        (ROOT_DIR / "semaphore" / "compose.override.yml").write_text(
            render_semaphore_port_override(), encoding="utf-8"
        )
        print(f"{GREEN}[+] Generated service Compose overrides for host port exposure{RESET}")
    else:
        for service in ("openbao", "semaphore"):
            override_file = ROOT_DIR / service / "compose.override.yml"
            if override_file.exists():
                override_file.unlink()
        print(f"{YELLOW}[-] Removed service Compose overrides (no host port bindings){RESET}")

def ensure_runtime_keys_injected(interactive=True):
    """
    Validates that necessary encryption and KMS keys are present in the runtime environment
    (from .env or shell environment injection). If missing (e.g. after reboot in manual mode),
    prompts the user interactively to inject them into the session memory.
    """
    seal_type = get_configured_seal_type()
    if seal_type == "gcpkms":
        return True

    env_vars = read_env_file()
    required_keys = [
        ("SEMAPHORE_ACCESS_KEY_ENCRYPTION", "Semaphore Access Key Encryption (32-byte Base64)"),
    ]

    missing = []
    for k, desc in required_keys:
        val = os.getenv(k) or env_vars.get(k)
        if not val:
            missing.append((k, desc))

    if missing:
        if interactive and sys.stdin.isatty():
            import getpass
            print(f"\n{BOLD}{YELLOW}================================================================================{RESET}")
            print(f"{BOLD}{YELLOW}       Manual Key Management Mode - Session Key Injection Required              {RESET}")
            print(f"{BOLD}{YELLOW}================================================================================{RESET}\n")
            print(" Master encryption keys are not found in .env (Zero-Knowledge Manual Mode).")
            print(" Please input the keys below to inject them into the current startup session.\n")
            print(" (Alternatively, export them as environment variables before starting: e.g. export KEY=...)\n")
            
            for k, desc in missing:
                try:
                    val = getpass.getpass(f" Enter {desc}: ").strip()
                    if not val:
                        val = input(f" (Visible input) Enter {desc}: ").strip()
                    if val:
                        os.environ[k] = val
                    else:
                        print(f"{RED}[!] Missing required key {k}. Startup may fail.{RESET}")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
        else:
            print(f"{YELLOW}[!] Notice: Running in manual mode with missing keys in .env. Ensure keys are exported in environment.{RESET}")
    return True

def prompt_and_configure_all(interactive=True):
    """
    Prompts (if interactive) and configures:
    1. Host Port binding exposure (Host exposed 0.0.0.0:<port>:<port> vs Internal backend only)
    2. Key Management & Storage Profile:
       [1] Local .env Persisted (Keys saved to host .env & disk, automatic reboot unseal)
       [2] Zero-Knowledge Manual (Keys printed once, completely wiped from .env & disk)
       [3] External Cloud KMS (Google Cloud KMS Cloud HSM auto-unseal)
    """
    ensure_env_file(interactive=interactive)
    
    # Determine defaults from existing env
    seal_type = get_configured_seal_type()
    expose_ports = os.getenv("EXPOSE_PORTS", "true").lower() != "false"
    shamir_mode = os.getenv("OPENBAO_SHAMIR_MODE", "auto").lower()
    
    # Unified profile detection
    if "SEAL_TYPE" in os.environ and os.environ["SEAL_TYPE"].strip().lower() == "gcpkms":
        profile = "gcpkms"
    elif "OPENBAO_SHAMIR_MODE" in os.environ and os.environ["OPENBAO_SHAMIR_MODE"].strip().lower() == "manual":
        profile = "manual"
    elif "KEY_MANAGEMENT_PROFILE" in os.environ and os.environ["KEY_MANAGEMENT_PROFILE"].strip():
        profile = os.environ["KEY_MANAGEMENT_PROFILE"].strip().lower()
    elif "SEAL_TYPE" in os.environ and os.environ["SEAL_TYPE"].strip().lower() == "local":
        profile = "local"
    else:
        env_profile = read_env_file().get("KEY_MANAGEMENT_PROFILE")
        if env_profile:
            profile = env_profile.strip().lower()
        elif seal_type == "gcpkms":
            profile = "gcpkms"
        elif shamir_mode == "manual":
            profile = "manual"
        else:
            profile = "local"
    
    if interactive and sys.stdin.isatty():
        print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
        print(f"{BOLD}{CYAN}              Overseer Control Plane Configuration Setup                        {RESET}")
        print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
        
        # 1. Port Exposure Question
        print(f"{BOLD}1. Host Port Exposure Mode:{RESET}")
        print("   [1] Bind ports to Host (0.0.0.0: 8200, 3000) [Default]")
        print("   [2] Internal Only (No host port binding, communication via 'backend' network)")
        try:
            port_choice = input("Select [1/2] (default 1): ").strip()
            expose_ports = False if port_choice == "2" else True
        except (EOFError, KeyboardInterrupt):
            expose_ports = True

        # 2. Key Management & Storage Profile Question
        print(f"\n{BOLD}2. Master Key Management & Storage Profile:{RESET}")
        print("   [1] Local .env Persisted (Keys stored in .env, automatic reboot recovery) [Default]")
        print("   [2] Zero-Knowledge Manual (Display keys once, completely wipe from .env & disk)")
        print("   [3] External Cloud KMS (Google Cloud KMS Cloud HSM Auto-Unseal)")
        try:
            prof_choice = input("Select [1/2/3] (default 1): ").strip()
            if prof_choice == "2":
                profile = "manual"
            elif prof_choice == "3":
                profile = "gcpkms"
            else:
                profile = "local"
        except (EOFError, KeyboardInterrupt):
            profile = "local"
        print("-" * 80)

    # Apply resolved settings
    if profile == "gcpkms":
        seal_type = "gcpkms"
        shamir_mode = os.getenv("OPENBAO_SHAMIR_MODE", "auto")
    elif profile == "manual":
        seal_type = "local"
        shamir_mode = "manual"
    else:
        seal_type = "local"
        shamir_mode = "auto"

    # Apply Port Binding & .env comments
    configure_port_binding(expose_ports)
    
    # Save modes to .env and os.environ
    set_env_var("SEAL_TYPE", seal_type, uncomment=True)
    set_env_var("OPENBAO_SHAMIR_MODE", shamir_mode, uncomment=True)
    set_env_var("KEY_MANAGEMENT_PROFILE", profile, uncomment=True)
    
    # Handle GCP KMS variables comment/uncomment (preserve existing values if in .env)
    gcp_keys = [
        ("GCP_PROJECT", "overseer-gcp-project"),
        ("GCP_REGION", "asia-northeast3"),
        ("GCP_KEY_RING", "overseer-keyring"),
        ("GCP_OPENBAO_KEY", "openbao-seal-key"),
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
        if k not in os.environ and v:
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

    # If Manual Mode is chosen: Display keys securely and completely wipe from .env
    if profile == "manual":
        sem_k = os.getenv("SEMAPHORE_ACCESS_KEY_ENCRYPTION") or env_vars.get("SEMAPHORE_ACCESS_KEY_ENCRYPTION") or generate_base64_key(32)

        print(f"\n{BOLD}{YELLOW}================================================================================{RESET}")
        print(f"{BOLD}{YELLOW} [IMPORTANT] ZERO-KNOWLEDGE MANUAL KEY MANAGEMENT MODE ACTIVATED!               {RESET}")
        print(f"{BOLD}{YELLOW} Please securely copy and store the master encryption keys below.               {RESET}")
        print(f"{BOLD}{YELLOW} These keys will now be COMPLETELY WIPED from .env and disk!                    {RESET}")
        print(f"--------------------------------------------------------------------------------")
        print(f" SEMAPHORE_ACCESS_KEY_ENCRYPTION   : {sem_k}")
        print(f"--------------------------------------------------------------------------------")
        print(f" (To restart containers later, export them in shell or enter interactively on make up)")
        print(f"================================================================================\n")

        # Keep values in os.environ for current running process
        os.environ["SEMAPHORE_ACCESS_KEY_ENCRYPTION"] = sem_k

        # Wipe keys from .env file on disk
        set_env_var("SEMAPHORE_ACCESS_KEY_ENCRYPTION", "", uncomment=True)

    return {
        "seal_type": seal_type,
        "expose_ports": expose_ports,
        "shamir_mode": shamir_mode,
        "key_management_profile": profile
    }

def wait_for_container_running(service_name: str, timeout: int = 20) -> bool:
    """Waits until a Docker Compose service reaches 'running' state."""
    start = time.time()
    while time.time() - start < timeout:
        res = run_cmd(compose_command(service_name, "ps", "--format", "{{.State}}", service_name), check=False, capture=True)
        state = res.stdout.strip().lower()
        if "running" in state:
            return True
        time.sleep(1)
    return False

def init_openbao():
    """Initializes and unseals OpenBao, setting up SSH CA."""
    print(f"{CYAN}[*] Initializing and unsealing OpenBao & SSH CA...{RESET}")
    run_cmd(compose_command("openbao", "up", "-d", "openbao"), check=True)
    wait_for_container_running("openbao", timeout=15)
    time.sleep(2)
    shamir_mode = os.getenv("OPENBAO_SHAMIR_MODE") or read_env_file().get("OPENBAO_SHAMIR_MODE", "auto")
    status_res = run_cmd(
        compose_command("openbao", "exec", "-T", "openbao", "bao", "status", "-format=json"),
        check=False,
        capture=True,
    )
    try:
        bao_status = json.loads(status_res.stdout)
    except (json.JSONDecodeError, TypeError):
        raise RuntimeError("Could not read OpenBao status safely; refusing to run initialization.")

    if "initialized" not in bao_status or "sealed" not in bao_status:
        raise RuntimeError("OpenBao status is incomplete; refusing to run initialization.")

    if bao_status.get("initialized") and not bao_status.get("sealed"):
        print(f"{GREEN}[+] OpenBao is already initialized and unsealed; skipping initialization.{RESET}")
        return

    if bao_status.get("initialized") and bao_status.get("sealed") and shamir_mode == "manual":
        if not sys.stdin.isatty():
            raise RuntimeError("OpenBao is sealed in manual mode; run this command interactively to enter the unseal key.")
        print(f"{YELLOW}[!] Enter the manual unseal key in OpenBao's hidden prompt.{RESET}")
        run_cmd(compose_command("openbao", "exec", "-it", "openbao", "bao", "operator", "unseal"), check=True)
        verify_res = run_cmd(
            compose_command("openbao", "exec", "-T", "openbao", "bao", "status", "-format=json"),
            check=False,
            capture=True,
        )
        try:
            verified_status = json.loads(verify_res.stdout)
        except (json.JSONDecodeError, TypeError):
            raise RuntimeError("Could not verify OpenBao unseal status.")
        if not verified_status.get("initialized") or verified_status.get("sealed"):
            raise RuntimeError("OpenBao remains sealed after the manual unseal attempt.")
        print(f"{GREEN}[+] OpenBao unsealed successfully; existing SSH CA configuration is retained.{RESET}")
        return
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        res = run_cmd(compose_command("openbao", "exec", "-T", "-u", "0:0", "-e", f"OPENBAO_SHAMIR_MODE={shamir_mode}", "openbao", "/bin/sh", "/openbao/scripts/init-openbao-ssh-ca.sh"), check=False)
        if res.returncode == 0:
            print(f"{GREEN}[+] OpenBao SSH CA setup finished.{RESET}")
            return
        time.sleep(2)
    print(f"{YELLOW}[!] OpenBao SSH CA setup finished with non-zero exit code.{RESET}")

def init_semaphore():
    """Seeds Semaphore project, keys, gitops repo, and task templates."""
    print(f"{CYAN}[*] Seeding Semaphore UI GitOps Templates...{RESET}")
    init_script = ROOT_DIR / "scripts" / "init-semaphore.sh"
    if init_script.exists():
        run_cmd(str(init_script), check=False)

def deploy_to_target(source_dir: Path, target_dir: Path):
    """
    Copies only production-critical operational files to the target deployment directory,
    excluding tests, docs, git repository, test artifacts, and caches.
    Preserves target environment state and does not start production services.
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
    top_files = ["Makefile", "README.md", "CONTEXT.md", ".env.example"]

    for tf in top_files:
        src_f = source_dir / tf
        dst_f = target_dir / tf
        if src_f.exists():
            shutil.copy2(src_f, dst_f)
            print(f"{GREEN}[+] Copied: {tf}{RESET}")

    # Remove obsolete combined Compose entrypoints without touching service data.
    for obsolete_file in ("compose.yml", "compose.override.yml"):
        stale_compose = target_dir / obsolete_file
        if stale_compose.exists():
            stale_compose.unlink()
            print(f"{YELLOW}[-] Removed obsolete {obsolete_file}{RESET}")

    # Each service owns its Compose project file and optional generated port override.
    for service in ("openbao", "semaphore"):
        for filename in ("compose.yml", "compose.override.yml"):
            src_compose = source_dir / service / filename
            dst_compose = target_dir / service / filename
            if src_compose.exists():
                dst_compose.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_compose, dst_compose)
            elif filename == "compose.override.yml" and dst_compose.exists():
                dst_compose.unlink()
    target_env = read_env_file(path=target_dir / ".env")
    semaphore_override = target_dir / "semaphore" / "compose.override.yml"
    openbao_override = target_dir / "openbao" / "compose.override.yml"
    if target_env.get("EXPOSE_PORTS", "false").lower() == "false":
        if semaphore_override.exists():
            semaphore_override.unlink()
    else:
        semaphore_override.parent.mkdir(parents=True, exist_ok=True)
        semaphore_override.write_text(render_semaphore_port_override(), encoding="utf-8")
    if openbao_override.exists():
        openbao_override.unlink()
    requirements_src = source_dir / "semaphore" / "requirements.txt"
    if requirements_src.exists():
        (target_dir / "semaphore").mkdir(parents=True, exist_ok=True)
        shutil.copy2(requirements_src, target_dir / "semaphore" / "requirements.txt")

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

    # 4. Operational Scripts
    (target_dir / "scripts").mkdir(parents=True, exist_ok=True)
    for sc in ["orchestrator.py", "init-semaphore.sh", "healthcheck.sh", "migrate-semaphore-postgres-to-sqlite.py"]:
        src_sc = source_dir / "scripts" / sc
        dst_sc = target_dir / "scripts" / sc
        if src_sc.exists():
            shutil.copy2(src_sc, dst_sc)
            dst_sc.chmod(0o755)
            print(f"{GREEN}[+] Copied script: scripts/{sc}{RESET}")

    migration_guide = source_dir / "docs" / "control-plane" / "semaphore-postgres-to-sqlite.md"
    if migration_guide.exists():
        guide_target = target_dir / "docs" / "control-plane" / migration_guide.name
        guide_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(migration_guide, guide_target)
        print(f"{GREEN}[+] Copied operational guide: docs/control-plane/{migration_guide.name}{RESET}")

    print(f"\n{BOLD}{GREEN}[+] Production operational files successfully deployed to {target_dir}!{RESET}\n")

    return True

def bootstrap():
    """Full end-to-end bootstrap of all Control Plane services."""

    # 0. Pre-Flight Prerequisites Validation (including backend network)
    run_preflight_checks(exit_on_failure=True)

    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}           Overseer Control Plane Full-Stack Bootstrap Starting         {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")
    
    # 0.1 Prompt and configure all modular options
    prompt_and_configure_all(interactive=True)
    
    # 0.2 Final Review & Customization in $EDITOR (vim) before starting containers
    prompt_edit_env_file(interactive=True)
    
    # 1. Initialize OpenBao
    init_openbao()
    
    # 2. Start Semaphore using its own Compose project; OpenBao was started above.
    print(f"{CYAN}[*] Starting Semaphore UI...{RESET}")
    run_cmd(compose_command("semaphore", "up", "-d", "semaphore"), check=True)
    
    # 4. Seed Semaphore
    init_semaphore()
    
    print(f"\n{BOLD}{GREEN}================================================================================{RESET}")
    print(f"{BOLD}{GREEN}  Overseer Control Plane is UP and READY!                                      {RESET}")
    print(f"{BOLD}{GREEN}  - OpenBao Web UI:     http://localhost:8200                                   {RESET}")
    print(f"{BOLD}{GREEN}  - Semaphore Web UI:   http://localhost:3000                                   {RESET}")
    print(f"{BOLD}{GREEN}================================================================================{RESET}\n")

def check_service_status():
    """Detailed health check and status reporting across all control plane services."""
    print(f"\n{BOLD}Checking Overseer Control Plane Services Health...{RESET}\n")
    services = [
        ("1. OpenBao API (8200)", compose_command("openbao", "exec", "-T", "openbao", "bao", "status", "-address=http://127.0.0.1:8200"), "cli"),
        ("2. Semaphore UI (3000)", "curl -s http://127.0.0.1:3000/api/ping || " + compose_command("semaphore", "exec", "-T", "semaphore", "/bin/sh", "-c", "nc -z 127.0.0.1 3000"), "http"),
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

def follow_service_logs():
    """Follow both service logs without combining their Compose project files."""
    processes = [
        subprocess.Popen(shlex.split(compose_command(service, "logs", "-f", service)), cwd=str(ROOT_DIR))
        for service in ("openbao", "semaphore")
    ]
    try:
        while any(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        for process in processes:
            if process.poll() is None:
                process.terminate()
    finally:
        for process in processes:
            if process.poll() is None:
                process.wait()

def main():
    parser = argparse.ArgumentParser(description="Overseer Control Plane Lifecycle Orchestrator")
    parser.add_argument("action", choices=["bootstrap", "up", "preflight", "status", "down", "init-openbao", "init-semaphore", "start-semaphore", "stop-openbao", "stop-semaphore", "restart-openbao", "restart-semaphore", "logs", "logs-openbao", "logs-semaphore", "configure-seal", "deploy-target"], help="Action to perform")
    parser.add_argument("--target-dir", default=None, help="Target production installation directory (default: /opt/services/overseer)")
    parser.add_argument("--seal-type", choices=["local", "gcpkms"], default=None, help="Force specific seal backend")
    parser.add_argument("--expose-ports", choices=["true", "false"], default=None, help="Expose ports to host")
    parser.add_argument("--shamir-mode", choices=["auto", "manual"], default=None, help="OpenBao shamir unseal mode")
    
    args = parser.parse_args()
    
    if args.action in ["bootstrap", "up"] and args.target_dir:
        parser.error("bootstrap only starts services from the current directory; use production-sync to copy files")

    if args.target_dir:
        os.environ["OVERSEER_TARGET_DIR"] = args.target_dir
    if args.seal_type:
        os.environ["SEAL_TYPE"] = args.seal_type
    if args.expose_ports:
        os.environ["EXPOSE_PORTS"] = args.expose_ports
    if args.shamir_mode:
        os.environ["OPENBAO_SHAMIR_MODE"] = args.shamir_mode

    if args.action in ["bootstrap", "up"]:
        bootstrap()
    elif args.action == "deploy-target":
        target = Path(args.target_dir if args.target_dir else "/opt/services/overseer").resolve()
        deploy_to_target(source_dir=ROOT_DIR, target_dir=target)
    elif args.action == "preflight":
        passed = run_preflight_checks(exit_on_failure=False)
        sys.exit(0 if passed else 1)
    elif args.action == "configure-seal":
        prompt_and_configure_all(interactive=False)
    elif args.action == "status":
        sys.exit(check_service_status())
    elif args.action == "down":
        for service in ("semaphore", "openbao"):
            run_cmd(compose_command(service, "stop", service), check=True)
            run_cmd(compose_command(service, "rm", "-f", service), check=True)
    elif args.action == "init-openbao":
        init_openbao()
    elif args.action == "init-semaphore":
        init_semaphore()
    elif args.action == "start-semaphore":
        run_cmd(compose_command("semaphore", "up", "-d", "semaphore"), check=True)
    elif args.action == "stop-openbao":
        run_cmd(compose_command("openbao", "stop", "openbao"), check=True)
    elif args.action == "stop-semaphore":
        run_cmd(compose_command("semaphore", "stop", "semaphore"), check=True)
    elif args.action == "restart-openbao":
        run_cmd(compose_command("openbao", "restart", "openbao"), check=True)
    elif args.action == "restart-semaphore":
        run_cmd(compose_command("semaphore", "restart", "semaphore"), check=True)
    elif args.action == "logs":
        follow_service_logs()
    elif args.action == "logs-openbao":
        run_cmd(compose_command("openbao", "logs", "--tail", "100", "openbao"), check=True)
    elif args.action == "logs-semaphore":
        run_cmd(compose_command("semaphore", "logs", "--tail", "100", "semaphore"), check=True)

if __name__ == "__main__":
    main()
