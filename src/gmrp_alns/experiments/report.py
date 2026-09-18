"""Auditable aggregation, paired comparisons, and standalone scientific plots."""

from __future__ import annotations

import csv
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from gmrp_alns.experiments.protocol import digest, identity
from gmrp_alns.experiments.runner import save


def load_records(directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    expected = {row["id"]: row for row in manifest["matrix"]}
    manifest_hash = digest(directory / "manifest.json")
    rows = []
    seen = set()
    paths = sorted((directory / "records").glob("*.json"))
    if paths:
        values = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    else:
        values = [json.loads(line) for line in (directory / "records.jsonl").read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()]
    for row in values:
        signature = row.pop("record_sha256")
        if identity(row) != signature or row["manifest_sha256"] != manifest_hash:
            raise ValueError("corrupt record or mismatched manifest")
        row["record_sha256"] = signature
        run_id = row["id"]
        if run_id not in expected or run_id in seen:
            raise ValueError("unexpected/duplicate run")
        if any(row[key] != value for key, value in expected[run_id].items()):
            raise ValueError("run identity differs from frozen matrix")
        rows.append(row)
        seen.add(run_id)
    for run_id in expected.keys() - seen:
        rows.append({**expected[run_id], "status": "missing"})
    return manifest, sorted(rows, key=lambda row: row["id"])


def improvement(row: dict[str, Any]) -> float:
    return float(100.0 * (row["initial_cost"] - row["best_cost"])
                 / max(1, abs(row["initial_cost"])))


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["instance"], row["method"], row["budget"]].append(row)
    summaries = []
    for (instance, method, budget), group in sorted(groups.items()):
        valid = [r for r in group if r["status"] == "ok" and r.get("official_valid")]
        costs = [r["best_cost"] for r in valid]
        summaries.append({
            "instance": instance, "method": method, "budget": budget,
            "expected": len(group), "valid": len(valid),
            "missing": sum(r["status"] == "missing" for r in group),
            "failures": sum(r["status"] not in ("ok", "missing") for r in group),
            "feasible_rate": len(valid) / len(group),
            "mean_cost": statistics.mean(costs) if costs else None,
            "sd_cost": statistics.stdev(costs) if len(costs) > 1 else None,
            "best_cost": min(costs) if costs else None,
            "worst_cost": max(costs) if costs else None,
            "mean_improvement_percent": statistics.mean(map(improvement, valid)) if valid else None,
            "mean_solver_seconds": statistics.mean(r["solver_seconds"] for r in valid)
            if valid else None,
            "mean_time_to_best": statistics.mean(r["time_to_best_seconds"] for r in valid)
            if valid else None,
            "max_peak_memory_mb": max((r["peak_memory_mb"] for r in valid), default=None),
            "over_budget": sum(not r["within_budget_tolerance"] for r in valid),
        })
    return summaries


def paired(
    rows: list[dict[str, Any]], baseline: str, variant: str,
    instances: list[str],
) -> dict[str, Any]:
    indexed = {(r["instance"], r["seed"], r["budget"], r["method"]): r for r in rows}
    wins = ties = losses = unavailable = 0
    differences = []
    timely = []
    for row in rows:
        if row["method"] != baseline or row["instance"] not in instances:
            continue
        other = indexed.get((row["instance"], row["seed"], row["budget"], variant))
        if other is None or any(r["status"] != "ok" or not r.get("official_valid")
                                for r in (row, other)):
            unavailable += 1
            continue
        delta = row["best_cost"] - other["best_cost"]
        wins += delta > 0
        ties += delta == 0
        losses += delta < 0
        normalized = 100 * delta / max(1, abs(row["initial_cost"]))
        differences.append(normalized)
        if row["within_budget_tolerance"] and other["within_budget_tolerance"]:
            timely.append(normalized)
    return {
        "baseline": baseline, "variant": variant, "instances": instances,
        "wins": wins, "ties": ties, "losses": losses, "unavailable_pairs": unavailable,
        "paired_mean_gain_percentage_points": statistics.mean(differences) if differences else None,
        "both_within_budget_pairs": len(timely),
        "timely_mean_gain_percentage_points": statistics.mean(timely) if timely else None,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def plots(rows: list[dict[str, Any]], output: Path, comparisons: list[dict[str, Any]]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str((output / ".mplconfig").resolve()))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = [r for r in rows if r["status"] == "ok" and r.get("official_valid")]
    methods = sorted({r["method"] for r in valid})
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for method in methods:
        group = [r for r in valid if r["method"] == method]
        axes[0].barh(method, statistics.mean(map(improvement, group)))
        axes[1].barh(method, statistics.mean(r["solver_seconds"] for r in group))
    axes[0].set_xlabel("Mean improvement over initial (%)")
    axes[1].set_xlabel("Measured solver call (seconds)")
    axes[1].axvline(1, color="black", linestyle="--", linewidth=1)
    figure.suptitle("Observed quality and runtime (method subsets differ; see CSV)")
    figure.savefig(output / "quality_runtime.png", dpi=160)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(10, 5), layout="constrained")
    for method in ("relocate", "vnd", "random-lns", "alns", "restricted"):
        group = [r for r in valid if r["method"] == method]
        if not group:
            continue
        grid = [i / 50 for i in range(51)]
        means = []
        for fraction in grid:
            values = []
            for row in group:
                cost = row["initial_cost"]
                for point in row["convergence_trace"]:
                    if point["elapsed_seconds"] <= row["budget"] * fraction:
                        cost = point["best_cost"]
                values.append(100 * (row["initial_cost"] - cost) / max(1, abs(row["initial_cost"])))
            means.append(statistics.mean(values))
        axis.plot(grid, means, label=method)
    axis.set(xlabel="Fraction of requested search budget", ylabel="Mean improvement (%)",
             title="Best-so-far observation times; final results may arrive after budget")
    axis.legend()
    figure.savefig(output / "convergence.png", dpi=160)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(10, 5), layout="constrained")
    values = [p for p in comparisons if p["paired_mean_gain_percentage_points"] is not None]
    axis.barh([p["variant"] for p in values],
              [p["paired_mean_gain_percentage_points"] for p in values])
    axis.axvline(0, color="black", linewidth=1)
    axis.set(xlabel="Variant gain over ALNS (percentage points of initial cost)",
             title="Paired ablations; all returned valid results, including overruns")
    figure.savefig(output / "ablations.png", dpi=160)
    plt.close(figure)


