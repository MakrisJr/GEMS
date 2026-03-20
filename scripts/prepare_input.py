import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.input_parser import detect_input_type


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare input for the fungal ModelSEED pipeline.")
    parser.add_argument("--input", required=True, help="Input accession or file path.")
    args = parser.parse_args()

    input_type = detect_input_type(args.input)
    print(f"Detected input type: {input_type}")

    if input_type == "accession":
        print("Accessions are not yet implemented for ModelSEED input loading in this minimal version.")
    elif input_type == "genome_fasta":
        print("Raw genome FASTA needs an annotation step before ModelSEEDpy in this minimal version.")
    elif input_type == "protein_fasta":
        print("Protein FASTA is supported for the next step.")
    else:
        print("Input type is not recognized by this minimal scaffold.")


if __name__ == "__main__":
    main()
