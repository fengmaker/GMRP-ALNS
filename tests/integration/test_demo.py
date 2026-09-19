from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_release_demo_runs_offline() -> None:
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, str(root / "scripts" / "demo.py")],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {
        "status": "ok",
        "gmrp_dimensions": {
            "resources": 2,
            "machines": 4,
            "services": 2,
            "processes": 3,
        },
        "gmrp_reference_cost": 2411,
        "gmrp_search_cost": 2411,
        "gmrp_candidate_revalidated": True,
        "gap_reference_cost": 8,
        "gap_optimal": True,
        "seed": 42,
        "max_iterations": 20,
    }
