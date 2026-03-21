# UI Update Instructions

This file explains how the existing UI should be updated to match the current
fungal GEM MVP.

Use the current UI code as the starting point:
- `frontend_app.py`
- `backend/main.py`
- `backend/pipeline_runner.py`

Do not redesign the product flow from scratch. Keep the existing Streamlit +
FastAPI structure, but change what is shown and which scripts/outputs are
treated as the default path.

## 1. New Default Product Flow

The old UI is still centered around the older step-by-step pipeline:
- `prepare_input.py`
- `first_modelseed_step.py`
- `build_draft_model.py`
- `gapfill_and_export_model.py`
- `inspect_with_cobra.py`
- plus many debugging tabs

The new default UI should instead be centered around the official MVP flow:

1. `run_mvp_pipeline.py`
2. `analyze_mvp.py --mode theoretical`
3. `analyze_mvp.py --mode preset`
4. `validate_mvp.py --mode theoretical_upper_bound --biomass-reaction bio2`

Optional user action:
5. `analyze_mvp.py --mode custom`

Important:
- treat `Custom Condition` as optional
- treat `Theoretical Upper Bound`, `Preset Conditions`, and `Validation` as the
  main default outputs

## 2. User-Facing Naming To Use Everywhere

Use these exact labels in the UI:

- `Theoretical Upper Bound`
- `Preset Conditions`
- `Custom Condition`
- `Validation`

Avoid using these as main section titles:
- `oracle`
- `oracle medium`
- `debug medium`
- `rescue medium`
- `bio2 benchmark`

Those can appear only in advanced details if needed.

## 3. Main UI Layout To Show

### Section A: Overview

Use:
- `data/models/<model_id>/mvp_summary.json`

Show summary cards:
- `Model ID`
- `Reactions`
- `Metabolites`
- `Genes`
- `Exchanges`
- `Baseline status`
- `Baseline objective value`

Hero plot:
- `data/models/<model_id>/mvp_mode_comparison.png`

This should be the main chart on the page.

### Section B: Theoretical Upper Bound

Show:
- `data/models/<model_id>/theoretical_upper_bound.png`
- `data/models/<model_id>/theoretical_upper_bound.txt`
- `data/models/<model_id>/theoretical_upper_bound_conditions.csv`

Summary values to display:
- `Condition`
- `Status`
- `Predicted bio2 rate`
- `Yield proxy`
- `Temporary boundaries added`

Table to display from `theoretical_upper_bound_conditions.csv`:
- `metabolite_name`
- `metabolite_id`
- `boundary_id`
- `flux`
- `abs_flux`

Important UI note:
- clearly label this section as:
  `Best-case benchmark, not a wet-lab medium recommendation`

### Section C: Preset Conditions

Show:
- `data/models/<model_id>/preset_conditions.png`
- `data/models/<model_id>/preset_conditions.csv`
- `data/models/<model_id>/preset_conditions.txt`

Use this table as the main ranked table:
- `display_name`
- `description`
- `bio2_rate`
- `bio2_yield_on_total_added_flux`
- `status`
- `n_added_boundaries`

This should be the main comparison table in the UI.

### Section D: Custom Condition

This should stay in the UI, but not as the default first screen.

Show:
- `data/models/<model_id>/custom_condition_<name>.png`
- `data/models/<model_id>/custom_condition_<name>.json`
- `data/models/<model_id>/custom_condition_<name>.txt`

Controls to keep:
- custom condition name
- preset seed selector
- metabolite ID input

Recommended preset seed to expose first:
- `rich_debug_medium`

Summary values to show:
- `Condition`
- `Status`
- `Predicted bio2 rate`
- `Yield proxy`

Also show the metabolite list used.

### Section E: Validation

Show:
- `data/models/<model_id>/theoretical_upper_bound_validation_dashboard.png`
- `data/models/<model_id>/theoretical_upper_bound_validation_summary.txt`
- `data/models/<model_id>/theoretical_upper_bound_validation_summary.json`

