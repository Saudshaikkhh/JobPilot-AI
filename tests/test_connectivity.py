"""
Deduplicated placeholder connectivity test.
Connectivity checks are run via standalone script: tests/run_connectivity_check.py
"""

def test_connectivity_check_script_exists():
    import os
    assert os.path.exists("tests/run_connectivity_check.py")
