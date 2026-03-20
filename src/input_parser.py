from pathlib import Path


def detect_input_type(value: str) -> str:
    if value.startswith(("GCA_", "GCF_")):
        return "accession"

    suffix = Path(value).suffix.lower()
    if suffix == ".faa":
        return "protein_fasta"
    if suffix in {".fasta", ".fa", ".fna"}:
        return "genome_fasta"
    return "unknown"
