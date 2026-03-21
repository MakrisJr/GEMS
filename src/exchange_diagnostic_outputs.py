"""Minimal output writers for exchange-space diagnostics.

This is a draft model inspection step before media optimisation.
"""

import json
from pathlib import Path

import pandas as pd

from .logging_utils import get_logger


logger = get_logger(__name__)


def save_exchange_diagnostics(exchange_rows, summary: dict, outdir: str):
    """Save annotated exchange rows and a short diagnostic summary."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataframe = pd.DataFrame(exchange_rows)
    dataframe.to_csv(output_dir / "exchange_metabolites.csv", index=False)
    (output_dir / "exchange_diagnosis.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "This is a draft model inspection step before media optimisation.",
        f"n_exchanges: {summary.get('n_exchanges', '')}",
        f"n_carbon_containing_exchanges: {summary.get('n_carbon_containing_exchanges', '')}",
        f"n_plausible_carbon_sources: {summary.get('n_plausible_carbon_sources', '')}",
        f"has_plausible_carbon_source: {summary.get('has_plausible_carbon_source', '')}",
        f"plausible_carbon_source_ids: {summary.get('plausible_carbon_source_ids', [])}",
        f"plausible_carbon_source_names: {summary.get('plausible_carbon_source_names', [])}",
    ]
    (output_dir / "exchange_diagnosis.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved exchange diagnostics to %s", output_dir)
