#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
import cobra

from PolytopeSampler import PolytopeSampler
from polyround_preproces import polyround_preprocess
from cobra.flux_analysis import flux_variability_analysis


def interior_sample(A, b, ess=1000):
    S = PolytopeSampler.sample_from_polytope(A=A, b=b, ess=ess)
    S = np.asarray(S, dtype=np.float64)
    d = A.shape[1]

    if S.shape[0] == d:
        S = S.T
    elif S.shape[1] != d:
        raise RuntimeError(f"Unexpected shape {S.shape}, expected (*, {d})")

    return S


def apply_model_specific_medium(model, scenario):
    """
    Apply scenario["medium"] using model-specific reaction IDs.

    Rule:
    - if a reaction already allows negative flux, treat uptake as lower_bound = -value
    - otherwise treat the controllable bound as upper_bound = value

    This is safer for fungal GEMs where many uptake/transport reactions are
    irreversible and controlled through upper bounds.
    """
    for rxn_id, value in scenario["medium"].items():
        if rxn_id not in model.reactions:
            print(f"[WARN] reaction {rxn_id} not found, skipping")
            continue

        rxn = model.reactions.get_by_id(rxn_id)
        value = abs(float(value))

        if rxn.lower_bound < 0:
            rxn.lower_bound = -value
        else:
            rxn.upper_bound = value


