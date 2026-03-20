"""Minimal first ModelSEEDpy step for protein FASTA inputs only.

This module only loads a protein FASTA into a ModelSEEDpy genome object.
It does not build a metabolic model, and raw genome FASTA is not supported
until an annotation step is added.
"""

import os
import tempfile
from pathlib import Path

from .logging_utils import get_logger


# ModelSEEDpy imports COBRApy on import. Using a fresh temp cache path avoids
# environment-specific cache directory issues without adding project files.
os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from modelseedpy.core.msgenome import MSGenome


logger = get_logger(__name__)


def load_protein_genome(path: str, split: str = " "):
    genome = MSGenome.from_fasta(path, split=split)
    logger.info("Loaded %s features from %s", len(genome.features), Path(path))
    return genome


def optionally_annotate_with_rast(genome, use_rast: bool = False):
    genome.annotation_attempted = use_rast
    genome.annotation_success = False

    if not use_rast:
        return genome

    try:
        from modelseedpy.core.rast_client import RastClient

        RastClient().annotate_genome(genome)
        genome.annotation_success = True
        logger.info("RAST annotation completed.")
    except Exception as exc:
        logger.warning("RAST annotation failed; continuing with unannotated genome: %s", exc)

    return genome


def summarize_genome(genome) -> dict:
    features = list(genome.features)[:10]
    return {
        "n_features": len(genome.features),
        "first_10_feature_ids": [feature.id for feature in features],
        "first_10_descriptions": [feature.description or "" for feature in features],
    }
