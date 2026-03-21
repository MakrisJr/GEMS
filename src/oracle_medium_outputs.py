"""Output helpers for oracle-derived rich debug medium screening.

This is a draft model debugging step before media optimisation.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .logging_utils import get_logger


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

    plt.figure(figsize=(10, 4.5))
    plt.bar(conditions, values)
    plt.ylabel("Predicted bio2 flux")
    plt.xlabel("Debug Condition")
    plt.title("Semi-artificial rich debug media on a draft model")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "oracle_medium_screen.png", dpi=150)
    plt.close()
    logger.info("Saved oracle-medium screening plot to %s", output_dir / "oracle_medium_screen.png")
