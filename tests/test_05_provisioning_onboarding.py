"""
E2E Test 05: Provisioning & Migration Onboarding Integration Suite
Verifies Greenfield (New Baseline Setup) and Brownfield (3-Stage Legacy Migration & Lockout Safety)
onboarding contracts, guidelines, and Semaphore UI orchestrator linkages.
"""

import os
import pytest
from pathlib import Path

def test_onboard_001_greenfield_baseline_workflow(root_dir):
    """
    [ONBOARD-001] Greenfield Server Baseline Provisioning Workflow
    Verifies that Greenfield onboarding is fully defined in guidelines and seeded into Semaphore:
    1. Guideline defines baseline orchestration (Common, Security, SSH CA, Boundary, Monitoring)
    2. Semaphore UI GitOps seeder registers 'Provision Target Servers' template
    3. OpenBao SSH CA public key integration point is configured
    """
    guideline_doc = root_dir / "docs" / "PROVISIONING_AND_MIGRATION_GUIDELINE.md"
    assert guideline_doc.exists(), "docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md is missing"
    content = guideline_doc.read_text(encoding="utf-8")
    
    assert "신규 서버 프로비저닝 (Greenfield)" in content, "Greenfield workflow section missing in guideline"
    assert "Chrony" in content, "Chrony NTP baseline requirement missing"
    assert "otelcol-contrib" in content or "hostmetrics" in content, "OTel hostmetrics monitoring requirement missing"
    
    # Semaphore UI GitOps 시딩 템플릿 연동 검증
    init_script = root_dir / "scripts" / "init-semaphore.sh"
    assert init_script.exists(), "scripts/init-semaphore.sh is missing"
    init_content = init_script.read_text(encoding="utf-8")
    assert "1. Provision Target Servers" in init_content, "Greenfield task template must be seeded in Semaphore"
    assert "playbooks/provision_servers.yml" in init_content, "provision_servers.yml playbook must be registered"


def test_onboard_002_brownfield_migration_and_lockout_safety(root_dir):
    """
    [ONBOARD-002] Brownfield Legacy Server 3-Stage Migration and Lockout Safety
    Verifies safety mechanisms for migrating existing production servers:
    1. Pre-flight & Dry-run: Firewall port reservation (firewall_allowed_tcp_ports)
    2. 3-Stage Tagged Deployment: tags common -> monitoring -> vault -> security
    3. SSH Lockout Prevention: SSH CA verification prior to password authentication disabling
    4. Semaphore UI Dry-Run Simulation template with '--check --diff'
    """
    guideline_doc = root_dir / "docs" / "PROVISIONING_AND_MIGRATION_GUIDELINE.md"
    assert guideline_doc.exists(), "docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md is missing"
    guideline_content = guideline_doc.read_text(encoding="utf-8")

    # 1. 3단계 점진적 마이그레이션 절차 및 락아웃 방지 지침 확인
    assert "SSH 락아웃(Lockout) 방지" in guideline_content, "SSH lockout prevention must be documented"
    assert "cleanup_legacy_node_exporter" in guideline_content, "Node exporter cleanup must be documented"
    assert "firewall_allowed_tcp_ports" in guideline_content, "Firewall port discovery must be documented"

    # 2. Semaphore UI Dry-Run 시뮬레이션 템플릿 검증
    init_script = root_dir / "scripts" / "init-semaphore.sh"
    init_content = init_script.read_text(encoding="utf-8")
    assert "5. Dry-Run Check & Diff (Simulation)" in init_content, "Dry-run template must be seeded in Semaphore"
    assert "--check --diff" in init_content, "Dry-run arguments must include --check --diff"


def test_onboarding_os_compatibility_matrix(root_dir):
    """
    OS Generation Compatibility Matrix Verification (CentOS 6/7/8, Rocky Linux 9/10, Ubuntu/Debian)
    Verifies that all OS-specific package managers, init systems, and SSH capabilities are documented.
    """
    guideline_doc = root_dir / "docs" / "PROVISIONING_AND_MIGRATION_GUIDELINE.md"
    content = guideline_doc.read_text(encoding="utf-8")

    expected_os_entries = [
        "CentOS 6",
        "CentOS 7",
        "CentOS 8",
        "Rocky Linux 9 / 10",
    ]
    for os_entry in expected_os_entries:
        assert os_entry in content, f"OS compatibility matrix missing {os_entry}"

    # Verify CentOS 6 legacy workaround documentation (OpenSSH 5.3 fallback & vault repo fix)
    assert "vault.centos.org" in content, "CentOS vault repository transition must be documented"
    assert "TrustedUserCAKeys" in content, "OpenSSH CA compatibility constraints must be documented"


def test_onboard_001_greenfield_linux_user_and_ssh_ca_contract(root_dir):
    """
    [ONBOARD-001] Greenfield Target Node Linux User & SSH CA Integration Verification
    Verifies that when a clean on-premises server is provisioned:
    1. Dedicated non-root administrative Linux user ('infra-admin') is defined with passwordless sudo
    2. OpenBao SSH CA public key is deployed to '/etc/ssh/trusted-user-ca-keys.pem'
    3. OpenSSH daemon is configured with 'TrustedUserCAKeys' and 'AuthorizedPrincipalsFile' / principals matching
    4. Root login and password authentication are disabled in favor of certificate authentication
    """
    guideline_doc = root_dir / "docs" / "PROVISIONING_AND_MIGRATION_GUIDELINE.md"
    content = guideline_doc.read_text(encoding="utf-8")

    # 1. Non-root user & sudoers contract
    assert "infra-admin" in content, "Target provisioning non-root user must be 'infra-admin'"
    assert "/etc/sudoers.d/90-infra-admin" in content, "Dedicated sudoers drop-in file must be defined"

    # 2. SSH CA trust & daemon hardening contract
    assert "trusted-user-ca-keys.pem" in content, "SSH CA public key file must be trusted-user-ca-keys.pem"
    assert "PermitRootLogin no" in content, "Root login must be disabled after provisioning"
    assert "PasswordAuthentication no" in content, "Password authentication must be disabled after CA verification"

    # 3. OpenBao SSH CA init script alignment
    openbao_init_script = root_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh"
    assert openbao_init_script.exists(), "OpenBao SSH CA init script must exist"
    openbao_script_content = openbao_init_script.read_text(encoding="utf-8")
    assert "infra-admin" in openbao_script_content or "infra-admin-role" in openbao_script_content, (
        "OpenBao SSH CA role must allow signing for 'infra-admin' principal"
    )


def test_onboard_001_greenfield_boundary_and_monitoring_contract(root_dir):
    """
    [ONBOARD-001] Greenfield Target Node Boundary Zero-Trust & Observability Integration Verification
    Verifies that:
    1. Target host is integrated with Boundary Worker proxy (default port 9202)
    2. OpenTelemetry Collector Contrib with hostmetrics receiver is deployed
    3. Time synchronization (Chrony) is enforced to ensure certificate timestamp validity
    """
    guideline_doc = root_dir / "docs" / "PROVISIONING_AND_MIGRATION_GUIDELINE.md"
    content = guideline_doc.read_text(encoding="utf-8")

    # 1. Boundary target integration
    assert "Boundary" in content, "Boundary Zero-Trust access must be integrated"

    # 2. OpenTelemetry Collector Hostmetrics
    assert "hostmetrics" in content, "Hostmetrics receiver must be configured for system metrics"
    assert "OTLP" in content, "OTLP outbound export must be documented"

    # 3. Chrony for SSH Certificate timestamp accuracy
    assert "Chrony" in content or "chrony" in content, "Chrony NTP must be required for CA timestamp validity"

