"""
E2E Test 00: 3-Way Specification & Traceability Verification Test
Executes the root 3-way validator to assert 100% consistency across Docs, Code, and Tests.
"""

import subprocess
import pytest
from pathlib import Path

def test_full_stack_3way_traceability(root_dir):
    """문서(Docs) ⟷ 코드(Code) ⟷ 테스트(Tests) 3단 정합성 100% 검증"""
    script_path = root_dir / "scripts" / "validate-specs.py"
    assert script_path.exists(), "validate-specs.py script is missing"
    
    result = subprocess.run(
        [str(script_path)],
        cwd=str(root_dir),
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"3-Way Traceability Validation failed:\n{result.stdout}\n{result.stderr}"
    assert "ROOT 3-WAY TRACEABILITY VALIDATION PASSED" in result.stdout
