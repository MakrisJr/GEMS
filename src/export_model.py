"""Minimal export helpers for draft models and gapfill summaries.

This is still a draft model. Gapfilling is a best-effort step in this
minimal version.
"""

import json
import os
import tempfile
from pathlib import Path

from .logging_utils import get_logger


os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from cobra.io import save_json_model, write_sbml_model


logger = get_logger(__name__)


def _fallback_model_payload(model, error_message: str) -> dict:
    objective = ""
    expression = getattr(getattr(model, "objective", None), "expression", None)
    if expression is not None:
        objective = str(expression)

    return {
        "export_type": "fallback_summary",
        "error_message": error_message,
        "model_id": getattr(model, "id", ""),
        "n_reactions": len(getattr(model, "reactions", [])),
        "n_metabolites": len(getattr(model, "metabolites", [])),
        "n_genes": len(getattr(model, "genes", [])),
        "objective": objective,
    }


def save_model_json_if_possible(model, outpath: str):
    """Save a COBRA JSON model, or a fallback summary JSON if export fails."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        save_json_model(model, str(output_path))
        logger.info("Saved model JSON to %s", output_path)
        return True
    except Exception as exc:
        payload = _fallback_model_payload(model, str(exc))
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.warning("Model JSON export failed; saved fallback summary JSON to %s", output_path)
        return False


def save_model_sbml_if_possible(model, outpath: str):
    """Save a COBRA SBML model if possible."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        write_sbml_model(model, str(output_path))
        logger.info("Saved model SBML to %s", output_path)
        return True
    except Exception as exc:
        logger.warning("Model SBML export failed: %s", exc)
        return False


def save_gapfill_summary(summary: dict, outpath: str):
    """Save gapfill summary JSON and a matching human-readable text file."""
    output_path = Path(outpath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved gapfill summary JSON to %s", output_path)

    text_path = output_path.with_suffix(".txt")
    lines = [
        "This is still a draft model. Gapfilling is a best-effort step in this minimal version.",
        f"gapfill_attempted: {summary.get('gapfill_attempted', False)}",
        f"gapfill_success: {summary.get('gapfill_success', False)}",
        f"error_message: {summary.get('error_message', '')}",
        f"reactions_before: {summary.get('reactions_before', '')}",
        f"reactions_after: {summary.get('reactions_after', '')}",
        f"metabolites_before: {summary.get('metabolites_before', '')}",
        f"metabolites_after: {summary.get('metabolites_after', '')}",
        f"genes_before: {summary.get('genes_before', '')}",
        f"genes_after: {summary.get('genes_after', '')}",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved gapfill summary text to %s", text_path)
