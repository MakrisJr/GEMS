"""Run one user-facing hackathon MVP analysis mode on a draft model.

Modes:
- theoretical
- preset
- custom
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.mvp_analysis import (
    build_custom_condition,
    get_preset_condition_library,
    parse_metabolite_ids,
    run_custom_condition,
    run_preset_benchmark,
    run_theoretical_upper_bound,
)
from src.mvp_outputs import (
    save_custom_condition,
    save_preset_benchmark,
    save_theoretical_upper_bound,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one user-facing hackathon MVP analysis mode on a draft model."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["theoretical", "preset", "custom"],
        help="Analysis mode to run.",
    )
    parser.add_argument("--biomass-reaction", default="bio2", help="Biomass-like reaction to test.")
    parser.add_argument("--condition-name", default="custom_condition", help="Name for a custom condition.")
    parser.add_argument(
        "--from-preset",
        default="",
        help="Seed a custom condition from a preset condition name.",
    )
    parser.add_argument(
        "--metabolite-ids",
        default="",
        help="Comma-separated metabolite IDs for a custom condition.",
    )
    parser.add_argument(
        "--add-metabolites",
        default="",
        help="Comma-separated metabolite IDs to add to a preset-seeded custom condition.",
    )
    parser.add_argument(
        "--remove-metabolites",
        default="",
        help="Comma-separated metabolite IDs to remove from a preset-seeded custom condition.",
    )
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))

    if args.mode == "theoretical":
        result = run_theoretical_upper_bound(model, biomass_reaction_id=args.biomass_reaction)
        save_theoretical_upper_bound(result, str(model_dir))
        print("Mode: Theoretical Upper Bound")
        print("This is a best-case benchmark, not a wet-lab medium recommendation.")
        print(f"Model path: {model_path}")
        print(f"Model format: {model_format}")
        print(f"bio2 rate: {result.get('bio2_rate', None)}")
        print(f"Yield proxy: {result.get('bio2_yield_on_total_added_flux', None)}")
        print(f"Status: {result.get('status', '')}")
        return 0

    if args.mode == "preset":
        results = run_preset_benchmark(model, biomass_reaction_id=args.biomass_reaction)
        save_preset_benchmark(results, str(model_dir))
        best = results[0] if results else {}
        print("Mode: Preset Conditions")
        print("These are pre-made benchmark conditions for comparing model behavior.")
        print(f"Model path: {model_path}")
        print(f"Model format: {model_format}")
        print(f"Number of conditions: {len(results)}")
        print(f"Best condition: {best.get('condition', '')}")
        print(f"Best bio2 rate: {best.get('bio2_rate', None)}")
        print(f"Best yield proxy: {best.get('bio2_yield_on_total_added_flux', None)}")
        return 0

    preset_library = get_preset_condition_library(model, biomass_reaction_id=args.biomass_reaction)
    if args.from_preset and args.from_preset not in preset_library:
        logger.error("Unknown preset condition: %s", args.from_preset)
        logger.error("Available presets: %s", ", ".join(sorted(preset_library)))
        return 1

    metabolite_ids = build_custom_condition(
        model,
        biomass_reaction_id=args.biomass_reaction,
        from_preset=args.from_preset,
        metabolite_ids=parse_metabolite_ids(args.metabolite_ids),
        add_metabolites=parse_metabolite_ids(args.add_metabolites),
        remove_metabolites=parse_metabolite_ids(args.remove_metabolites),
    )
    if not metabolite_ids:
        logger.error("Custom mode needs metabolites. Use --from-preset, --metabolite-ids, or both.")
        return 1

    result = run_custom_condition(
        model,
        metabolite_ids=metabolite_ids,
        condition_name=args.condition_name,
        biomass_reaction_id=args.biomass_reaction,
    )
    save_custom_condition(result, str(model_dir))
    print("Mode: Custom Condition")
    print("This lets you test your own draft condition on the model.")
    print(f"Model path: {model_path}")
    print(f"Model format: {model_format}")
    print(f"Condition: {result.get('condition', '')}")
    print(f"bio2 rate: {result.get('bio2_rate', None)}")
    print(f"Yield proxy: {result.get('bio2_yield_on_total_added_flux', None)}")
    print(f"Status: {result.get('status', '')}")
    print("Metabolites used:")
    for metabolite_id in result.get("metabolite_ids", []):
        print(metabolite_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
