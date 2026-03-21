"""Minimal COBRApy inspection helpers for the draft model.

This is a draft model inspection step before media optimisation.
"""


def summarize_cobra_model(model) -> dict:
    """Return a small summary for a loaded COBRApy model."""
    objective = ""
    expression = getattr(model.objective, "expression", None)
    if "bio1" in model.reactions and expression is not None and "bio1" in str(expression):
        objective = "bio1"
    elif expression is not None:
        objective = str(expression)

    return {
        "n_reactions": len(model.reactions),
        "n_metabolites": len(model.metabolites),
        "n_genes": len(model.genes),
        "objective": objective,
        "n_exchanges": len(model.exchanges),
    }


def get_exchange_table(model):
    """Return a small exchange-reaction table."""
    rows = [
        {
            "reaction_id": reaction.id,
            "reaction": reaction.reaction,
            "lower_bound": reaction.lower_bound,
            "upper_bound": reaction.upper_bound,
        }
        for reaction in model.exchanges
    ]

    try:
        import pandas as pd

        return pd.DataFrame(rows)
    except Exception:
        return rows


def run_baseline_optimization(model) -> dict:
    """Run one baseline optimization without changing the medium."""
    try:
        solution = model.optimize()
        return {
            "status": solution.status,
            "objective_value": solution.objective_value,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "objective_value": None,
            "error_message": str(exc),
        }
