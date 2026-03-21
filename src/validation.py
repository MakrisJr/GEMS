"""Optional COBRA-based validation checks for the draft model.

This is an optional draft-model validation step before real media optimisation.
"""

import os
import tempfile

from .logging_utils import get_logger
from .oracle_growth import find_biomass_reaction
from .oracle_medium import build_debug_medium_library


os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="fungal_modelseed_cache_"))

from cobra.flux_analysis import flux_variability_analysis, single_gene_deletion


logger = get_logger(__name__)


def prepare_validation_model(model, mode: str = "default", biomass_reaction_id: str = "bio2"):
    """Return a model copy prepared for the requested validation mode."""
    if mode == "default":
        return model.copy(), {
            "validation_mode": "default",
            "description": "validation on the exported draft model as saved",
            "biomass_reaction_id": "",
            "condition_name": "default",
            "n_added_boundaries": 0,
            "added_boundary_ids": [],
            "missing_metabolite_ids": [],
            "metabolite_ids": [],
        }

    if mode != "theoretical_upper_bound":
        raise ValueError(f"Unsupported validation mode: {mode}")

    validation_model = model.copy()
    biomass_reaction = find_biomass_reaction(
        validation_model, preferred_id=biomass_reaction_id
    )
    debug_library = build_debug_medium_library(
        validation_model, biomass_reaction_id=biomass_reaction_id
    )
    theoretical_condition = debug_library["full_oracle"]

    added_boundary_ids = []
    missing_metabolite_ids = []
    for metabolite_id in theoretical_condition.get("metabolite_ids", []):
        if metabolite_id not in validation_model.metabolites:
            missing_metabolite_ids.append(metabolite_id)
            continue

        metabolite = validation_model.metabolites.get_by_id(metabolite_id)
        boundary = validation_model.add_boundary(metabolite, type="sink")
        added_boundary_ids.append(boundary.id)

    validation_model.objective = biomass_reaction.id
    return validation_model, {
        "validation_mode": "theoretical_upper_bound",
        "description": (
            "validation under the theoretical upper-bound condition on a draft model"
        ),
        "biomass_reaction_id": biomass_reaction.id,
        "condition_name": "theoretical_upper_bound",
        "n_added_boundaries": len(added_boundary_ids),
        "added_boundary_ids": added_boundary_ids,
        "missing_metabolite_ids": missing_metabolite_ids,
        "metabolite_ids": list(theoretical_condition.get("metabolite_ids", [])),
    }


def _reaction_can_consume(reaction, coefficient: float) -> bool:
    """Return whether a reaction can consume a metabolite with this coefficient."""
    return (coefficient < 0 and reaction.upper_bound > 0) or (
        coefficient > 0 and reaction.lower_bound < 0
    )


def _reaction_can_produce(reaction, coefficient: float) -> bool:
    """Return whether a reaction can produce a metabolite with this coefficient."""
    return (coefficient > 0 and reaction.upper_bound > 0) or (
        coefficient < 0 and reaction.lower_bound < 0
    )


def _normalize_gene_ids(value) -> str:
    """Return a readable gene identifier from single-gene deletion output."""
    if isinstance(value, frozenset):
        return ",".join(sorted(value))
    if isinstance(value, set):
        return ",".join(sorted(value))
    if isinstance(value, tuple):
        return ",".join(str(item) for item in value)
    return str(value)


def run_fba_check(model) -> dict:
    """Run one baseline FBA check on the exported model."""
    objective = ""
    expression = getattr(getattr(model, "objective", None), "expression", None)
    if expression is not None:
        objective = str(expression)

    try:
        solution = model.optimize()
        return {
            "status": solution.status,
            "objective_value": solution.objective_value,
            "objective": objective,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "objective_value": None,
            "objective": objective,
            "error_message": str(exc),
        }


