"""Output helpers for minimal bio2 benchmarking.

This is a draft model debugging step before media optimisation.
The reported yield is a debug proxy based on total added boundary flux.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .logging_utils import get_logger
from .plot_utils import PALETTE, annotate_barh, finalize_figure, style_axis, wrap_label


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

    wrapped_conditions = [wrap_label(condition) for condition in conditions]
    figure_height = max(4.8, len(conditions) * 0.6 + 1.8)
    figure, axes = plt.subplots(
        1,
        2,
        figsize=(13, figure_height),
        sharey=True,
        gridspec_kw={"width_ratios": [1.15, 1.0]},
    )
    colors = [PALETTE["debug"]] + [PALETTE["preset_alt"]] * max(0, len(conditions) - 1)

    rate_bars = axes[0].barh(
        range(len(conditions)),
        rates,
        color=colors,
        edgecolor="#FFFDFC",
        linewidth=1.2,
        height=0.68,
    )
    style_axis(axes[0], grid_axis="x")
    axes[0].set_yticks(range(len(conditions)), wrapped_conditions)
    axes[0].invert_yaxis()
    axes[0].set_title("bio2 rate", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Flux")
    max_rate = max(rates) if rates else 0.0
    axes[0].set_xlim(0.0, max(1.0, max_rate * 1.16))
    annotate_barh(axes[0], rate_bars, rates)

    yield_bars = axes[1].barh(
        range(len(conditions)),
        yields,
        color=colors,
        edgecolor="#FFFDFC",
        linewidth=1.2,
        height=0.68,
    )
    style_axis(axes[1], grid_axis="x")
    axes[1].set_title("bio2 yield proxy", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("bio2 / total added flux")
    axes[1].tick_params(axis="y", labelleft=False)
    max_yield = max(yields) if yields else 0.0
    axes[1].set_xlim(0.0, max(0.01, max_yield * 1.16 if max_yield > 0 else 0.01))
    annotate_barh(axes[1], yield_bars, yields)

    figure.suptitle(
        "First-pass bio2 benchmarking on a draft model",
        fontsize=14,
        fontweight="bold",
    )
    finalize_figure(figure, output_dir / "bio2_benchmark.png")
    logger.info("Saved bio2 benchmark plot to %s", output_dir / "bio2_benchmark.png")
