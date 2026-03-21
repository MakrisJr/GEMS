"""Inspect the exported draft model with COBRApy.

This is a draft model inspection step before media optimisation.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_inspect import get_exchange_table, run_baseline_optimization, summarize_cobra_model
from src.cobra_loader import load_cobra_model
from src.cobra_outputs import (
    save_baseline_result,
    save_cobra_inspection_text,
    save_exchange_table,
    save_model_overview,
)
from src.logging_utils import get_logger


def main() -> int:
    parser = argparse.ArgumentParser(
        description="This is a draft model inspection step before media optimisation."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing model.xml, model.sbml, or model.json.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))
    summary = summarize_cobra_model(model)
    exchanges = get_exchange_table(model)
    baseline = run_baseline_optimization(model)

    save_model_overview(summary, str(model_dir / "model_overview.json"))
    save_exchange_table(exchanges, str(model_dir / "exchanges.csv"))
    save_baseline_result(baseline, str(model_dir / "baseline_optimization.json"))
    save_cobra_inspection_text(summary, baseline, str(model_dir / "cobra_inspection.txt"))

    print("This is a draft model inspection step before media optimisation.")
    print(f"Chosen file path: {model_path}")
    print(f"File format: {model_format}")
    print(f"Reactions: {summary['n_reactions']}")
    print(f"Metabolites: {summary['n_metabolites']}")
    print(f"Genes: {summary['n_genes']}")
    print(f"Exchange reactions: {summary['n_exchanges']}")
    print(f"Objective: {summary['objective']}")
    print(f"Optimization status: {baseline['status']}")
    print(f"Objective value: {baseline['objective_value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
