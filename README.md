# fungal_modelseed_pipeline

Minimal local MVP for fungal draft metabolic-model benchmarking with ModelSEEDpy and COBRApy.

## What Goes In
- Protein FASTA (`.faa`)
- Model ID

## What Comes Out
- Draft GEM export (`model.xml` when possible)
- Ranked condition outputs
- Plots for theoretical, preset, and custom analyses
- Optional validation outputs for the draft model

## Official Commands
These are the 3 commands to treat as the main product interface.

1. Build and export the draft model

```bash
python scripts/run_mvp_pipeline.py --input ncbi_dataset/data/GCA_000182925.2/protein.faa --model-id test_model_rast --use-rast
```

To try the local fungal template instead of the built-in core template:

```bash
python scripts/run_mvp_pipeline.py --input ncbi_dataset/data/GCA_000182925.2/protein.faa --model-id test_model_fungi --use-rast --template-name fungi --template-source local
```

2. Run one analysis mode

```bash
python scripts/analyze_mvp.py --model-dir data/models/test_model_rast --mode theoretical
python scripts/analyze_mvp.py --model-dir data/models/test_model_rast --mode preset
python scripts/analyze_mvp.py --model-dir data/models/test_model_rast --mode custom --from-preset rich_debug_medium --condition-name my_custom_condition
```

3. Run validation

```bash
python scripts/validate_mvp.py --model-dir data/models/test_model_rast
python scripts/validate_mvp.py --model-dir data/models/test_model_rast --mode theoretical_upper_bound --biomass-reaction bio2
```

## Analysis Modes
- `Theoretical Upper Bound`
  Best-case benchmark showing how much biomass-like flux the draft model can achieve under idealized input availability.
- `Preset Conditions`
  Small pre-defined condition library for side-by-side benchmarking.
- `Custom Condition`
  User-defined condition starting from a preset or explicit metabolite list.
- `Validation`
  Draft-model quality checks such as baseline FBA, dead-end metabolites, exchange FVA, and gene essentiality.

## Recommended Demo Outputs
If you are presenting the project live, these are the most useful files to open:

- [mvp_mode_comparison.png](/home/constantinos/projects/Biohacathon/fungal_modelseed_pipeline/data/models/test_model_rast/mvp_mode_comparison.png)
- [preset_conditions.png](/home/constantinos/projects/Biohacathon/fungal_modelseed_pipeline/data/models/test_model_rast/preset_conditions.png)
- [theoretical_upper_bound_conditions.txt](/home/constantinos/projects/Biohacathon/fungal_modelseed_pipeline/data/models/test_model_rast/theoretical_upper_bound_conditions.txt)
- [theoretical_upper_bound_validation_dashboard.png](/home/constantinos/projects/Biohacathon/fungal_modelseed_pipeline/data/models/test_model_rast/theoretical_upper_bound_validation_dashboard.png)

## Important Notes
- This is a draft-model pipeline.
- `Theoretical Upper Bound` is a best-case benchmark, not a wet-lab medium recommendation.
- `Preset Conditions` and `Custom Condition` are screening tools for comparing model behavior.
- Current realistic growth predictions may stay at `0.0` for sparse draft models.

## Current Scope
- Build a draft model from protein FASTA
- Choose between the built-in core template and the local fungal template at build time
- Export it for COBRApy
- Benchmark a small set of conditions
- Inspect theoretical, preset, and custom outputs
- Run optional validation checks, including a theoretical upper-bound validation mode

## Planned Next Steps
- More realistic media benchmarking
- Cleaner UI
- Targeted product benchmarking
