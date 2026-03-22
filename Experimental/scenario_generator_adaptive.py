import json
import random

BASE_MEDIUM = {
    "EX_glc__D_e": 10.0,
    "EX_nh4_e": 5.0,
    "EX_pi_e": 3.0,
    "EX_so4_e": 2.0,
    "EX_o2_e": 1000.0,  # fixed high: no oxygen limitation
}

RANGES = {
    "EX_glc__D_e": (2.0, 25.0),
    "EX_nh4_e": (1.0, 12.0),
    "EX_pi_e": (0.5, 8.0),
    "EX_so4_e": (0.5, 6.0),
    "temperature": (25.0, 34.0),
    "pH": (4.5, 7.0),
    "mixing": ("low", "medium", "high"),
}


def sample_uniform():
    medium = BASE_MEDIUM.copy()
    medium["EX_glc__D_e"] = random.uniform(*RANGES["EX_glc__D_e"])
    medium["EX_nh4_e"] = random.uniform(*RANGES["EX_nh4_e"])
    medium["EX_pi_e"] = random.uniform(*RANGES["EX_pi_e"])
    medium["EX_so4_e"] = random.uniform(*RANGES["EX_so4_e"])
    medium["EX_o2_e"] = 1000.0

    return {
        "medium": medium,
        "temperature": round(random.uniform(*RANGES["temperature"]), 2),
        "pH": round(random.uniform(*RANGES["pH"]), 2),
        "mixing": random.choice(RANGES["mixing"]),
        "search_stage": "explore",
    }


def local_perturb(best_scenario, frac=0.15):
    medium = best_scenario["medium"].copy()

    for k in ["EX_glc__D_e", "EX_nh4_e", "EX_pi_e", "EX_so4_e"]:
        lo, hi = RANGES[k]
        center = float(medium[k])
        width = frac * (hi - lo)
        medium[k] = min(hi, max(lo, random.uniform(center - width, center + width)))

    temp_lo, temp_hi = RANGES["temperature"]
    ph_lo, ph_hi = RANGES["pH"]

    temperature = min(
        temp_hi,
        max(temp_lo, random.uniform(best_scenario["temperature"] - 1.0, best_scenario["temperature"] + 1.0)),
    )
    pH = min(
        ph_hi,
        max(ph_lo, random.uniform(best_scenario["pH"] - 0.3, best_scenario["pH"] + 0.3)),
    )

    mixing = best_scenario["mixing"]
    if random.random() < 0.25:
        mixing = random.choice(RANGES["mixing"])

    medium["EX_o2_e"] = 1000.0

    return {
        "medium": medium,
        "temperature": round(temperature, 2),
        "pH": round(pH, 2),
        "mixing": mixing,
        "search_stage": "exploit",
    }


def generate_initial(n=40, out_path="dingo/scenarios.json"):
    scenarios = [sample_uniform() for _ in range(n)]
    with open(out_path, "w") as f:
        json.dump(scenarios, f, indent=2)
    print(f"[INFO] Generated {n} exploration scenarios -> {out_path}")


def generate_from_top(top_scenarios, n_per_top=8, out_path="dingo/scenarios_refined.json"):
    scenarios = []
    for s in top_scenarios:
        for _ in range(n_per_top):
            scenarios.append(local_perturb(s))
    with open(out_path, "w") as f:
        json.dump(scenarios, f, indent=2)
    print(f"[INFO] Generated {len(scenarios)} exploitation scenarios -> {out_path}")


if __name__ == "__main__":
    generate_initial(20)