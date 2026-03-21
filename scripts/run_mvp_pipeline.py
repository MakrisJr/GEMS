"""Run the simplified hackathon MVP pipeline from protein FASTA to exported model.

This script builds a draft model, exports it, runs a small COBRA inspection,
and saves a compact MVP summary.
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
from src.export_model import save_gapfill_summary, save_model_json_if_possible, save_model_sbml_if_possible
from src.gapfill import gapfill_model_minimally, summarize_gapfill
from src.input_parser import detect_input_type
from src.logging_utils import get_logger
from src.model_io import save_model_basic_text, save_model_summary
from src.mvp_outputs import save_mvp_summary
from src.paths import MODELS_DIR
from src.reconstruction import build_draft_model_from_protein_fasta, summarize_model


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the simplified hackathon MVP pipeline from protein FASTA to exported model."
    )
    parser.add_argument("--input", required=True, help="Protein FASTA input path.")
    parser.add_argument("--model-id", required=True, help="Model identifier.")
    parser.add_argument("--use-rast", action="store_true", help="Try reconstruction with RAST.")
    parser.add_argument(
        "--template-name",
        default="template_core",
        help="Template name to use for reconstruction and gapfilling. Use 'fungi' with --template-source local to try the local fungal template.",
    )
    parser.add_argument(
        "--template-source",
        choices=("builtin", "local"),
        default="builtin",
        help="Where to load the template from.",
    )
    args = parser.parse_args()

    input_type = detect_input_type(args.input)
    if input_type == "genome_fasta":
        print("Raw genome FASTA is not supported yet. Add an annotation step first.")
        return 0
    if input_type == "accession":
        print("Accession input is not supported in this MVP pipeline.")
        return 0
    if input_type != "protein_fasta":
        print("Only protein FASTA (.faa) input is supported in this MVP pipeline.")
        return 0

    logger = get_logger(__name__)
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Protein FASTA not found: %s", input_path)
        return 1

    model_dir = MODELS_DIR / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Building draft model from %s", input_path)
    model = build_draft_model_from_protein_fasta(
        str(input_path),
        args.model_id,
        use_rast=args.use_rast,
        template_name=args.template_name,
        template_source=args.template_source,
    )
    draft_summary = summarize_model(model)
    draft_summary["input_path"] = str(input_path)
    draft_summary["use_rast"] = args.use_rast
    save_model_summary(draft_summary, str(model_dir / "model_summary.json"))
    save_model_basic_text(draft_summary, str(model_dir / "model_summary.txt"))

    logger.info("Running best-effort gapfill and export")
    before_model = model.copy()
    after_model = gapfill_model_minimally(
        model,
        template_name=args.template_name,
        template_source=args.template_source,
    )
    gapfill_summary = summarize_gapfill(before_model, after_model)
    save_gapfill_summary(gapfill_summary, str(model_dir / "gapfill_summary.json"))

    exported_model_path = model_dir / "model.xml"
    if not save_model_sbml_if_possible(after_model, str(exported_model_path)):
        exported_model_path = model_dir / "model.json"
        save_model_json_if_possible(after_model, str(exported_model_path))

    inspection_success = False
    cobra_summary = {}
    baseline_result = {"status": "failed", "objective_value": None}
    try:
        cobra_model, loaded_path, _ = load_cobra_model(str(model_dir))
        cobra_summary = summarize_cobra_model(cobra_model)
        exchange_table = get_exchange_table(cobra_model)
        baseline_result = run_baseline_optimization(cobra_model)

        save_model_overview(cobra_summary, str(model_dir / "model_overview.json"))
        save_exchange_table(exchange_table, str(model_dir / "exchanges.csv"))
        save_baseline_result(baseline_result, str(model_dir / "baseline_optimization.json"))
        save_cobra_inspection_text(
            cobra_summary, baseline_result, str(model_dir / "cobra_inspection.txt")
        )
        inspection_success = True
        exported_model_path = loaded_path
    except Exception as exc:
        logger.warning("COBRA inspection failed in MVP pipeline: %s", exc)

    mvp_summary = {
        "model_id": args.model_id,
        "input_path": str(input_path),
        "model_dir": str(model_dir),
        "exported_model_path": str(exported_model_path),
        "n_reactions": cobra_summary.get("n_reactions", draft_summary.get("n_reactions")),
        "n_metabolites": cobra_summary.get("n_metabolites", draft_summary.get("n_metabolites")),
        "n_genes": cobra_summary.get("n_genes", draft_summary.get("n_genes")),
        "n_exchanges": cobra_summary.get("n_exchanges", ""),
        "objective": cobra_summary.get("objective", draft_summary.get("objective", "")),
        "baseline_status": baseline_result.get("status", ""),
        "baseline_objective_value": baseline_result.get("objective_value", None),
        "inspection_success": inspection_success,
        "template_name": draft_summary.get("template_name", args.template_name),
        "template_source": draft_summary.get("template_source", args.template_source),
    }
    save_mvp_summary(mvp_summary, str(model_dir))

    print("Fungal GEM MVP pipeline complete.")
    print(f"Model ID: {args.model_id}")
    print(f"Input path: {input_path}")
    print(f"Template name: {mvp_summary['template_name']}")
    print(f"Template source: {mvp_summary['template_source']}")
    print(f"Model directory: {model_dir}")
    print(f"Exported model path: {exported_model_path}")
    print(f"Reactions: {mvp_summary['n_reactions']}")
    print(f"Metabolites: {mvp_summary['n_metabolites']}")
    print(f"Genes: {mvp_summary['n_genes']}")
    print(f"Exchanges: {mvp_summary['n_exchanges']}")
    print(f"Objective: {mvp_summary['objective']}")
    print(f"Baseline status: {mvp_summary['baseline_status']}")
    print(f"Baseline objective value: {mvp_summary['baseline_objective_value']}")
    print("Official next steps:")
    print(f"python scripts/analyze_mvp.py --model-dir {model_dir} --mode theoretical")
    print(f"python scripts/analyze_mvp.py --model-dir {model_dir} --mode preset")
    print(
        "python scripts/analyze_mvp.py "
        f"--model-dir {model_dir} --mode custom --from-preset rich_debug_medium "
        "--condition-name my_custom_condition"
    )
    print(f"python scripts/validate_mvp.py --model-dir {model_dir}")
    print(
        "python scripts/validate_mvp.py "
        f"--model-dir {model_dir} --mode theoretical_upper_bound --biomass-reaction bio2"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
