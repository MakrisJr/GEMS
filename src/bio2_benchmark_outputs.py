"""Output helpers for minimal bio2 benchmarking.

This is a draft model debugging step before media optimisation.
The reported yield is a debug proxy based on total added boundary flux.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .logging_utils import get_logger


logger = get_logger(__name__)


def _table_rows(results):
    rows = []
    for row in results:
        rows.append(
            {
                "condition": row.get("condition", ""),
                "description": row.get("description", ""),
                "biomass_reaction_id": row.get("biomass_reaction_id", ""),
                "bio2_rate": row.get("bio2_rate"),
                "bio2_yield_on_total_added_flux": row.get("bio2_yield_on_total_added_flux"),
                "total_added_boundary_flux": row.get("total_added_boundary_flux"),
                "status": row.get("status", ""),
                "n_added_boundaries": row.get("n_added_boundaries", 0),
            }
        )
    return rows


def save_bio2_benchmark_results(results, outdir: str):
    """Save bio2 benchmark results as JSON, CSV, and text."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    table_rows = _table_rows(results)
    pd.DataFrame(table_rows).to_csv(output_dir / "bio2_benchmark.csv", index=False)
    (output_dir / "bio2_benchmark.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )

    lines = [
        "This is a draft model debugging step before media optimisation.",
        "The reported yield is a debug proxy based on total added boundary flux.",
    ]
    if results:
        best = results[0]
        lines.append(f"best_condition: {best.get('condition', '')}")
        lines.append(f"best_bio2_rate: {best.get('bio2_rate', '')}")
        lines.append(
            "best_bio2_yield_on_total_added_flux: "
            f"{best.get('bio2_yield_on_total_added_flux', '')}"
        )
    for row in table_rows:
        lines.append(
            f"{row['condition']}: rate={row['bio2_rate']}, yield={row['bio2_yield_on_total_added_flux']}, status={row['status']}"
        )

    (output_dir / "bio2_benchmark.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved bio2 benchmark results to %s", output_dir)


def save_bio2_benchmark_plot(results, outdir: str):
    """Save a simple comparison plot for bio2 rate and yield."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = [row.get("condition", "") for row in results]
    rates = [0.0 if row.get("bio2_rate") is None else row.get("bio2_rate") for row in results]
    yields = [
        0.0
        if row.get("bio2_yield_on_total_added_flux") is None
        else row.get("bio2_yield_on_total_added_flux")
        for row in results
    ]

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].bar(conditions, rates)
    axes[0].set_title("bio2 rate")
    axes[0].set_ylabel("Flux")
    axes[0].set_xlabel("Condition")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(conditions, yields)
    axes[1].set_title("bio2 yield proxy")
    axes[1].set_ylabel("bio2 / total added flux")
    axes[1].set_xlabel("Condition")
    axes[1].tick_params(axis="x", rotation=20)

    figure.suptitle("First-pass bio2 benchmarking on a draft model")
    figure.tight_layout()
    figure.savefig(output_dir / "bio2_benchmark.png", dpi=150)
    plt.close(figure)
    logger.info("Saved bio2 benchmark plot to %s", output_dir / "bio2_benchmark.png")
