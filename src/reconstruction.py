"""Minimal draft reconstruction from protein FASTA with ModelSEEDpy.

This step builds a draft metabolic model only. It does not add gapfilling,
simulation, or support for raw genome FASTA inputs.
"""

import os
import tempfile
from pathlib import Path

from .logging_utils import get_logger
from .template_loader import build_template, describe_template_source


os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from modelseedpy.core.msbuilder import MSBuilder
from modelseedpy.core.msgenome import MSGenome


logger = get_logger(__name__)


def build_draft_model_from_protein_fasta(
    input_path: str,
    model_id: str,
    use_rast: bool = False,
    template_name: str = "template_core",
    template_source: str = "builtin",
):
    """Build a draft ModelSEEDpy reconstruction from a protein FASTA file."""
    input_file = Path(input_path)
    template_info = describe_template_source(template_name=template_name, source=template_source)

    logger.info("Loading genome from %s", input_file)
    genome = MSGenome.from_fasta(str(input_file), split=" ")
    logger.info("Loaded %s features", len(genome.features))

    logger.info(
        "Loading template: %s (%s)",
        template_info["template_name"],
        template_info["template_source"],
    )
    template = build_template(
        template_name=template_info["template_name"],
        source=template_info["template_source"],
    )

    logger.info("Building draft model for %s", model_id)
    try:
        model = MSBuilder.build_metabolic_model(
            model_id,
            genome,
            gapfill_media=None,
            template=template,
            allow_all_non_grp_reactions=True,
            annotate_with_rast=use_rast,
            gapfill_model=False,
        )
    except Exception as exc:
        if not use_rast:
            raise

        logger.warning("RAST reconstruction failed; retrying without RAST: %s", exc)
        logger.info("Reloading genome from %s", input_file)
        genome = MSGenome.from_fasta(str(input_file), split=" ")
        logger.info("Building draft model for %s without RAST", model_id)
        model = MSBuilder.build_metabolic_model(
            model_id,
            genome,
            gapfill_media=None,
            template=template,
            allow_all_non_grp_reactions=True,
            annotate_with_rast=False,
            gapfill_model=False,
        )

    if "bio1" in model.reactions:
        model.objective = "bio1"

    model.reconstruction_template_name = template_info["template_name"]
    model.reconstruction_template_source = template_info["template_source"]
    model.reconstruction_template_path = template_info["template_path"]
    return model


def summarize_model(model) -> dict:
    """Return a small summary for a draft reconstruction."""
    objective = ""
    expression = getattr(model.objective, "expression", None)
    if "bio1" in model.reactions and expression is not None and "bio1" in str(expression):
        objective = "bio1"
    elif expression is not None:
        objective = str(expression)

    return {
        "model_id": model.id,
        "n_reactions": len(model.reactions),
        "n_metabolites": len(model.metabolites),
        "n_genes": len(model.genes),
        "objective": objective,
        "template_name": getattr(model, "reconstruction_template_name", ""),
        "template_source": getattr(model, "reconstruction_template_source", ""),
        "template_path": getattr(model, "reconstruction_template_path", ""),
    }
