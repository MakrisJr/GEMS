"""Run an oracle-growth debug optimization on the exported draft model.

This is a draft model debugging step before media optimisation.
"""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.oracle_growth import run_oracle_growth


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an oracle-growth debug optimization on the draft model."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    parser.add_argument("--biomass-reaction", default="bio2", help="Biomass-like reaction to test.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))
    result = run_oracle_growth(model, biomass_reaction_id=args.biomass_reaction)
    result["model_path"] = str(model_path)
    result["model_format"] = model_format

    json_path = model_dir / "oracle_growth.json"
    txt_path = model_dir / "oracle_growth.txt"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "This is a draft model debugging step before media optimisation.",
        f"model_path: {model_path}",
        f"model_format: {model_format}",
        f"biomass_reaction_id: {result['biomass_reaction_id']}",
        f"biomass_reaction: {result['biomass_reaction']}",
        f"status: {result['status']}",
        f"objective_value: {result['objective_value']}",
        f"n_added_boundaries: {result['n_added_boundaries']}",
        "added_boundaries:",
    ]
    for row in result["added_boundaries"]:
        lines.append(
            f"{row['boundary_id']}: {row['metabolite_id']} ({row['metabolite_name']}) [{row['lower_bound']}, {row['upper_bound']}]"
        )
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("This is a draft model debugging step before media optimisation.")
    print(f"Model path: {model_path}")
    print(f"Biomass reaction: {result['biomass_reaction_id']}")
    print(f"Status: {result['status']}")
    print(f"Objective value: {result['objective_value']}")
    print(f"Added boundaries: {result['n_added_boundaries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
