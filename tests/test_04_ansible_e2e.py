"""
E2E Test 04: Ansible Inventory & Prometheus Integration Validation
Verifies that Ansible configuration, inventory definitions, and monitoring scrape targets are properly wired.
"""

import yaml
import pytest
from pathlib import Path

def test_ansible_inventory_and_vars(root_dir):
    """Ansible 인벤토리 및 group_vars 파일 유효성 검증"""
    inv_file = root_dir / "ansible" / "inventory" / "hosts.yml"
    assert inv_file.exists(), "Inventory file hosts.yml is missing"
    
    with open(inv_file, 'r', encoding='utf-8') as f:
        inv_data = yaml.safe_load(f)
    assert "all" in inv_data, "Inventory missing root 'all' key"
    
    # group_vars 검증
    all_vars_file = root_dir / "ansible" / "inventory" / "group_vars" / "all.yml"
    assert all_vars_file.exists(), "group_vars/all.yml is missing"
    with open(all_vars_file, 'r', encoding='utf-8') as f:
        all_vars = yaml.safe_load(f)
    assert "admin_user" in all_vars, "admin_user is not defined in all.yml"
    assert "timezone" in all_vars, "timezone is not defined in all.yml"

def test_prom_ctrl_002_scrape_targets(root_dir, http_session, prometheus_url):
    """[PROM-CTRL-002] Prometheus Control Plane and Node Scrape Config wiring"""
    prom_cfg_file = root_dir / "prometheus" / "prometheus.yml"
    assert prom_cfg_file.exists(), "prometheus.yml is missing"
    
    with open(prom_cfg_file, 'r', encoding='utf-8') as f:
        prom_data = yaml.safe_load(f)
    
    job_names = [job.get("job_name") for job in prom_data.get("scrape_configs", [])]
    assert "overseer-control-plane" in job_names, "Missing overseer-control-plane job in Prometheus config"
    assert "idc-node-exporters" in job_names, "Missing idc-node-exporters job in Prometheus config"
