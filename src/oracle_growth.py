"""Minimal oracle-growth debugging for the draft COBRA model.

This is a draft model debugging step before media optimisation.
"""


def find_biomass_reaction(model, preferred_id: str = "bio2"):
    """Choose a biomass-like reaction, preferring bio2 when present."""
    if preferred_id in model.reactions:
        return model.reactions.get_by_id(preferred_id)

    for reaction in model.reactions:
        search_text = f"{reaction.id} {reaction.name}".lower()
        if "bio" in search_text or "biomass" in search_text:
            return reaction

    raise ValueError("No biomass-like reaction found in the model.")


def run_oracle_growth(model, biomass_reaction_id: str = "bio2"):
    """Add temporary sink boundaries around a biomass reaction and optimize it."""
    biomass_reaction = find_biomass_reaction(model, preferred_id=biomass_reaction_id)

    with model as oracle_model:
        biomass_reaction = oracle_model.reactions.get_by_id(biomass_reaction.id)
        added_boundaries = []

        for metabolite in biomass_reaction.metabolites:
            existing_boundary = any(
                reaction.id.startswith(("EX_", "DM_", "SK_"))
                for reaction in metabolite.reactions
            )
            if existing_boundary:
                continue

            boundary = oracle_model.add_boundary(metabolite, type="sink")
            added_boundaries.append(
                {
                    "boundary_id": boundary.id,
                    "metabolite_id": metabolite.id,
                    "metabolite_name": metabolite.name,
                    "lower_bound": boundary.lower_bound,
                    "upper_bound": boundary.upper_bound,
                }
            )

        oracle_model.objective = biomass_reaction.id
        solution = oracle_model.optimize()

        return {
            "biomass_reaction_id": biomass_reaction.id,
            "biomass_reaction": biomass_reaction.reaction,
            "status": solution.status,
            "objective_value": solution.objective_value,
            "added_boundaries": added_boundaries,
            "n_added_boundaries": len(added_boundaries),
        }
