"""Minimal exchange-space diagnostics for the draft COBRA model.

This is a draft model inspection step before media optimisation.
"""

import re


def _carbon_count(formula: str):
    if not formula:
        return None

    count = 0
    for element, amount in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        if element == "C":
            count += int(amount) if amount else 1
    return count


def _is_plausible_carbon_source(name: str, formula: str, carbon_count):
    if not carbon_count or carbon_count <= 0:
        return False

    text = f"{name or ''} {formula or ''}".lower()
    excluded_terms = [
        "co2",
        "carbon dioxide",
        "carbonate",
        "bicarbonate",
        "menaquinone",
        "menaquinol",
        "ubiquinone",
        "ubiquinol",
        "cytochrome",
        "heme",
        "quinone",
        "quinol",
    ]
    return not any(term in text for term in excluded_terms)


def summarize_exchange_metabolites(model):
    """Return a small annotated table for exchange metabolites."""
    rows = []

    for reaction in model.exchanges:
        metabolites = list(reaction.metabolites)
        metabolite = metabolites[0] if metabolites else None
        name = metabolite.name if metabolite is not None else ""
        formula = metabolite.formula if metabolite is not None else ""
        carbon_count = _carbon_count(formula)
        rows.append(
            {
                "reaction_id": reaction.id,
                "metabolite_id": metabolite.id if metabolite is not None else "",
                "metabolite_name": name,
                "formula": formula or "",
                "carbon_count": carbon_count,
                "lower_bound": reaction.lower_bound,
                "upper_bound": reaction.upper_bound,
                "plausible_carbon_source": _is_plausible_carbon_source(name, formula, carbon_count),
            }
        )

    return rows


def flag_plausible_carbon_sources(exchange_rows):
    """Summarize whether the exchange space includes plausible carbon sources."""
    plausible = [row for row in exchange_rows if row["plausible_carbon_source"]]
    carbon_containing = [row for row in exchange_rows if row["carbon_count"] and row["carbon_count"] > 0]

    return {
        "n_exchanges": len(exchange_rows),
        "n_carbon_containing_exchanges": len(carbon_containing),
        "n_plausible_carbon_sources": len(plausible),
        "plausible_carbon_source_ids": [row["reaction_id"] for row in plausible],
        "plausible_carbon_source_names": [row["metabolite_name"] for row in plausible],
        "has_plausible_carbon_source": len(plausible) > 0,
    }
