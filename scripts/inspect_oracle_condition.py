"""Inspect one ranked oracle-derived debug condition in detail.

This is a draft model debugging step before media optimisation.
"""

import argparse
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.oracle_medium import build_debug_medium_library, screen_debug_media


def _growth_key(row):
    value = row.get("predicted_growth")
    return float("-inf") if value is None else value


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one ranked oracle-derived debug condition."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    parser.add_argument("--condition", required=True, help="Condition name to inspect.")
    parser.add_argument("--biomass-reaction", default="bio2", help="Biomass-like reaction to test.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))
    medium_library = build_debug_medium_library(model, biomass_reaction_id=args.biomass_reaction)
    results = screen_debug_media(model, medium_library, biomass_reaction_id=args.biomass_reaction)
    results = sorted(results, key=_growth_key, reverse=True)

    chosen = None
    for index, row in enumerate(results, start=1):
        if row["condition"] == args.condition:
            chosen = dict(row)
            chosen["rank"] = index
            break

    if chosen is None:
        logger.error("Condition not found: %s", args.condition)
        return 1

    chosen["model_path"] = str(model_path)
    chosen["model_format"] = model_format

    safe_condition = _safe_name(args.condition)
    json_path = model_dir / f"selected_condition_{safe_condition}.json"
    txt_path = model_dir / f"selected_condition_{safe_condition}.txt"
    json_path.write_text(json.dumps(chosen, indent=2), encoding="utf-8")

    lines = [
        "This is a draft model debugging step before media optimisation.",
        f"condition: {chosen['condition']}",
        f"rank: {chosen['rank']}",
        f"description: {chosen.get('description', '')}",
        f"biomass_reaction_id: {chosen.get('biomass_reaction_id', '')}",
        f"predicted_growth: {chosen.get('predicted_growth', '')}",
        f"status: {chosen.get('status', '')}",
        f"n_added_boundaries: {chosen.get('n_added_boundaries', 0)}",
        "ingredients:",
    ]
    for row in chosen.get("metabolite_details", []):
        lines.append(f"{row['metabolite_id']}: {row['metabolite_name']}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("This is a draft model debugging step before media optimisation.")
    print(f"Condition: {chosen['condition']}")
    print(f"Rank: {chosen['rank']}")
    print(f"Description: {chosen.get('description', '')}")
    print(f"Predicted growth: {chosen.get('predicted_growth', None)}")
    print(f"Status: {chosen.get('status', '')}")
    print("Ingredients:")
    for row in chosen.get("metabolite_details", []):
        print(f"{row['metabolite_id']}: {row['metabolite_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