Display these values:
- `FBA status`
- `Objective value`
- `Dead-end metabolites`
- `Produced only`
- `Consumed only`
- `Exchange reactions tested`
- `Gene essentiality status`
- `Essential genes found`

This section should be framed as:
- `Draft-model quality checks`

## 4. Exact Files To Use As Main UI Data Sources

Use these files as the primary sources for the new UI:

- `mvp_summary.json`
- `mvp_mode_comparison.png`
- `theoretical_upper_bound.json`
- `theoretical_upper_bound.txt`
- `theoretical_upper_bound_conditions.csv`
- `preset_conditions.csv`
- `preset_conditions.png`
- `preset_conditions.txt`
- `custom_condition_<name>.json`
- `custom_condition_<name>.png`
- `custom_condition_<name>.txt`
- `theoretical_upper_bound_validation_summary.json`
- `theoretical_upper_bound_validation_summary.txt`
- `theoretical_upper_bound_validation_dashboard.png`

## 5. What To Remove Or Hide From The Main UI

These are still useful internally, but should not be front-and-center:

- `prepare_input`
- `first_modelseed_step`
- `screen_media`
- `debug_growth`
- `run_oracle_growth`
- `screen_oracle_medium`
- `benchmark_bio2`
- `inspect_oracle_condition`
- raw `exchange_fva.csv`
- raw `dead_end_metabolites.csv`
- raw `exchange_diagnosis.json`
- raw `EX_` and `SK_` IDs as the first thing a user sees

Recommendation:
- move these to an `Advanced` expander or an `Internal Debug` tab
- do not keep them as the main numbered tab flow

## 6. Changes Needed In `frontend_app.py`

The current Streamlit file still reflects the older pipeline.

Change these parts:

1. Replace the current numbered step-tab layout with these sections:
- `Overview`
- `Theoretical Upper Bound`
- `Preset Conditions`
- `Custom Condition`
- `Validation`
- `Advanced Files`

2. Keep the file upload flow, but update the main story after upload:
- show summary cards first
- show `mvp_mode_comparison.png` next
- show preset and theoretical sections next

3. Keep custom-condition support, but move it below preset conditions

4. Do not make old debug steps the primary tabs

5. Use the current report-style `.txt` outputs in expandable text blocks

6. Prefer the newer display names from `preset_conditions.csv`

## 7. Changes Needed In `backend/pipeline_runner.py`

The current backend runner still executes the old long script chain.

Update the default backend run flow so it executes:

1. `scripts/run_mvp_pipeline.py`
2. `scripts/analyze_mvp.py --mode theoretical`
3. `scripts/analyze_mvp.py --mode preset`
4. `scripts/validate_mvp.py --mode theoretical_upper_bound --biomass-reaction bio2`

Optional custom-condition actions can remain separate.

Reason:
- this matches the current MVP product story
- it produces the exact files the new UI should show

## 8. Changes Needed In `backend/main.py`

Recommended backend behavior:

- `/run` should return the `model_id` and the status of the default MVP flow
- optional future endpoints can support:
  - custom condition analysis
  - rerunning validation

But for now the main backend requirement is:
- make sure `/run` drives the new default MVP outputs

## 9. Example Files To Use During UI Development

Use this directory as the reference example:

- `data/models/final_demo_run/`

Most useful files there:
- `mvp_mode_comparison.png`
- `mvp_summary.txt`
- `theoretical_upper_bound.txt`
- `theoretical_upper_bound_conditions.csv`
- `preset_conditions.csv`
- `preset_conditions.png`
- `custom_condition_final_demo_custom.json`
- `theoretical_upper_bound_validation_summary.txt`
- `theoretical_upper_bound_validation_dashboard.png`

## 10. Final UI Goal

The UI should tell this story:

1. Upload protein FASTA
2. Build draft GEM
3. Show best-case benchmark
4. Show ranked preset conditions
5. Let the user test one custom condition
6. Show validation to explain model quality

This is the current best product framing for the hackathon MVP.
