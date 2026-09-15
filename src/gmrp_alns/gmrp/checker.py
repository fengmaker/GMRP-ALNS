"""Adapter for cross-checking with the unmodified official executable."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CheckerResult:
    returncode: int
    stdout: str
    stderr: str


def run_official_checker(
    executable: str | Path,
    model: str | Path,
    original: str | Path,
    solution: str | Path,
    *,
    timeout_seconds: float = 30.0,
) -> CheckerResult:
    """Run the official checker as an external process without interpreting its output."""
    completed = subprocess.run(
        [str(executable), str(model), str(original), str(solution)],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return CheckerResult(completed.returncode, completed.stdout, completed.stderr)

