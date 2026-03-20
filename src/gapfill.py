"""Minimal best-effort gapfilling for draft ModelSEEDpy reconstructions.

This is still a draft model. Gapfilling is a best-effort step in this
minimal version.
"""

import os
import tempfile

from .logging_utils import get_logger


os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from modelseedpy.core.msbuilder import MSBuilder
from modelseedpy.core.mstemplate import MSTemplateBuilder
from modelseedpy.helpers import get_template


logger = get_logger(__name__)


def _set_gapfill_metadata(model, attempted: bool, success: bool, error_message: str = ""):
    model.gapfill_attempted = attempted
    model.gapfill_success = success
    model.gapfill_error_message = error_message


def gapfill_model_minimally(model):
    """Attempt one public ModelSEEDpy gapfilling step and return a model."""
    _set_gapfill_metadata(model, attempted=True, success=False)

    if "bio1" not in model.reactions:
        message = "Target reaction bio1 was not found. Skipping gapfilling."
        logger.warning(message)
        model.gapfill_error_message = message
        return model

    try:
        logger.info("Loading template: template_core")
        template_dict = get_template("template_core")
        template = MSTemplateBuilder.from_dict(template_dict).build()

        logger.info("Attempting minimal gapfilling for draft model %s", model.id)
        updated_model = MSBuilder.gapfill_model(model, "bio1", template, None)
        _set_gapfill_metadata(updated_model, attempted=True, success=True)
        return updated_model
    except Exception as exc:
        message = str(exc)
        logger.warning("Gapfilling failed; continuing with ungapfilled draft model: %s", message)
        _set_gapfill_metadata(model, attempted=True, success=False, error_message=message)
        return model


def summarize_gapfill(before_model, after_model) -> dict:
    """Return a small before/after summary for the best-effort gapfill step."""
    return {
        "gapfill_attempted": bool(getattr(after_model, "gapfill_attempted", False)),
        "gapfill_success": bool(getattr(after_model, "gapfill_success", False)),
        "error_message": getattr(after_model, "gapfill_error_message", ""),
        "reactions_before": len(before_model.reactions),
        "reactions_after": len(after_model.reactions),
        "metabolites_before": len(before_model.metabolites),
        "metabolites_after": len(after_model.metabolites),
        "genes_before": len(before_model.genes),
        "genes_after": len(after_model.genes),
    }