def build_dataset(model_path, scenarios_path, biomass_rxn, out_path="results/dataset.csv"):
    with open(scenarios_path) as f:
        scenarios = json.load(f)

    rows = []
    os.makedirs("results", exist_ok=True)

    for i, scenario in enumerate(scenarios):
        print(f"[INFO] scenario {i+1}/{len(scenarios)}")

        try:
            model = cobra.io.read_sbml_model(model_path)

            # Apply model-specific medium
            apply_model_specific_medium(model, scenario)

            model.objective = biomass_rxn
            sol = model.optimize()

            if sol.status != "optimal" or sol.objective_value < 1e-8:
                print("[WARN] infeasible or zero growth -> skip")
                continue

            growth = float(sol.objective_value)
            print(f"[INFO] feasible growth={growth:.6f}")

            fluxes = sol.fluxes
            reaction_ids = [r.id for r in model.reactions]

            # FVA summaries
            try:
                fva = flux_variability_analysis(model, fraction_of_optimum=0.9)
                fva_range = float((fva["maximum"] - fva["minimum"]).mean())
            except Exception as e:
                print(f"[WARN] FVA failed for scenario {i}: {e}")
                fva_range = np.nan

            # Polytope preprocessing
            tmp_path = f"tmp_dataset_builder_{i}.xml"
            cobra.io.write_sbml_model(model, tmp_path)

            try:
                P, _ = polyround_preprocess(tmp_path)
                A = np.asarray(P.A, dtype=float)
                b = np.asarray(P.b, dtype=float)
            except Exception as e:
                print(f"[WARN] PolyRound failed for scenario {i}: {e}")
                continue
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # Interior sampling
            try:
                Z = interior_sample(A, b, ess=2000)
            except Exception as e:
                print(f"[WARN] Sampling failed for scenario {i}: {e}")
                continue

            # Back-transform
            try:
                V = []
                for z in Z:
                    z = np.asarray(z, dtype=np.float64).reshape(-1)
                    v = P.back_transform(z)
                    v = np.asarray(v, dtype=np.float64).reshape(-1)
                    V.append(v)
                V = np.vstack(V)
            except Exception as e:
                print(f"[WARN] Back-transform failed for scenario {i}: {e}")
                continue

            if V.shape[1] != len(reaction_ids):
                print(
                    f"[WARN] Back-transformed sample dimension {V.shape[1]} does not match "
                    f"number of model reactions {len(reaction_ids)} -> skip"
                )
                continue

            if biomass_rxn not in reaction_ids:
                print(f"[WARN] Biomass reaction {biomass_rxn} not found in model reaction list -> skip")
                continue

            # Geometry features
            cov = np.cov(V, rowvar=False)
            eig = np.linalg.eigvalsh(cov)
            eig = np.maximum(eig, 1e-12)

            logvol = float(np.sum(np.log(eig)))
            anis_log = float(np.log(np.max(eig) / (np.median(eig) + 1e-12)))
            flux_std = float(np.mean(np.std(V, axis=0)))

            biomass_j = reaction_ids.index(biomass_rxn)
            biomass_flux_mean = float(np.mean(V[:, biomass_j]))
            biomass_std = float(np.std(V[:, biomass_j]))

            # Fungal first-pass: disable yeast-specific byproducts for now
            # Fungal excretion reactions (A. oryzae)
            byproduct_map = {
                "ethanol": "r2325",
                "acetate": "r2343",
                "formate": "r2344",
                "d_lactate": "r2348",
                "l_lactate": "r2349",
                "succinate": "r2342",
                "pyruvate": "r2341",
                "citrate": "r2335",
                "oxalate": "r2339",
                "malate": "r2333",
            }

            byprod_fluxes = {}
            for name, rid in byproduct_map.items():
                if rid in reaction_ids:
                    j = reaction_ids.index(rid)
                    byprod_fluxes[name] = float(np.mean(np.maximum(V[:, j], 0.0)))
                else:
                    byprod_fluxes[name] = 0.0

            byproduct_mean = float(np.mean(list(byprod_fluxes.values())))
            byproduct_total = float(np.sum(list(byprod_fluxes.values())))

            # Uptake proxies from scenario medium, since fungal boundary reactions
            # may not follow yeast-style EX_* names
            glucose_uptake = float(scenario["medium"].get("r2205", 0.0))
            oxygen_uptake = float(scenario["medium"].get("r2202", 0.0))
            phosphate_uptake = float(scenario["medium"].get("r2203", 0.0))
            sulfate_uptake = float(scenario["medium"].get("r2093", 0.0))
            ammonium_uptake = float(scenario["medium"].get("r2095", 0.0))

            biomass_yield = growth / max(glucose_uptake, 1e-8)
            clean_score = growth / (1.0 + byproduct_total)

            rows.append(
                {
                    "scenario": i,
                    "search_stage": scenario.get("search_stage", "unknown"),

                    # fungal medium controls
                    "glucose": glucose_uptake,
                    "ammonium": ammonium_uptake,
                    "phosphate": phosphate_uptake,
                    "sulfate": sulfate_uptake,
                    "oxygen_bound": oxygen_uptake,

                    # process variables
                    "temperature": float(scenario["temperature"]),
                    "pH": float(scenario["pH"]),
                    "mixing": scenario["mixing"],

                    # metabolic / geometric outputs
                    "growth": growth,
                    "fba_growth": growth,
                    "fva_range": fva_range,
                    "log_volume": logvol,
                    "anisotropy_log": anis_log,
                    "flux_std": flux_std,
                    "biomass_flux_mean": biomass_flux_mean,
                    "biomass_std": biomass_std,

                    # uptake proxies
                    "glucose_uptake": glucose_uptake,
                    "oxygen_uptake": oxygen_uptake,
                    "ammonium_uptake": ammonium_uptake,
                    "phosphate_uptake": phosphate_uptake,
                    "sulfate_uptake": sulfate_uptake,

                    "ethanol_excr": byprod_fluxes["ethanol"],
                    "acetate_excr": byprod_fluxes["acetate"],
                    "formate_excr": byprod_fluxes["formate"],
                    "d_lactate_excr": byprod_fluxes["d_lactate"],
                    "l_lactate_excr": byprod_fluxes["l_lactate"],
                    "succinate_excr": byprod_fluxes["succinate"],
                    "pyruvate_excr": byprod_fluxes["pyruvate"],
                    "citrate_excr": byprod_fluxes["citrate"],
                    "oxalate_excr": byprod_fluxes["oxalate"],
                    "malate_excr": byprod_fluxes["malate"],

                    # objective-side summaries
                    "biomass_yield": biomass_yield,
                    "byproduct_mean": byproduct_mean,
                    "byproduct_total": byproduct_total,
                    "clean_score": clean_score,
                }
            )

            # Save progress after every successful scenario
            pd.DataFrame(rows).to_csv(out_path, index=False)

        except Exception as e:
            print(f"[WARN] scenario {i} crashed: {e}")
            continue

    if not rows:
        print("[WARN] No valid scenarios kept; dataset is empty.")
        pd.DataFrame().to_csv(out_path, index=False)
        return

    df = pd.DataFrame(rows)

    def norm01(x):
        x = np.asarray(x, dtype=float)
        lo, hi = np.min(x), np.max(x)
        if hi - lo < 1e-12:
            return np.ones_like(x)
        return (x - lo) / (hi - lo)

    df["growth_norm"] = norm01(df["growth"])
    df["biomass_norm"] = norm01(df["biomass_flux_mean"])
    df["yield_norm"] = norm01(df["biomass_yield"])
    df["byproduct_penalty_norm"] = norm01(df["byproduct_total"])

    df["overall_rank_score"] = (
        0.40 * df["growth_norm"]
        + 0.25 * df["biomass_norm"]
        + 0.20 * df["yield_norm"]
        - 0.35 * df["byproduct_penalty_norm"]
    )

    df = df.sort_values("overall_rank_score", ascending=False).reset_index(drop=True)
    df.to_csv(out_path, index=False)

    print(f"[INFO] dataset saved -> {out_path}")
    print(f"[INFO] valid scenarios kept = {len(df)}")


if __name__ == "__main__":
    build_dataset(
        model_path="dingo/A_oryzae_optimized.xml",
        scenarios_path="dingo/scenarios_fungi.json",
        biomass_rxn="r2359",
    )