import sys
import cobra

model_path = sys.argv[1]
biomass_rxn = sys.argv[2]

model = cobra.io.read_sbml_model(model_path)

print("Model:", model_path)
print("Loaded reactions:", len(model.reactions))
print("Current objective expression:", model.objective.expression)

ids = set(r.id for r in model.reactions)

if biomass_rxn not in ids:
    print(f"\n[ERROR] Reaction '{biomass_rxn}' not found in loaded model.\n")
    print("Candidate biomass/growth reactions:")
    found = False
    for r in model.reactions:
        text = (r.id + " " + r.name).lower()
        if "biomass" in text or "growth" in text:
            print(f"  {r.id} | {r.name}")
            found = True
    if not found:
        print("  [none found by name search]")
    sys.exit(1)

model.objective = biomass_rxn
sol = model.optimize()

print("\nChosen biomass reaction:", biomass_rxn)
print("Status:", sol.status)
print("Objective value:", sol.objective_value)