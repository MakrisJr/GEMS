"""Screen a semi-artificial rich debug medium derived from oracle growth.

This is a draft model debugging step before media optimisation.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.oracle_medium import build_debug_medium_library, screen_debug_media
from src.oracle_medium_outputs import save_oracle_medium_plot, save_oracle_medium_results


def _growth_key(row):
    value = row.get("predicted_growth")
    return float("-inf") if value is None else value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="This is a draft model debugging step before media optimisation."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    parser.add_argument("--biomass-reaction", default="bio2", help="Biomass-like reaction to test.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, _ = load_cobra_model(str(model_dir))
    medium_library = build_debug_medium_library(model, biomass_reaction_id=args.biomass_reaction)
    results = screen_debug_media(model, medium_library, biomass_reaction_id=args.biomass_reaction)
    results = sorted(results, key=_growth_key, reverse=True)

    save_oracle_medium_results(results, str(model_dir))
    save_oracle_medium_plot(results, str(model_dir))

    best = results[0] if results else {"condition": "", "predicted_growth": None}
    print("This is a draft model debugging step before media optimisation.")
    print(f"Model path: {model_path}")
    print(f"Biomass reaction: {args.biomass_reaction}")
    print(f"Number of conditions: {len(results)}")
    print(f"Best condition: {best['condition']}")
    print(f"Best predicted growth: {best['predicted_growth']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