def report(directory: Path, output: Path) -> None:
    manifest, rows = load_records(directory)
    output.mkdir(parents=True, exist_ok=True)
    summaries = summarize(rows)
    config = manifest["config"]
    comparisons = [paired(rows, "alns", method, config["ablation_instances"])
                   for method in ["restricted", *config["ablation_methods"]]]
    heldout = paired(rows, "alns", "restricted", config.get("heldout_instances", []))
    save(output / "summary.json", summaries)
    save(output / "paired.json", {"ablations": comparisons, "heldout": heldout})
    write_csv(output / "summary.csv", summaries)
    operators = []
    for row in rows:
        for name, stats in row.get("operator_stats", {}).items():
            operators.append({"run_id": row["id"], "instance": row["instance"],
                              "method": row["method"], "operator": name,
                              "calls": stats["calls"], "seconds": stats["wall_time_seconds"],
                              "improvement": stats["total_improvement"]})
    write_csv(output / "operators.csv", operators)
    completed = [r for r in rows if r["status"] != "missing"]
    (output / "records.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in completed), encoding="utf-8"
    )
    # Preserve manifest bytes because their digest is part of every raw record identity.
    (output / "manifest.json").write_bytes((directory / "manifest.json").read_bytes())
    plots(rows, output, comparisons)
    lines = ["# M7 generated results", "", f"Source commit: `{manifest['git_commit']}`.", "",
             f"Expected {len(rows)} runs; recorded {len(completed)}; "
             f"official-valid {sum(r.get('official_valid', False) for r in rows)}.", "",
             "All statistics use valid returned results; overruns remain visible. "
             "Initial repeats are deterministic controls, not independent stochastic evidence.", "",
             "| Instance | Method | n/expected | Mean cost | SD | Improvement % | Overruns |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for s in summaries:
        def fmt(value: Any) -> str:
            return "NA" if value is None else f"{value:,.3f}"
        lines.append(f"| {s['instance']} | {s['method']} | {s['valid']}/{s['expected']} | "
                     f"{fmt(s['mean_cost'])} | {fmt(s['sd_cost'])} | "
                     f"{fmt(s['mean_improvement_percent'])} | {s['over_budget']} |")
    lines += ["", "## Paired ablations", "",
              "Positive gain favors the variant. Pairs use the same instance, seed and budget.", "",
              "| Variant | Wins/ties/losses | Missing/failed | Mean gain (pp) | Timely pairs |",
              "|---|---:|---:|---:|---:|"]
    for p in comparisons:
        lines.append(f"| {p['variant']} | {p['wins']}/{p['ties']}/{p['losses']} | "
                     f"{p['unavailable_pairs']} | {fmt(p['paired_mean_gain_percentage_points'])} | "
                     f"{p['both_within_budget_pairs']} |")
    lines += ["", "![Quality and time](quality_runtime.png)", "",
              "![Convergence](convergence.png)", "", "![Ablations](ablations.png)", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    save(output / "checksums.json", {
        p.name: digest(p) for p in sorted(output.iterdir())
        if p.is_file() and p.name != "checksums.json"
    })
    print(f"Generated report for {len(completed)}/{len(rows)} runs in {output}")
