"""Minimal output writers for COBRApy inspection.

This is a draft model inspection step before media optimisation.
"""

import csv
import json
from pathlib import Path

from .logging_utils import get_logger


logger = get_logger(__name__)


def save_model_overview(summary: dict, outpath: str):
    """Save a small JSON overview for the loaded model."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved model overview to %s", output_path)


def save_exchange_table(exchange_table, outpath: str):
    """Save exchange reactions to CSV using pandas if available, otherwise csv."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(exchange_table, "to_csv"):
        exchange_table.to_csv(output_path, index=False)
    else:
        rows = list(exchange_table)
        fieldnames = ["reaction_id", "reaction", "lower_bound", "upper_bound"]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    logger.info("Saved exchanges table to %s", output_path)


def save_baseline_result(result: dict, outpath: str):
    """Save a small JSON result for the baseline optimization."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("Saved baseline optimization result to %s", output_path)


def save_cobra_inspection_text(summary: dict, result: dict, outpath: str):
    """Save a short human-readable COBRA inspection summary."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "This is a draft model inspection step before media optimisation.",
        f"n_reactions: {summary.get('n_reactions', '')}",
        f"n_metabolites: {summary.get('n_metabolites', '')}",
        f"n_genes: {summary.get('n_genes', '')}",
        f"n_exchanges: {summary.get('n_exchanges', '')}",
        f"objective: {summary.get('objective', '')}",
        f"optimization_status: {result.get('status', '')}",
        f"objective_value: {result.get('objective_value', '')}",
        f"error_message: {result.get('error_message', '')}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved COBRA inspection text to %s", output_path)
