"""Minimal output writers for the first-pass media screen.

This is a first-pass media screen on a draft model.
"""

import json
from pathlib import Path

import pandas as pd

from .logging_utils import get_logger
from .plot_utils import PALETTE, save_ranked_barh_plot
from .report_utils import make_report, make_section


logger = get_logger(__name__)


def save_media_results(results, outdir: str):
    """Save media screening results as CSV, JSON, and text."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataframe = pd.DataFrame(results)
    dataframe.to_csv(output_dir / "media_screen.csv", index=False)
    (output_dir / "media_screen.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )

    summary_lines = ["First-pass condition comparison on a draft model."]
    if results:
        best = results[0]
        summary_lines.extend(
            [
                f"Best condition: {best.get('condition', '')}",
                f"Best predicted growth: {best.get('predicted_growth', '')}",
            ]
        )
    ranking_lines = []
    for row in results:
        ranking_lines.append(
            f"{row['condition']}: growth={row['predicted_growth']}, status={row['status']}, missing_exchange_ids={row['missing_exchange_ids']}"
        )

    (output_dir / "media_screen.txt").write_text(
        make_report(
            "Media Screen Report",
            [
                make_section("Summary", summary_lines),
                make_section("Ranked Conditions", ranking_lines),
            ],
        ),
        encoding="utf-8",
    )
    logger.info("Saved media screening results to %s", output_dir)


def save_media_plot(results, outdir: str):
    """Save a simple bar plot of predicted growth by condition."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = [row["condition"] for row in results]
    values = [0.0 if row["predicted_growth"] is None else row["predicted_growth"] for row in results]
    colors = [PALETTE["media"]] + [PALETTE["preset_alt"]] * max(0, len(conditions) - 1)
    save_ranked_barh_plot(
        conditions,
        values,
        outpath=output_dir / "media_screen.png",
        title="First-pass media screen on a draft model",
        xlabel="Predicted growth",
        colors=colors,
        subtitle="This is an early screen on a draft model, so flat or zero results are still informative.",
    )
    logger.info("Saved media screening plot to %s", output_dir / "media_screen.png")
