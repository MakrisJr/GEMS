"""Output helpers for oracle-derived rich debug medium screening.

This is a draft model debugging step before media optimisation.
"""

import json
from pathlib import Path

import pandas as pd

from .logging_utils import get_logger
from .plot_utils import PALETTE, save_ranked_barh_plot


logger = get_logger(__name__)


def save_oracle_medium_results(results, outdir: str):
    """Save ranked oracle-medium screen results."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataframe = pd.DataFrame(results)
    dataframe.to_csv(output_dir / "oracle_medium_screen.csv", index=False)
    (output_dir / "oracle_medium_screen.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )

    lines = ["This is a draft model debugging step before media optimisation."]
    if results:
        best = results[0]
        lines.append(f"best_condition: {best.get('condition', '')}")
        lines.append(f"best_predicted_growth: {best.get('predicted_growth', '')}")
    for row in results:
        lines.append(
            f"{row['condition']}: growth={row['predicted_growth']}, status={row['status']}, n_added_boundaries={row['n_added_boundaries']}"
        )

    (output_dir / "oracle_medium_screen.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    logger.info("Saved oracle-medium screening results to %s", output_dir)


def save_oracle_medium_plot(results, outdir: str):
    """Save a bar plot for oracle-derived debug media."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = [row["condition"] for row in results]
    values = [0.0 if row["predicted_growth"] is None else row["predicted_growth"] for row in results]
    colors = [PALETTE["debug"]] + [PALETTE["preset_alt"]] * max(0, len(conditions) - 1)
    save_ranked_barh_plot(
        conditions,
        values,
        outpath=output_dir / "oracle_medium_screen.png",
        title="Semi-artificial rich debug media on a draft model",
        xlabel="Predicted bio2 flux",
        colors=colors,
        subtitle="These debug conditions help show which internal precursor sets can rescue biomass-like flux.",
    )
    logger.info("Saved oracle-medium screening plot to %s", output_dir / "oracle_medium_screen.png")
