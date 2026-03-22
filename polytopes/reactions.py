import sys
import cobra

model = cobra.io.read_sbml_model(sys.argv[1])
patterns = sys.argv[2:]

for p in patterns:
    print(f"\n=== pattern: {p} ===")
    found = False
    for r in model.reactions:
        txt = f"{r.id} {r.name}".lower()
        if p.lower() in txt:
            print(r.id, "|", r.name, "| lb =", r.lower_bound, "| ub =", r.upper_bound)
            found = True
    if not found:
        print("none")