"""Minimal COBRApy media screening for a draft model.

This is a first-pass media screen on a draft model.
"""

from pathlib import Path

import yaml


def load_media_library(path: str):
    """Load a tiny YAML media library."""
    library_path = Path(path)
    with library_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def apply_medium(model, bounds: dict):
    """Apply medium bounds by reassigning the full medium dictionary."""
    medium = dict(model.medium)
    exchange_ids = {reaction.id for reaction in model.exchanges}
    missing_exchange_ids = []

    for exchange_id, value in bounds.items():
        if exchange_id in exchange_ids:
            medium[exchange_id] = float(value)
        else:
            missing_exchange_ids.append(exchange_id)

    model.medium = medium
    return missing_exchange_ids


def screen_media(model, media_library):
    """Screen a few candidate media conditions with slim_optimize."""
    results = []

    for condition, config in media_library.items():
        model_copy = model.copy()
        bounds = config.get("bounds", {})
        description = config.get("description", "")
        missing_exchange_ids = apply_medium(model_copy, bounds)

        try:
            predicted_growth = model_copy.slim_optimize()
            status = model_copy.solver.status or "unknown"
            if predicted_growth != predicted_growth:
                predicted_growth = None
        except Exception:
            predicted_growth = None
            status = "failed"

        results.append(
            {
                "condition": condition,
                "description": description,
                "predicted_growth": predicted_growth,
                "status": status,
                "missing_exchange_ids": missing_exchange_ids,
            }
        )

    return results
