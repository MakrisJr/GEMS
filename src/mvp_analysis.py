"""User-facing analysis modes for the hackathon MVP.

This is a draft model analysis layer before real media optimisation.
Theoretical and preset conditions are best used as benchmarking tools.
"""

from .bio2_benchmark import benchmark_bio2_conditions
from .oracle_growth import find_biomass_reaction
from .oracle_medium import build_debug_medium_library


DEFAULT_PRESET_LABELS = {
    "all_reactants": "full_precursor_set",
    "central_carbon_precursors": "rich_debug_medium",
    "lower_tca_precursors": "lower_tca_rescue",
    "upper_sugar_precursors": "upper_sugar_only",
    "energy_redox_only": "energy_redox_only",
}

DEFAULT_PRESET_DISPLAY_NAMES = {
    "all_reactants": "Full Precursor Set",
    "central_carbon_precursors": "Rich Debug Medium",
    "lower_tca_precursors": "Lower TCA Rescue",
    "upper_sugar_precursors": "Upper Sugar Only",
    "energy_redox_only": "Energy Redox Only",
}

DEFAULT_PRESET_DESCRIPTIONS = {
    "all_reactants": "all biomass reactants available as a rich debug benchmark",
    "central_carbon_precursors": "central carbon precursor rescue medium",
    "lower_tca_precursors": "lower glycolysis and TCA-linked precursor rescue medium",
    "upper_sugar_precursors": "upper sugar phosphate-only debug condition",
    "energy_redox_only": "energy and redox cofactors only",
}

BIO1_FALLBACK_PRESET_LABELS = {
    "reactants_plus_full_balance": "full_precursor_set",
    "reactants_plus_energy_balance": "rich_debug_medium",
    "reactants_plus_recycling_core": "lower_tca_rescue",
    "all_reactants": "upper_sugar_only",
    "energy_redox_only": "energy_redox_only",
}

BIO1_FALLBACK_DISPLAY_NAMES = {
    "reactants_plus_full_balance": "Full Biomass Support",
    "reactants_plus_energy_balance": "Balanced Biomass Support",
    "reactants_plus_recycling_core": "Recycling Core Support",
    "all_reactants": "Reactants Only",
    "energy_redox_only": "Energy Redox Only",
}

BIO1_FALLBACK_DESCRIPTIONS = {
    "reactants_plus_full_balance": "biomass reactants plus full product-balance support",
    "reactants_plus_energy_balance": "biomass reactants plus recycling support and partial balance products",
    "reactants_plus_recycling_core": "biomass reactants plus the key recycling product support",
    "all_reactants": "biomass reactants only",
    "energy_redox_only": "energy and redox cofactors only",
}


def _growth_key(row):
    value = row.get("bio2_rate")
    return float("-inf") if value is None else value


def _get_preset_spec(model, biomass_reaction_id: str = "bio2"):
    """Choose the user-facing preset library spec for the current biomass reaction."""
    biomass_reaction = find_biomass_reaction(model, preferred_id=biomass_reaction_id)
    if biomass_reaction.id == "bio1" and "bio2" not in model.reactions:
        return (
            BIO1_FALLBACK_PRESET_LABELS,
            BIO1_FALLBACK_DISPLAY_NAMES,
            BIO1_FALLBACK_DESCRIPTIONS,
        )
    return (
        DEFAULT_PRESET_LABELS,
        DEFAULT_PRESET_DISPLAY_NAMES,
        DEFAULT_PRESET_DESCRIPTIONS,
    )


def get_preset_condition_library(model, biomass_reaction_id: str = "bio2"):
    """Return a small user-facing preset library derived from debug conditions."""
    debug_library = build_debug_medium_library(model, biomass_reaction_id=biomass_reaction_id)
    preset_labels, preset_display_names, preset_descriptions = _get_preset_spec(
        model, biomass_reaction_id=biomass_reaction_id
    )
    preset_library = {}

    for source_name, target_name in preset_labels.items():
        if source_name not in debug_library:
            continue
        preset_library[target_name] = {
            "description": preset_descriptions[source_name],
            "display_name": preset_display_names[source_name],
            "metabolite_ids": list(debug_library[source_name].get("metabolite_ids", [])),
        }

    return preset_library


def run_theoretical_upper_bound(model, biomass_reaction_id: str = "bio2"):
    """Benchmark the best-case theoretical upper bound using the full oracle condition."""
    debug_library = build_debug_medium_library(model, biomass_reaction_id=biomass_reaction_id)
    full_oracle = debug_library["full_oracle"]
    result = benchmark_bio2_conditions(
        model,
        {
            "theoretical_upper_bound": {
                "description": (
                    "best-case benchmark showing how much biomass-like flux the draft model "
                    "can achieve under idealized input availability"
                ),
                "display_name": "Theoretical Upper Bound",
                "metabolite_ids": list(full_oracle.get("metabolite_ids", [])),
            }
        },
        biomass_reaction_id=biomass_reaction_id,
    )[0]
    result["mode"] = "theoretical_upper_bound"
    result["display_name"] = "Theoretical Upper Bound"
    return result


def run_preset_benchmark(model, biomass_reaction_id: str = "bio2"):
    """Benchmark the small preset condition library."""
    preset_library = get_preset_condition_library(model, biomass_reaction_id=biomass_reaction_id)
    results = benchmark_bio2_conditions(
        model, preset_library, biomass_reaction_id=biomass_reaction_id
    )
    results = sorted(results, key=_growth_key, reverse=True)
    for row in results:
        row["mode"] = "preset_conditions"
        row["display_name"] = preset_library.get(row["condition"], {}).get(
            "display_name",
            row.get("condition", ""),
        )
    return results


def parse_metabolite_ids(value: str):
    """Parse a comma-separated metabolite list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_custom_condition(
    model,
    biomass_reaction_id: str = "bio2",
    from_preset: str = "",
    metabolite_ids=None,
    add_metabolites=None,
    remove_metabolites=None,
):
    """Build one custom condition from a preset seed and/or explicit metabolites."""
    metabolite_ids = list(metabolite_ids or [])
    add_metabolites = list(add_metabolites or [])
    remove_metabolites = set(remove_metabolites or [])

    if from_preset:
        preset_library = get_preset_condition_library(model, biomass_reaction_id=biomass_reaction_id)
        if from_preset not in preset_library:
            raise ValueError(f"Unknown preset condition: {from_preset}")
        metabolite_ids = list(preset_library[from_preset].get("metabolite_ids", [])) + metabolite_ids

    combined = []
    seen = set()
    for metabolite_id in metabolite_ids + add_metabolites:
        if metabolite_id in seen or metabolite_id in remove_metabolites:
            continue
        seen.add(metabolite_id)
        combined.append(metabolite_id)

    return combined


def run_custom_condition(
    model,
    metabolite_ids,
    condition_name: str = "custom_condition",
    biomass_reaction_id: str = "bio2",
):
    """Benchmark one user-defined custom condition."""
    result = benchmark_bio2_conditions(
        model,
        {
            condition_name: {
                "description": "user-defined custom condition",
                "display_name": condition_name,
                "metabolite_ids": list(metabolite_ids),
            }
        },
        biomass_reaction_id=biomass_reaction_id,
    )[0]
    result["mode"] = "custom_condition"
    result["display_name"] = condition_name
    return result
