"""Minimal debugging CLI for draft-model growth checks."""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_debug import (
    inspect_candidate_biomass_reactions,
    inspect_objective,
    inspect_open_medium,
    run_debug_optimization,
)
from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug objective, medium, and feasibility for a draft COBRA model.")
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))
    objective = inspect_objective(model)
    open_medium = inspect_open_medium(model)
    biomass_candidates = inspect_candidate_biomass_reactions(model)

    try:
        optimization = run_debug_optimization(model)
    except Exception as exc:
        optimization = {
            "status": "failed",
            "objective_value": None,
            "error_message": str(exc),
        }

    first_20_exchanges = [
        {
            "reaction_id": reaction.id,
            "reaction": reaction.reaction,
            "lower_bound": reaction.lower_bound,
            "upper_bound": reaction.upper_bound,
        }
        for reaction in list(model.exchanges)[:20]
    ]

    report = {
        "model_path": str(model_path),
        "model_format": model_format,
        "objective": objective,
        "optimization": optimization,
        "n_exchanges": len(model.exchanges),
        "first_20_exchanges": first_20_exchanges,
        "candidate_biomass_reactions": biomass_candidates,
        "open_medium": open_medium,
    }

    json_path = model_dir / "debug_growth.json"
    txt_path = model_dir / "debug_growth.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        f"model_path: {model_path}",
        f"model_format: {model_format}",
        f"current_objective: {objective}",
        f"optimization_status: {optimization.get('status', '')}",
        f"objective_value: {optimization.get('objective_value', '')}",
        f"number_of_exchanges: {len(model.exchanges)}",
        "first_20_exchanges:",
    ]
    for row in first_20_exchanges:
        lines.append(
            f"{row['reaction_id']}: {row['reaction']} [{row['lower_bound']}, {row['upper_bound']}]"
        )
    lines.append("candidate_biomass_reactions:")
    for row in biomass_candidates:
        lines.append(
            f"{row['reaction_id']}: {row['reaction']} [{row['lower_bound']}, {row['upper_bound']}]"
        )
    lines.append("currently_open_medium_entries:")
    for exchange_id, value in open_medium.items():
        lines.append(f"{exchange_id}: {value}")
    if "error_message" in optimization:
        lines.append(f"error_message: {optimization['error_message']}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Current objective: {objective}")
    print(f"Optimization status: {optimization.get('status', '')}")
    print(f"Objective value: {optimization.get('objective_value', None)}")
    print(f"Number of exchanges: {len(model.exchanges)}")
    print("First 20 exchanges:")
    for row in first_20_exchanges:
        print(f"{row['reaction_id']}: {row['reaction']} [{row['lower_bound']}, {row['upper_bound']}]")
    print("Candidate biomass reactions:")
    for row in biomass_candidates:
        print(f"{row['reaction_id']}: {row['reaction']} [{row['lower_bound']}, {row['upper_bound']}]")
    print("Currently open medium entries:")
    for exchange_id, value in open_medium.items():
        print(f"{exchange_id}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
