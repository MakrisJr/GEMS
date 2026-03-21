"""Semi-artificial rich debug medium screening derived from oracle growth.

This is a draft model debugging step before media optimisation.
"""

from .oracle_growth import find_biomass_reaction, run_oracle_growth


ENERGY_REDOX_IDS = {
    "cpd00002_c0",  # ATP
    "cpd00001_c0",  # H2O
    "cpd00005_c0",  # NADPH
    "cpd00003_c0",  # NAD
    "cpd00008_c0",  # ADP
    "cpd00009_c0",  # phosphate
    "cpd00067_c0",  # H+
    "cpd00010_c0",  # CoA
    "cpd00006_c0",  # NADP
    "cpd00004_c0",  # NADH
}

UPPER_SUGAR_IDS = {
    "cpd00079_c0",  # glucose-6-phosphate
    "cpd00072_c0",  # fructose-6-phosphate
    "cpd00101_c0",  # ribose-5-phosphate
    "cpd00236_c0",  # erythrose-4-phosphate
    "cpd00102_c0",  # glyceraldehyde-3-phosphate
}

LOWER_TCA_IDS = {
    "cpd00169_c0",  # 3-phosphoglycerate
    "cpd00061_c0",  # phosphoenolpyruvate
    "cpd00020_c0",  # pyruvate
    "cpd00022_c0",  # acetyl-CoA
    "cpd00032_c0",  # oxaloacetate
    "cpd00024_c0",  # 2-oxoglutarate
}


def describe_condition_metabolites(model, metabolite_ids):
    """Return readable metabolite details for a debug condition."""
    details = []
    for metabolite_id in metabolite_ids:
        if metabolite_id not in model.metabolites:
            details.append(
                {
                    "metabolite_id": metabolite_id,
                    "metabolite_name": "",
                }
            )
            continue

        metabolite = model.metabolites.get_by_id(metabolite_id)
        details.append(
            {
                "metabolite_id": metabolite.id,
                "metabolite_name": metabolite.name,
            }
        )
    return details


def build_debug_medium_library(model, biomass_reaction_id: str = "bio2"):
    """Build a tiny set of oracle-derived debug-medium conditions."""
    oracle_result = run_oracle_growth(model, biomass_reaction_id=biomass_reaction_id)
    full_oracle_ids = [row["metabolite_id"] for row in oracle_result["added_boundaries"]]

    biomass_reaction = find_biomass_reaction(model, preferred_id=biomass_reaction_id)
    reactant_ids = [
        metabolite.id
        for metabolite, coefficient in biomass_reaction.metabolites.items()
        if coefficient < 0
    ]

    central_carbon_ids = [met_id for met_id in reactant_ids if met_id not in ENERGY_REDOX_IDS]
    upper_sugar_ids = [met_id for met_id in reactant_ids if met_id in UPPER_SUGAR_IDS]
    lower_tca_ids = [met_id for met_id in reactant_ids if met_id in LOWER_TCA_IDS]
    energy_redox_ids = [met_id for met_id in full_oracle_ids if met_id in ENERGY_REDOX_IDS]

    return {
        "full_oracle": {
            "description": "all oracle-added metabolites, including products",
            "metabolite_ids": full_oracle_ids,
        },
        "all_reactants": {
            "description": "all biomass reactants only",
            "metabolite_ids": reactant_ids,
        },
        "central_carbon_precursors": {
            "description": "central carbon and precursor metabolites",
            "metabolite_ids": central_carbon_ids,
        },
        "lower_tca_precursors": {
            "description": "lower glycolysis and TCA-linked precursors",
            "metabolite_ids": lower_tca_ids,
        },
        "upper_sugar_precursors": {
            "description": "upper sugar phosphate precursors",
            "metabolite_ids": upper_sugar_ids,
        },
        "energy_redox_only": {
            "description": "energy and redox cofactors only",
            "metabolite_ids": energy_redox_ids,
        },
    }


def screen_debug_media(model, medium_library, biomass_reaction_id: str = "bio2"):
    """Screen oracle-derived debug media against a biomass-like objective."""
    results = []

    for condition, config in medium_library.items():
        with model as debug_model:
            biomass_reaction = find_biomass_reaction(debug_model, preferred_id=biomass_reaction_id)
            added_boundary_ids = []
            missing_metabolite_ids = []
            metabolite_ids = list(config.get("metabolite_ids", []))
            metabolite_details = describe_condition_metabolites(debug_model, metabolite_ids)

            try:
                for metabolite_id in metabolite_ids:
                    if metabolite_id not in debug_model.metabolites:
                        missing_metabolite_ids.append(metabolite_id)
                        continue

                    boundary = debug_model.add_boundary(
                        debug_model.metabolites.get_by_id(metabolite_id), type="sink"
                    )
                    added_boundary_ids.append(boundary.id)

                debug_model.objective = biomass_reaction.id
                solution = debug_model.optimize()
                predicted_growth = solution.objective_value
                status = solution.status
            except Exception as exc:
                predicted_growth = None
                status = "failed"
                results.append(
                    {
                        "condition": condition,
                        "description": config.get("description", ""),
                        "biomass_reaction_id": biomass_reaction_id,
                        "predicted_growth": predicted_growth,
                        "status": status,
                        "metabolite_ids": metabolite_ids,
                        "metabolite_details": metabolite_details,
                        "n_added_boundaries": len(added_boundary_ids),
                        "added_boundary_ids": added_boundary_ids,
                        "missing_metabolite_ids": missing_metabolite_ids,
                        "error_message": str(exc),
                    }
                )
                continue

            results.append(
                {
                    "condition": condition,
                    "description": config.get("description", ""),
                    "biomass_reaction_id": biomass_reaction.id,
                    "predicted_growth": predicted_growth,
                    "status": status,
                    "metabolite_ids": metabolite_ids,
                    "metabolite_details": metabolite_details,
                    "n_added_boundaries": len(added_boundary_ids),
                    "added_boundary_ids": added_boundary_ids,
                    "missing_metabolite_ids": missing_metabolite_ids,
                }
            )

    return results
