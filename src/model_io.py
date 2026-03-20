"""Minimal summary writers for draft model outputs."""

import json
from pathlib import Path

from .logging_utils import get_logger


logger = get_logger(__name__)


def save_model_summary(summary: dict, outpath: str):
    """Save a JSON summary for a draft model."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved model summary JSON to %s", output_path)


def save_model_basic_text(summary: dict, outpath: str):
    """Save a plain text summary for quick inspection."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"model_id: {summary.get('model_id', '')}",
        f"input_path: {summary.get('input_path', '')}",
        f"n_reactions: {summary.get('n_reactions', '')}",
        f"n_metabolites: {summary.get('n_metabolites', '')}",
        f"n_genes: {summary.get('n_genes', '')}",
        f"objective: {summary.get('objective', '')}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved model summary text to %s", output_path)
