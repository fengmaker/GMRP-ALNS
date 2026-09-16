"""Download official OR-Library GAP files and record provenance metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS: dict[str, dict[str, object]] = {
    "gap1": {
        "sense": "maximize",
        "reference_values": [336, 327, 339, 341, 326],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=sorted(DATASETS))
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "raw" / "orlib")
    parser.add_argument(
        "--manifest-directory", type=Path, default=PROJECT_ROOT / "data" / "manifests"
    )
    args = parser.parse_args()

    filename = f"{args.dataset}.txt"
    url = f"{BASE_URL}/{filename}"
    destination = args.output / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
            size += len(chunk)

    manifest = {
        "dataset": args.dataset,
        **DATASETS[args.dataset],
        "source_format": "OR-Library GAP multi-instance integer stream",
        "file": {
            "url": url,
            "path": destination.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": size,
            "sha256": digest.hexdigest(),
            "downloaded_at": datetime.now(UTC).isoformat(),
        },
    }
    manifest_path = args.manifest_directory / f"orlib_{args.dataset}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"downloaded {filename}; manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
