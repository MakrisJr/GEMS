"""Minimal output writers for the first-pass media screen.

This is a first-pass media screen on a draft model.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .logging_utils import get_logger


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

    lines = ["This is a first-pass media screen on a draft model."]
    if results:
        best = results[0]
        lines.append(f"best_condition: {best.get('condition', '')}")
        lines.append(f"best_predicted_growth: {best.get('predicted_growth', '')}")
    for row in results:
        lines.append(
            f"{row['condition']}: growth={row['predicted_growth']}, status={row['status']}, missing_exchange_ids={row['missing_exchange_ids']}"
        )

    (output_dir / "media_screen.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved media screening results to %s", output_dir)


def save_media_plot(results, outdir: str):
    """Save a simple bar plot of predicted growth by condition."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = [row["condition"] for row in results]
    values = [0.0 if row["predicted_growth"] is None else row["predicted_growth"] for row in results]

    plt.figure(figsize=(8, 4))
    plt.bar(conditions, values)
    plt.ylabel("Predicted Growth")
    plt.xlabel("Condition")
    plt.title("First-pass media screen on a draft model")
    plt.tight_layout()
    plt.savefig(output_dir / "media_screen.png", dpi=150)
    plt.close()
    logger.info("Saved media screening plot to %s", output_dir / "media_screen.png")
