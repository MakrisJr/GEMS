"""Run optional validation checks on an exported draft model.

This is an optional draft-model validation step before real media optimisation.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_inspect import summarize_cobra_model
from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.validation import (
    find_dead_end_metabolites,
    prepare_validation_model,
    run_exchange_fva,
    run_fba_check,
    run_gene_essentiality,
)
from src.validation_outputs import save_validation_dashboard, save_validation_outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run optional validation checks on an exported draft model."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    parser.add_argument(
        "--mode",
        default="default",
        choices=["default", "theoretical_upper_bound"],
        help="Validation mode. theoretical_upper_bound uses the draft model's best-case benchmark setup.",
    )
    parser.add_argument(
        "--biomass-reaction",
        default="bio2",
        help="Biomass-like reaction to use for theoretical upper-bound validation.",
    )
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))
    model_summary = summarize_cobra_model(model)

    logger.info("Preparing validation model in %s mode", args.mode)
    validation_model, validation_context = prepare_validation_model(
        model,
        mode=args.mode,
        biomass_reaction_id=args.biomass_reaction,
    )
    validation_model_summary = summarize_cobra_model(validation_model)

    logger.info("Running baseline FBA validation")
    fba_result = run_fba_check(validation_model)

    logger.info("Finding dead-end metabolites")
    dead_end_rows, dead_end_summary = find_dead_end_metabolites(validation_model)

    logger.info("Running exchange FVA")
    exchange_fva_rows, exchange_fva_summary = run_exchange_fva(validation_model)

    logger.info("Running single-gene deletion screen")
    gene_essentiality_rows, gene_essentiality_summary = run_gene_essentiality(
        validation_model, baseline_objective_value=fba_result.get("objective_value")
    )

    summary = {
        "model_path": str(model_path),
        "model_format": model_format,
        "model": model_summary,
        "validation_model": validation_model_summary,
        "validation_context": validation_context,
        "fba": fba_result,
        "dead_end_metabolites": dead_end_summary,
        "exchange_fva": exchange_fva_summary,
        "gene_essentiality": gene_essentiality_summary,
    }

    prefix = ""
    if args.mode != "default":
        prefix = f"{args.mode}_"

    save_validation_outputs(
        summary,
        dead_end_rows,
        exchange_fva_rows,
        gene_essentiality_rows,
        str(model_dir),
        prefix=prefix,
    )
    save_validation_dashboard(summary, str(model_dir), prefix=prefix)

    print("This is an optional draft-model validation step before real media optimisation.")
    print(f"Validation mode: {validation_context.get('validation_mode', 'default')}")
    print(f"Model path: {model_path}")
    print(f"Model format: {model_format}")
    print(
        "Biomass reaction: "
        f"{validation_context.get('biomass_reaction_id', model_summary.get('objective', ''))}"
    )
    print(
        "Added boundaries: "
        f"{validation_context.get('n_added_boundaries', 0)}"
    )
    print(f"FBA status: {fba_result.get('status', '')}")
    print(f"Objective value: {fba_result.get('objective_value', None)}")
    print(
        "Dead-end metabolites: "
        f"{dead_end_summary.get('n_dead_end_metabolites', 0)}"
    )
    print(
        "Exchange FVA status: "
        f"{exchange_fva_summary.get('status', '')}"
    )
    print(
        "Essential gene status: "
        f"{gene_essentiality_summary.get('status', '')}"
    )
    print(f"Output directory: {model_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
