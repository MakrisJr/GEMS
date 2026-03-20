"""Minimal first functional ModelSEEDpy CLI for protein FASTA inputs.

This script only loads a protein FASTA into a ModelSEEDpy genome object.
It does not build a metabolic model, and raw genome FASTA is not supported
until an annotation step is added.
"""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.input_parser import detect_input_type
from src.logging_utils import get_logger
from src.modelseed_step import load_protein_genome, optionally_annotate_with_rast, summarize_genome
from src.paths import INTERMEDIATE_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the first ModelSEED-oriented step for a protein FASTA input.")
    parser.add_argument("--input", required=True, help="Input accession or file path.")
    parser.add_argument("--use-rast", action="store_true", help="Try RAST annotation if available.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    input_type = detect_input_type(args.input)

    if input_type == "genome_fasta":
        print("Raw genome FASTA is not supported in this minimal step. Add an annotation step first.")
        return 0

    if input_type == "accession":
        print("Accession input is not supported in this minimal ModelSEED step.")
        return 0

    if input_type != "protein_fasta":
        print("Only protein FASTA (.faa) input is supported in this minimal ModelSEED step.")
        return 0

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Protein FASTA not found: %s", input_path)
        return 1

    genome = load_protein_genome(str(input_path))
    genome = optionally_annotate_with_rast(genome, use_rast=args.use_rast)

    summary = {
        "input_path": args.input,
        "annotation_attempted": bool(getattr(genome, "annotation_attempted", False)),
        "annotation_success": bool(getattr(genome, "annotation_success", False)),
        **summarize_genome(genome),
    }

    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = INTERMEDIATE_DIR / "genome_summary.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    logger.info("Genome summary saved to %s", output_path)
    logger.info("Features: %s", summary["n_features"])
    logger.info("Annotation attempted: %s", summary["annotation_attempted"])
    logger.info("Annotation success: %s", summary["annotation_success"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
