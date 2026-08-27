"""
E2E Test 04: Ansible Inventory & Architecture Validation
Verifies that Ansible configuration, inventory definitions (overseer & servers), playbooks, and roles are properly wired.
"""

import yaml
import pytest
from pathlib import Path

def test_ansible_inventory_and_vars(root_dir):
    """Ansible 인벤토리 및 group_vars 파일 유효성 검증 (overseer / servers 그룹 격리)"""
    inv_file = root_dir / "ansible" / "inventory" / "hosts.yml"
    if not inv_file.exists():
        inv_file = root_dir / "ansible" / "inventory" / "hosts.yml.example"
    assert inv_file.exists(), "Inventory file hosts.yml or hosts.yml.example is missing"
    
    with open(inv_file, 'r', encoding='utf-8') as f:
        inv_data = yaml.safe_load(f)
    assert "all" in inv_data, "Inventory missing root 'all' key"
    children = inv_data["all"].get("children", {})
    assert "overseer" in children, "Missing 'overseer' group in inventory"
    assert "servers" in children, "Missing 'servers' group in inventory"
    
    # group_vars 검증
    all_vars_file = root_dir / "ansible" / "inventory" / "group_vars" / "all.yml"
    assert all_vars_file.exists(), "group_vars/all.yml is missing"
    with open(all_vars_file, 'r', encoding='utf-8') as f:
        all_vars = yaml.safe_load(f)
    assert "admin_user" in all_vars, "admin_user is not defined in all.yml"
    assert "timezone" in all_vars, "timezone is not defined in all.yml"
    assert "otel_target_endpoint" in all_vars, "otel_target_endpoint is not defined in all.yml"

    # overseer group_vars 검증
    overseer_vars_file = root_dir / "ansible" / "inventory" / "group_vars" / "overseer.yml"
    assert overseer_vars_file.exists(), "group_vars/overseer.yml is missing"
    with open(overseer_vars_file, 'r', encoding='utf-8') as f:
        overseer_vars = yaml.safe_load(f)
    assert "overseer_install_dir" in overseer_vars, "overseer_install_dir is not defined in overseer.yml"
    assert "docker_metrics_enabled" in overseer_vars, "docker_metrics_enabled is not defined in overseer.yml"

    # servers group_vars 검증
    servers_vars_file = root_dir / "ansible" / "inventory" / "group_vars" / "servers.yml"
    assert servers_vars_file.exists(), "group_vars/servers.yml is missing"

def test_ansible_playbooks_structure(root_dir):
    """Ansible 플레이북 분리 구조 검증"""
    playbooks_dir = root_dir / "ansible" / "playbooks"
    assert (playbooks_dir / "provision_overseer.yml").exists(), "provision_overseer.yml is missing"
    assert (playbooks_dir / "provision_servers.yml").exists(), "provision_servers.yml is missing"
    assert (playbooks_dir / "provision.yml").exists(), "provision.yml is missing"
    assert (playbooks_dir / "maintenance.yml").exists(), "maintenance.yml is missing"
    assert (playbooks_dir / "site.yml").exists(), "site.yml is missing"

def test_ansible_roles_structure(root_dir):
    """Ansible 신규 역할(docker_engine, overseer_control_plane) 구조 검증"""
    roles_dir = root_dir / "ansible" / "roles"
    expected_roles = ["docker_engine", "overseer_control_plane", "common", "security", "openbao_ssh_ca", "boundary_target", "monitoring"]
    for role in expected_roles:
        assert (roles_dir / role).exists(), f"Role {role} is missing"
        assert (roles_dir / role / "tasks" / "main.yml").exists(), f"Role {role} main task file is missing"

def test_monitoring_otel_system_logs(root_dir):
    """모니터링 역할(monitoring)의 OTel 시스템 로그 수집 경로 검증 (ISMS/ISMS-P 커버리지)"""
    defaults_file = root_dir / "ansible" / "roles" / "monitoring" / "defaults" / "main.yml"
    assert defaults_file.exists(), "monitoring defaults/main.yml is missing"
    with open(defaults_file, 'r', encoding='utf-8') as f:
        defaults = yaml.safe_load(f)

    assert "otel_system_logs" in defaults, "otel_system_logs should be defined in defaults"
    logs = defaults["otel_system_logs"]

    expected_logs = [
        "/var/log/messages",
        "/var/log/syslog",
        "/var/log/secure",
        "/var/log/auth.log",
        "/var/log/sudo.log",
        "/var/log/audit/audit.log",
        "/var/log/cron*",
        "/var/log/fail2ban.log",
        "/var/log/dnf.log",
        "/var/log/yum.log",
        "/var/log/dpkg.log",
        "/var/log/firewalld",
    ]
    for expected in expected_logs:
        assert expected in logs, f"Expected log path {expected} missing from otel_system_logs"

def test_monitoring_node_exporter_removed_and_hostmetrics_enabled(root_dir):
    """Node Exporter 변수 및 설정 제거와 OTel hostmetrics receiver 활성화 상태 검증"""
    defaults_file = root_dir / "ansible" / "roles" / "monitoring" / "defaults" / "main.yml"
    with open(defaults_file, 'r', encoding='utf-8') as f:
        defaults = yaml.safe_load(f)

    assert "node_exporter_version" not in defaults, "node_exporter_version should be completely removed"
    assert "node_exporter_port" not in defaults, "node_exporter_port should be completely removed"
    assert "otel_hostmetrics_interval" in defaults, "otel_hostmetrics_interval should be defined"
    assert "otel_hostmetrics_scrapers" in defaults, "otel_hostmetrics_scrapers should be defined"
    assert "cleanup_legacy_node_exporter" in defaults, "cleanup_legacy_node_exporter should be present"

    # 템플릿 검증
    template_file = root_dir / "ansible" / "roles" / "monitoring" / "templates" / "otelcol-contrib.yaml.j2"
    assert template_file.exists(), "otelcol-contrib template file is missing"
    template_content = template_file.read_text(encoding='utf-8')
    assert "node_exporter" not in template_content, "Template should not contain node_exporter references"
    assert "hostmetrics:" in template_content, "Template must configure hostmetrics receiver"
    assert "traces:" in template_content, "Template must configure traces pipeline"



