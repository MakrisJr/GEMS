"""Diagnose the exchange space of the exported draft model.

This is a draft model inspection step before media optimisation.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_loader import load_cobra_model
from src.exchange_diagnostic_outputs import save_exchange_diagnostics
from src.exchange_diagnostics import flag_plausible_carbon_sources, summarize_exchange_metabolites
from src.logging_utils import get_logger


def main() -> int:
    parser = argparse.ArgumentParser(
        description="This is a draft model inspection step before media optimisation."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    model, model_path, model_format = load_cobra_model(str(model_dir))
    exchange_rows = summarize_exchange_metabolites(model)
    summary = flag_plausible_carbon_sources(exchange_rows)
    save_exchange_diagnostics(exchange_rows, summary, str(model_dir))

    print("This is a draft model inspection step before media optimisation.")
    print(f"Model path: {model_path}")
    print(f"Model format: {model_format}")
    print(f"Exchange reactions: {summary['n_exchanges']}")
    print(f"Carbon-containing exchanges: {summary['n_carbon_containing_exchanges']}")
    print(f"Plausible carbon sources: {summary['n_plausible_carbon_sources']}")
    print(f"Has plausible carbon source: {summary['has_plausible_carbon_source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
