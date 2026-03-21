"""Build a minimal draft ModelSEEDpy reconstruction from protein FASTA.

This script builds a draft model only. It does not add gapfilling,
simulation, or raw genome FASTA support.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.input_parser import detect_input_type
from src.logging_utils import get_logger
from src.model_io import save_model_basic_text, save_model_summary
from src.paths import MODELS_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a minimal draft ModelSEEDpy reconstruction.")
    parser.add_argument("--input", required=True, help="Protein FASTA input path.")
    parser.add_argument("--model-id", required=True, help="Model identifier.")
    parser.add_argument("--use-rast", action="store_true", help="Try reconstruction with RAST annotation.")
    args = parser.parse_args()

    input_type = detect_input_type(args.input)
    if input_type == "genome_fasta":
        print("Raw genome FASTA is not supported yet. Add an annotation step first.")
        return 0

    if input_type == "accession":
        print("Accession input is not supported in this reconstruction step.")
        return 0

    if input_type != "protein_fasta":
        print("Only protein FASTA (.faa) input is supported in this reconstruction step.")
        return 0

    logger = get_logger(__name__)
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Protein FASTA not found: %s", input_path)
        return 1

    output_dir = MODELS_DIR / args.model_id
    output_dir.mkdir(parents=True, exist_ok=True)

    from src.reconstruction import build_draft_model_from_protein_fasta, summarize_model

    model = build_draft_model_from_protein_fasta(str(input_path), args.model_id, use_rast=args.use_rast)
    summary = summarize_model(model)
    summary["input_path"] = str(input_path)
    summary["use_rast"] = args.use_rast

    logger.info("Saving summary files to %s", output_dir)
    save_model_summary(summary, str(output_dir / "model_summary.json"))
    save_model_basic_text(summary, str(output_dir / "model_summary.txt"))

    print(f"Model ID: {summary['model_id']}")
    print(f"Input path: {input_path}")
    print(f"Reactions: {summary['n_reactions']}")
    print(f"Metabolites: {summary['n_metabolites']}")
    print(f"Genes: {summary['n_genes']}")
    print(f"Objective: {summary['objective']}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