def find_dead_end_metabolites(model):
    """Find metabolites that are only produced or only consumed internally."""
    rows = []
    produced_only = 0
    consumed_only = 0

    for metabolite in model.metabolites:
        if metabolite.compartment == "e":
            continue

        producing_reactions = []
        consuming_reactions = []

        for reaction in metabolite.reactions:
            if reaction.boundary:
                continue

            coefficient = reaction.metabolites.get(metabolite, 0.0)
            if _reaction_can_produce(reaction, coefficient):
                producing_reactions.append(reaction.id)
            if _reaction_can_consume(reaction, coefficient):
                consuming_reactions.append(reaction.id)

        if producing_reactions and consuming_reactions:
            continue

        if not producing_reactions and not consuming_reactions:
            status = "isolated"
        elif producing_reactions:
            status = "produced_only"
            produced_only += 1
        else:
            status = "consumed_only"
            consumed_only += 1

        rows.append(
            {
                "metabolite_id": metabolite.id,
                "metabolite_name": metabolite.name,
                "compartment": metabolite.compartment,
                "status": status,
                "n_producing_reactions": len(producing_reactions),
                "n_consuming_reactions": len(consuming_reactions),
                "producing_reactions": ";".join(producing_reactions),
                "consuming_reactions": ";".join(consuming_reactions),
            }
        )

    summary = {
        "n_dead_end_metabolites": len(rows),
        "n_produced_only": produced_only,
        "n_consumed_only": consumed_only,
        "n_isolated": sum(1 for row in rows if row["status"] == "isolated"),
    }
    return rows, summary


def run_exchange_fva(model):
    """Run FVA on exchange reactions when possible."""
    exchange_reactions = list(model.exchanges)
    if not exchange_reactions:
        return [], {
            "status": "skipped",
            "error_message": "No exchange reactions found.",
            "n_exchange_reactions": 0,
        }

    try:
        fva = flux_variability_analysis(model, reaction_list=exchange_reactions, processes=1)
        rows = []
        for reaction in exchange_reactions:
            minimum = float(fva.loc[reaction.id, "minimum"])
            maximum = float(fva.loc[reaction.id, "maximum"])
            rows.append(
                {
                    "reaction_id": reaction.id,
                    "reaction_name": reaction.name or reaction.id,
                    "minimum": minimum,
                    "maximum": maximum,
                    "range": maximum - minimum,
                    "lower_bound": reaction.lower_bound,
                    "upper_bound": reaction.upper_bound,
                }
            )

        return rows, {
            "status": "completed",
            "error_message": "",
            "n_exchange_reactions": len(rows),
        }
    except Exception as exc:
        logger.warning("Exchange FVA failed: %s", exc)
        return [], {
            "status": "failed",
            "error_message": str(exc),
            "n_exchange_reactions": len(exchange_reactions),
        }


def run_gene_essentiality(model, baseline_objective_value=None):
    """Run a single-gene deletion screen when it is meaningful."""
    if len(model.genes) == 0:
        return [], {
            "status": "skipped",
            "error_message": "Model has no genes.",
            "n_genes": 0,
            "n_essential_genes": 0,
        }

    if baseline_objective_value is None:
        baseline = run_fba_check(model)
        baseline_objective_value = baseline.get("objective_value")

    if baseline_objective_value is None or baseline_objective_value <= 1e-9:
        return [], {
            "status": "skipped",
            "error_message": "Baseline objective is zero or unavailable.",
            "n_genes": len(model.genes),
            "n_essential_genes": 0,
        }

    try:
        deletion = single_gene_deletion(model, processes=1)
        rows = []
        essential_count = 0

        for gene_key, row in deletion.iterrows():
            raw_gene_ids = row.get("ids", gene_key)
            growth = float(row.get("growth")) if row.get("growth") is not None else None
            essential = growth is not None and growth < baseline_objective_value * 0.01
            if essential:
                essential_count += 1
            rows.append(
                {
                    "gene_id": _normalize_gene_ids(raw_gene_ids),
                    "growth": growth,
                    "essential": essential,
                }
            )

        return rows, {
            "status": "completed",
            "error_message": "",
            "n_genes": len(model.genes),
            "n_essential_genes": essential_count,
        }
    except Exception as exc:
        logger.warning("Single-gene deletion failed: %s", exc)
        return [], {
            "status": "failed",
            "error_message": str(exc),
            "n_genes": len(model.genes),
            "n_essential_genes": 0,
        }
