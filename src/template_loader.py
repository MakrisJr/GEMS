"""Helpers for loading ModelSEED templates from built-in or local sources."""

import json
import os
import tempfile
from pathlib import Path

from .paths import PROJECT_ROOT


os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from modelseedpy.core.mstemplate import MSTemplateBuilder
from modelseedpy.helpers import get_template


MODELSEED_DATABASE_ROOT = PROJECT_ROOT / "ModelSEEDDatabase" / "Templates"

_TEMPLATE_ALIASES = {
    "core": "template_core",
    "template_core": "template_core",
    "fungi": "fungi",
    "fungal": "fungi",
}

_LOCAL_TEMPLATE_PATHS = {
    "fungi": MODELSEED_DATABASE_ROOT / "Fungi" / "Fungi.json",
}


def normalize_template_name(template_name: str) -> str:
    """Return a canonical template name used internally by this project."""
    value = str(template_name).strip().lower()
    if not value:
        raise ValueError("Template name cannot be empty.")
    return _TEMPLATE_ALIASES.get(value, value)


def get_local_template_path(template_name: str) -> Path:
    """Return the on-disk path for a supported local ModelSEED template."""
    normalized_name = normalize_template_name(template_name)
    path = _LOCAL_TEMPLATE_PATHS.get(normalized_name)
    if path is None:
        supported = ", ".join(sorted(_LOCAL_TEMPLATE_PATHS))
        raise ValueError(
            f"Unsupported local template '{template_name}'. Supported local templates: {supported}."
        )
    if not path.exists():
        raise FileNotFoundError(f"Local template file not found: {path}")
    return path


def load_template_dict(template_name: str = "template_core", source: str = "builtin") -> dict:
    """Load a template dictionary from the chosen source."""
    normalized_name = normalize_template_name(template_name)
    normalized_source = str(source).strip().lower()

    if normalized_source == "builtin":
        return get_template(normalized_name)
    if normalized_source == "local":
        template_path = get_local_template_path(normalized_name)
        template_dict = json.loads(template_path.read_text(encoding="utf-8"))
        template_dict.setdefault("__VERSION__", "local")
        for reaction in template_dict.get("reactions", []):
            reaction_id = reaction.get("id", "")
            base_reaction_id = reaction_id.rsplit("_", 1)[0] if "_" in reaction_id else reaction_id
            reaction.setdefault(
                "reaction_ref",
                f"kbase/default/reactions/id/{base_reaction_id}",
            )
        return template_dict

    raise ValueError("Template source must be 'builtin' or 'local'.")


def build_template(template_name: str = "template_core", source: str = "builtin"):
    """Build and return an MSTemplate object from the chosen source."""
    template_dict = load_template_dict(template_name=template_name, source=source)
    return MSTemplateBuilder.from_dict(template_dict).build()


def describe_template_source(template_name: str = "template_core", source: str = "builtin") -> dict:
    """Return normalized metadata describing which template was requested."""
    normalized_name = normalize_template_name(template_name)
    normalized_source = str(source).strip().lower()
    template_path = ""
    if normalized_source == "local":
        template_path = str(get_local_template_path(normalized_name))

    return {
        "template_name": normalized_name,
        "template_source": normalized_source,
        "template_path": template_path,
    }
