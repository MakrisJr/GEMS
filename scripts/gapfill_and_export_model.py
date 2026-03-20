"""Run a minimal best-effort gapfill and export step for a draft model.

This is still a draft model. Gapfilling is a best-effort step in this
minimal version.
"""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.export_model import save_gapfill_summary, save_model_json_if_possible, save_model_sbml_if_possible
from src.gapfill import gapfill_model_minimally, summarize_gapfill
from src.logging_utils import get_logger


def _load_existing_or_rebuild_model(model_dir: Path):
    summary_path = model_dir / "model_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Draft model summary not found: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    model_id = summary["model_id"]

    sbml_path = model_dir / "model.xml"
    if sbml_path.exists():
        try:
            from cobra.io import read_sbml_model

            return read_sbml_model(str(sbml_path))
        except Exception:
            pass

    json_path = model_dir / "model.json"
    if json_path.exists():
        try:
            from cobra.io import load_json_model

            return load_json_model(str(json_path))
        except Exception:
            pass

    from src.reconstruction import build_draft_model_from_protein_fasta

    input_path = Path(summary["input_path"])
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    use_rast = bool(summary.get("use_rast", False))
    return build_draft_model_from_protein_fasta(str(input_path), model_id, use_rast=use_rast)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a minimal best-effort gapfill and export step for a draft model."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing draft model outputs.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    logger.info("Loading or rebuilding draft model from %s", model_dir)
    model = _load_existing_or_rebuild_model(model_dir)
    before_model = model.copy()

    after_model = gapfill_model_minimally(model)
    summary = summarize_gapfill(before_model, after_model)

    save_gapfill_summary(summary, str(model_dir / "gapfill_summary.json"))

    saved_files = [model_dir / "gapfill_summary.json", model_dir / "gapfill_summary.txt"]

    sbml_path = model_dir / "model.xml"
    json_path = model_dir / "model.json"
    if save_model_sbml_if_possible(after_model, str(sbml_path)):
        saved_files.append(sbml_path)
    else:
        save_model_json_if_possible(after_model, str(json_path))
        saved_files.append(json_path)

    print("This is still a draft model. Gapfilling is a best-effort step in this minimal version.")
    print(f"Model directory: {model_dir}")
    print(f"Gapfill attempted: {summary['gapfill_attempted']}")
    print(f"Gapfill success: {summary['gapfill_success']}")
    print(f"Reactions before/after: {summary['reactions_before']} -> {summary['reactions_after']}")
    print(f"Metabolites before/after: {summary['metabolites_before']} -> {summary['metabolites_after']}")
    print(f"Genes before/after: {summary['genes_before']} -> {summary['genes_after']}")
    print("Saved files:")
    for path in saved_files:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
