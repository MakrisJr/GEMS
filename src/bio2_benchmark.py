"""Minimal bio2 benchmarking across oracle-derived debug conditions.

This is a draft model debugging step before media optimisation.
The reported yield is a debug proxy based on total added boundary flux.
"""

from .oracle_growth import find_biomass_reaction


def benchmark_bio2_conditions(model, medium_library, biomass_reaction_id: str = "bio2"):
    """Benchmark bio2-like rate and a simple yield proxy across conditions."""
    results = []

    for condition, config in medium_library.items():
        with model as debug_model:
            biomass_reaction = find_biomass_reaction(debug_model, preferred_id=biomass_reaction_id)
            metabolite_ids = list(config.get("metabolite_ids", []))
            added_boundaries = []
            missing_metabolite_ids = []

            try:
                for metabolite_id in metabolite_ids:
                    if metabolite_id not in debug_model.metabolites:
                        missing_metabolite_ids.append(metabolite_id)
                        continue

                    metabolite = debug_model.metabolites.get_by_id(metabolite_id)
                    boundary = debug_model.add_boundary(metabolite, type="sink")
                    added_boundaries.append((metabolite, boundary))

                debug_model.objective = biomass_reaction.id
                solution = debug_model.optimize()

                boundary_fluxes = []
                total_added_boundary_flux = 0.0
                for metabolite, boundary in added_boundaries:
                    flux = float(solution.fluxes.get(boundary.id, 0.0))
                    abs_flux = abs(flux)
                    total_added_boundary_flux += abs_flux
                    boundary_fluxes.append(
                        {
                            "boundary_id": boundary.id,
                            "metabolite_id": metabolite.id,
                            "metabolite_name": metabolite.name,
                            "flux": flux,
                            "abs_flux": abs_flux,
                        }
                    )

                bio2_rate = solution.objective_value
                bio2_yield = None
                if total_added_boundary_flux > 0 and bio2_rate is not None:
                    bio2_yield = bio2_rate / total_added_boundary_flux

                results.append(
                    {
                        "condition": condition,
                        "display_name": config.get("display_name", condition),
                        "description": config.get("description", ""),
                        "biomass_reaction_id": biomass_reaction.id,
                        "bio2_rate": bio2_rate,
                        "status": solution.status,
                        "bio2_yield_on_total_added_flux": bio2_yield,
                        "total_added_boundary_flux": total_added_boundary_flux,
                        "n_added_boundaries": len(added_boundaries),
                        "metabolite_ids": metabolite_ids,
                        "missing_metabolite_ids": missing_metabolite_ids,
                        "boundary_fluxes": boundary_fluxes,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "condition": condition,
                        "display_name": config.get("display_name", condition),
                        "description": config.get("description", ""),
                        "biomass_reaction_id": biomass_reaction.id,
                        "bio2_rate": None,
                        "status": "failed",
                        "bio2_yield_on_total_added_flux": None,
                        "total_added_boundary_flux": 0.0,
                        "n_added_boundaries": len(added_boundaries),
                        "metabolite_ids": metabolite_ids,
                        "missing_metabolite_ids": missing_metabolite_ids,
                        "boundary_fluxes": [],
                        "error_message": str(exc),
                    }
                )

    return results
