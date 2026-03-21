"""Minimal COBRApy debugging helpers for draft-model growth checks."""


def inspect_objective(model):
    """Return the current objective expression as a string."""
    expression = getattr(model.objective, "expression", None)
    return str(expression) if expression is not None else ""


def inspect_open_medium(model):
    """Return the currently open medium dictionary."""
    return dict(model.medium)


def inspect_candidate_biomass_reactions(model):
    """Return reactions whose id or name suggests a biomass objective."""
    candidates = []
    for reaction in model.reactions:
        search_text = f"{reaction.id} {reaction.name}".lower()
        if "bio" in search_text or "biomass" in search_text:
            candidates.append(
                {
                    "reaction_id": reaction.id,
                    "name": reaction.name,
                    "reaction": reaction.reaction,
                    "lower_bound": reaction.lower_bound,
                    "upper_bound": reaction.upper_bound,
                }
            )
    return candidates


def run_debug_optimization(model):
    """Run a plain optimization and return status and objective value."""
    solution = model.optimize()
    return {
        "status": solution.status,
        "objective_value": solution.objective_value,
    }
