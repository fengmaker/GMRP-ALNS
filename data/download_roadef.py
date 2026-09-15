"""Download selected official ROADEF 2012 artifacts and record SHA-256 metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = "https://roadef.org/challenge/2012/files"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "a1": ("data_A_first_part", tuple(range(1, 6))),
    "a2": ("data_A_second_part", tuple(range(1, 6))),
    "b": ("dataB", tuple(range(1, 11))),
}
CHECKER_FILES = ("solution_checker.cc", "solution_checker.h", "solution_checker_run.cc")


def _download(url: str, destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return {
        "url": url,
        "path": destination.relative_to(PROJECT_ROOT).as_posix(),
        "bytes": size,
        "sha256": digest.hexdigest(),
        "downloaded_at": datetime.now(UTC).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=[*DATASETS, "checker"])
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "raw" / "roadef")
    parser.add_argument(
        "--manifest-directory", type=Path, default=PROJECT_ROOT / "data" / "manifests"
    )
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    if args.dataset == "checker":
        for filename in CHECKER_FILES:
            records.append(
                _download(
                    f"{BASE_URL}/solution_checker/{filename}",
                    args.output / "checker" / filename,
                )
            )
    else:
        directory, indices = DATASETS[args.dataset]
        for index in indices:
            for prefix in ("model", "assignment"):
                filename = f"{prefix}_{args.dataset}_{index}.txt"
                url = f"{BASE_URL}/{directory}/{filename}"
                destination = args.output / args.dataset / filename
                records.append(_download(url, destination))

    manifest_path = args.manifest_directory / f"roadef_{args.dataset}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"downloaded {len(records)} file(s); manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
