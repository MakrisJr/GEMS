"""Benchmark bio2 rate and a simple yield proxy across debug conditions.

This is a draft model debugging step before media optimisation.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bio2_benchmark import benchmark_bio2_conditions
from src.bio2_benchmark_outputs import save_bio2_benchmark_plot, save_bio2_benchmark_results
from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.oracle_medium import build_debug_medium_library


def _rate_key(row):
    value = row.get("bio2_rate")
    return float("-inf") if value is None else value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark bio2 rate and a debug yield proxy on a draft model."
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
    results = benchmark_bio2_conditions(
        model, medium_library, biomass_reaction_id=args.biomass_reaction
    )
    results = sorted(results, key=_rate_key, reverse=True)

    save_bio2_benchmark_results(results, str(model_dir))
    save_bio2_benchmark_plot(results, str(model_dir))

    best = results[0] if results else {}
    print("This is a draft model debugging step before media optimisation.")
    print("The reported yield is a debug proxy based on total added boundary flux.")
    print(f"Model path: {model_path}")
    print(f"Biomass reaction: {args.biomass_reaction}")
    print(f"Number of conditions: {len(results)}")
    print(f"Best condition: {best.get('condition', '')}")
    print(f"Best bio2 rate: {best.get('bio2_rate', None)}")
    print(
        "Best bio2 yield proxy: "
        f"{best.get('bio2_yield_on_total_added_flux', None)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
