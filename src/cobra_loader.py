"""Minimal COBRApy model loading for draft model inspection.

This is a draft model inspection step before media optimisation.
"""

import os
import tempfile
from pathlib import Path

from .logging_utils import get_logger


os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from cobra.io import load_json_model, read_sbml_model


logger = get_logger(__name__)


def find_model_file(model_dir: str):
    """Find the preferred exported model file in a model directory."""
    model_path = Path(model_dir)
    candidates = [
        (model_path / "model.xml", "sbml"),
        (model_path / "model.sbml", "sbml"),
        (model_path / "model.json", "json"),
    ]

    for path, model_format in candidates:
        if path.exists():
            return path, model_format

    raise FileNotFoundError(
        f"No supported model file found in {model_path}. Expected model.xml, model.sbml, or model.json."
    )


def load_cobra_model(model_dir: str):
    """Load a COBRApy model from SBML if available, otherwise JSON."""
    model_path, model_format = find_model_file(model_dir)
    logger.info("Loading COBRA model from %s", model_path)

    if model_format == "sbml":
        model = read_sbml_model(str(model_path))
    else:
        model = load_json_model(str(model_path))

    return model, model_path, model_format
