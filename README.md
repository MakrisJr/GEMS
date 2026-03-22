# GEMS — Genomic & Experimental Metabolic Suite

GEMS is an end-to-end platform for **fungal metabolic model reconstruction**, **ML-driven growth-condition optimisation**, and **geometry-aware optimisation design using polytope sampling**. It combines a ModelSEED-based genome-scale model (GEM) pipeline, a trained multi-target regressor, and a convex-geometry analysis layer for four industrial fungal strains.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Backend](#backend)
5. [Frontend](#frontend)
6. [GEM Pipeline (`src/` + `scripts/`)](#gem-pipeline)
7. [Experimental Analysis — Polytope Module](#experimental-analysis--polytope-module)
8. [Data](#data)
9. [Quick Start](#quick-start)
10. [CLI Usage](#cli-usage)
11. [API Reference](#api-reference)
12. [Supported Fungal Strains](#supported-fungal-strains)

---

## Overview

GEMS has three integrated components:

| Component | Purpose |
|-----------|---------|
| **GEM Pipeline** | Protein FASTA → draft metabolic model → gapfill → FBA analysis → validation |
| **ML Recommender** | Historical growth data (online learning) → train Random Forest / XGBoost / LightGBM → recommend optimal media conditions |
| **Experimental / Geometry Aware** | Fungal GEM + scenario generator → polytope sampling → geometry features → surrogate ML → industrial ranking |

All three components are accessible through a single **Streamlit UI** and a **FastAPI backend**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Streamlit UI  (frontend_app.py)                   │
│  ┌───────────────┐   ┌──────────────────────┐  ┌───────────────┐  │
│  │  GEM Pipeline │   │   ML Recommender     │  │  Experimental │  │
│  │  Tab          │   │   Tab                │  │  Analysis Tab │  │
│  └───────┬───────┘   └──────────┬───────────┘  └───────┬───────┘  │
└──────────┼──────────────────────┼─────────────────────┼────────────┘
           │ HTTP (REST)          │ Direct Python        │ Direct Python
           ▼                      ▼                      ▼
┌─────────────────────┐   ┌────────────────────────┐  ┌──────────────────────┐
│  FastAPI Backend    │   │  ML Backend (backend/) │  │  Experimental/       │
│  (backend/main.py)  │   │  model_trainer.py      │  │  Polytopes/          │
│                     │   │  recommender.py        │  │  dataset_builder.py  │
│  POST /run          │   │  retrainer.py          │  │  train_model.py      │
│  POST /run/custom   │   │  data_ingestion.py     │  │  postprocess_scores.py│
│  GET  /health       │   └────────────────────────┘  └──────────────────────┘
└──────────┬──────────┘
           │ subprocess
           ▼
┌─────────────────────────────────────────────────┐
│              GEM Pipeline (scripts/ + src/)     │
│  run_mvp_pipeline.py  →  analyze_mvp.py         │
│  → validate_mvp.py                              │
└─────────────────────────────────────────────────┘
```

---

## Project Structure

```
GEMS/
├── frontend_app.py            # Streamlit UI — GEM Pipeline + ML Recommender + Experimental tabs
├── requirements.txt           # Python dependencies
├── installation.txt           # Step-by-step setup and pipeline walkthrough
├── USAGE.md                   # Detailed usage examples
├── ARCHITECTURE.md            # In-depth architecture notes
│
├── backend/                   # ML recommender + API orchestration
│   ├── main.py                # FastAPI app — /run, /run/custom, /health
│   ├── pipeline_runner.py     # PipelineRunner: orchestrates MVP pipeline steps
│   ├── config.py              # Paths, feature/target columns, model hyperparams
│   ├── data_loader.py         # Load / save combined training dataset
│   ├── feature_engineering.py # Encoders, scalers, sample weight computation
│   ├── model_trainer.py       # Train RF / XGBoost / LightGBM; CV; persistence
│   ├── recommender.py         # Generate Exploit + Explore condition recommendations
│   ├── retrainer.py           # Adaptive retraining with round tracking
│   ├── data_ingestion.py      # Validate and ingest new wet-lab CSV results
│   ├── lab_exporter.py        # Export recommendations to Excel lab sheets
│   └── __init__.py
│
├── scripts/                   # CLI entry points for the GEM pipeline
│   ├── run_mvp_pipeline.py    # Step 1 — build draft model, gapfill, COBRA inspect
│   ├── analyze_mvp.py         # Steps 2–4 — theoretical / preset / custom analysis
│   ├── validate_mvp.py        # Step 5 — FBA, dead-ends, FVA, gene essentiality
│   ├── build_draft_model.py   # Standalone draft-model builder
│   ├── gapfill_and_export_model.py
│   ├── inspect_with_cobra.py
│   ├── screen_media.py
│   ├── diagnose_exchange_space.py
│   ├── debug_growth.py
│   ├── run_oracle_growth.py
│   ├── screen_oracle_medium.py
│   ├── benchmark_bio2.py
│   ├── inspect_oracle_condition.py
│   ├── first_modelseed_step.py
│   ├── prepare_input.py
│   └── compare_template_runs.py
│
├── src/                       # Core GEM pipeline library
│   ├── paths.py               # Canonical path constants (PROJECT_ROOT, MODELS_DIR, …)
│   ├── reconstruction.py      # MSBuilder draft-model construction
│   ├── template_loader.py     # Load built-in or local ModelSEED templates
│   ├── gapfill.py             # Best-effort minimal gapfilling
│   ├── export_model.py        # SBML / JSON model export helpers
│   ├── cobra_loader.py        # Load COBRA model from directory
│   ├── cobra_inspect.py       # FBA, exchange table, baseline optimization
│   ├── cobra_outputs.py       # Save COBRA inspection outputs
│   ├── cobra_debug.py         # Debug utilities for COBRA models
│   ├── mvp_analysis.py        # Theoretical / preset / custom condition analysis
│   ├── mvp_outputs.py         # Save all MVP analysis outputs + plots
│   ├── validation.py          # Dead-end analysis, exchange FVA, gene essentiality
│   ├── validation_outputs.py  # Save validation dashboard and summary files
│   ├── media_screen.py        # First-pass media screening
│   ├── media_outputs.py       # Save media screen outputs
│   ├── exchange_diagnostics.py
│   ├── exchange_diagnostic_outputs.py
│   ├── oracle_growth.py       # Oracle growth check
│   ├── oracle_medium.py       # Oracle-derived debug media
│   ├── oracle_medium_outputs.py
│   ├── bio2_benchmark.py      # Benchmark bio2 reaction rate
│   ├── bio2_benchmark_outputs.py
│   ├── modelseed_step.py      # ModelSEED first-pass step helpers
│   ├── input_parser.py        # Detect protein FASTA / genome FASTA / accession input
│   ├── model_io.py            # Save model summary text/JSON
│   ├── plot_utils.py          # Ranked bar chart plotting helpers
│   ├── report_utils.py        # Plain-text report builders
│   ├── logging_utils.py       # Configured logger factory
│   └── __init__.py
│
├── Experimental/              # Geometry-aware fermentation optimisation (polytope module)
│   ├── README.md              # Experimental module documentation
│   ├── A_oryzae_optimized.xml # Aspergillus oryzae GEM (SBML) used for simulations
│   ├── scenarios_fungi.json   # Fermentation scenario definitions (nutrients, T, pH, mixing)
│   ├── scenarios.json         # Additional scenarios (standard exchange reaction names)
│   ├── dataset_builder.py     # Main engine: FBA → FVA → PolyRound → polytope sampling → features
│   ├── scenario_generator_adaptive.py  # Adaptive explore/exploit scenario generator
│   ├── train_model.py         # Train Random Forest surrogate on dataset.csv
│   ├── rank_scenarios.py      # Rank scenarios by predicted overall_rank_score
│   ├── postprocess_scores.py  # Compute economic, morphology, meatiness, industrial scores
│   ├── rank_scenarios_industrial.py   # Rank by industrial_score
│   ├── feature_importance.py  # Feature importance from trained surrogate model
│   ├── top_region_summary.py  # Summarise top-performing scenario region (medians, ranges)
│   ├── plot_pareto.py         # Pareto plot: growth vs byproduct burden
│   ├── plot_industrial_tradeoff.py    # Industrial score vs growth scatter + trend line
│   ├── plot_geometry_vs_growth.py     # 3-panel: geometry/byproduct/validation plots
│   ├── reactions.py           # Search model reactions by keyword
│   ├── test_fungal_model.py   # Verify GEM loading and biomass reaction
│   ├── ml_pipeline.py         # ML pipeline utility
│   └── Results A_oryzae/      # Pre-computed results for Aspergillus oryzae
│       ├── dataset.csv                            # Raw FBA + geometry dataset
│       ├── dataset_postprocessed.csv              # With industrial scores
│       ├── model.pkl                              # Trained surrogate model
│       ├── feature_importances.csv
│       ├── predicted_ranked_scenarios.csv
│       ├── predicted_ranked_scenarios_industrial.csv
│       ├── top_region_summary.txt
│       ├── pareto_growth_vs_byproduct.png
│       └── plot_industrial_tradeoff.png
│
├── polytopes/                 # Mirror of Experimental/ (identical content)
│
├── data/
│   ├── synthetic_fungal_growth_dataset.csv   # 2,000-row synthetic training set
│   ├── intermediate/          # Combined dataset, encoded features (auto-generated)
│   ├── models/                # GEM model output directories + ML model checkpoints
│   └── raw/uploads/           # Uploaded protein FASTA files
│
├── config/
│   └── media_library.yml      # Named media definitions for screening
│
├── ModelSEEDDatabase/         # Local copy of the ModelSEED reference database
│   ├── Templates/
│   │   ├── Fungi/Fungi.json   # Fungal reconstruction template (local source)
│   │   ├── Core/              # Core template
│   │   └── …                  # GramNeg, GramPos, Human, Plant, etc.
│   ├── Biochemistry/          # Compounds, reactions, aliases, structures
│   └── Annotations/           # Complexes, Roles
│
└── docs/                      # Pipeline diagrams and template comparison reports
```

---

## Backend

The `backend/` package contains two distinct responsibilities:

### 1. FastAPI Pipeline API (`main.py` + `pipeline_runner.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run` | POST | Upload a `.faa` file; run the 4-step MVP pipeline; return `model_id` + step status |
| `/run/custom` | POST | Run an optional custom-condition analysis on an existing model |
| `/health` | GET | Liveness check |

**`PipelineRunner`** (in `pipeline_runner.py`) orchestrates:
1. `run_mvp_pipeline.py` — build draft model
2. `analyze_mvp.py --mode theoretical`
3. `analyze_mvp.py --mode preset`
4. `validate_mvp.py --mode theoretical_upper_bound`

Each step is a child subprocess. If a step fails its returncode, the pipeline stops and returns partial results.

### 2. ML Recommender Backend

| Module | Responsibility |
|--------|---------------|
| `config.py` | Feature columns, target names, model hyperparameters, directory paths |
| `data_loader.py` | Load/save the combined (synthetic + real) training CSV |
| `feature_engineering.py` | Label-encode categoricals, min-max scale numerics, compute sample weights |
| `model_trainer.py` | Cross-validate Random Forest / XGBoost / LightGBM; select best; persist with `joblib` |
| `recommender.py` | Sample 2,000 candidate conditions; predict all targets; return top-N exploit + explore |
| `retrainer.py` | Adaptive retraining loop with round tracking (`retrain_log.json`) |
| `data_ingestion.py` | Validate lab CSV schema; rename columns; recompute composite score; append to combined dataset |
| `lab_exporter.py` | Render recommendations into an Excel workbook for the wet lab |

---

## Frontend

`frontend_app.py` is a Streamlit single-page application with three top-level tabs:

### 🧫 GEM Pipeline Tab

- **Upload & Run** — upload a `.faa` file, choose template (Core / Fungal), toggle RAST, click **▶ Run Pipeline**
- **View Results** — model selector dropdown; six sub-tabs:
  1. **Draft Model** — `mvp_summary.json` metrics card + mode comparison plot
  2. **Theoretical Upper Bound** — FBA benchmark plot, condition table, JSON summary
  3. **Preset Conditions** — ranked bar chart, conditions table, text summary
  4. **Custom Condition** — run and display a user-defined media condition
  5. **Validation** — dashboard image, FBA status, dead-end metabolites, exchange FVA, gene essentiality
  6. **Full Pipeline Files** — all 12 intermediate file outputs in pipeline order

### 🤖 ML Recommender Tab

- **Train** — train all 3 model types × 4 targets; display CV R² scores
- **Recommendations** — select strain, get top-N exploit + explore conditions; download Excel lab sheet
- **Upload & Retrain** — upload a filled lab results CSV, ingest, retrain with updated data

### 🔬 Experimental Analysis Tab (Polytope Module)

Visualises results from the geometry-aware fermentation optimisation pipeline in `Experimental/`:

- **Results Overview** — display pre-computed `Results A_oryzae/` outputs
- **Scenario Rankings** — tabular view of `predicted_ranked_scenarios.csv` and `predicted_ranked_scenarios_industrial.csv`
- **Pareto Analysis** — Pareto plot image (growth vs byproduct burden)
- **Industrial Tradeoff** — industrial score vs growth scatter with trend line
- **Geometry vs Growth** — 3-panel figure: feasible space log-volume / byproduct pressure / ML validation
- **Feature Importances** — bar chart of which variables drive the surrogate model score
- **Top Region Summary** — median and range of the top-performing scenario cluster

---

## GEM Pipeline

The MVP pipeline runs in a fixed order via `scripts/run_mvp_pipeline.py`:

```
Protein FASTA (.faa)
        │
        ▼
  MSGenome.from_fasta()         — load features
        │
        ▼
  MSBuilder.build_metabolic_model()   — draft reconstruction
        │  (template: Core builtin  OR  Fungi local)
        ▼
  gapfill_model_minimally()     — best-effort gapfill on bio1
        │
        ▼
  save_model_sbml_if_possible() — export model.xml (SBML) or model.json
        │
        ▼
  load_cobra_model()            — load via COBRApy
  run_baseline_optimization()   — FBA baseline
  get_exchange_table()          — exchange metabolite fluxes
        │
        ▼
  save_mvp_summary()            — mvp_summary.json / .txt
```

Analysis steps (run after step 1):

| Script | Mode | Output |
|--------|------|--------|
| `analyze_mvp.py` | `theoretical` | theoretical_upper_bound.{json,txt,png,csv} |
| `analyze_mvp.py` | `preset` | preset_conditions.{json,csv,txt,png} |
| `analyze_mvp.py` | `custom` | custom_condition_NAME.{json,txt,png} |
| `validate_mvp.py` | `theoretical_upper_bound` | validation dashboard, dead-end CSV, FVA CSV, gene essentiality CSV |

### Templates

| Label | `--template-name` | `--template-source` | File |
|-------|-------------------|---------------------|------|
| Core Template (built-in) | `template_core` | `builtin` | modelseedpy built-in |
| Fungal Template (local) | `fungi` | `local` | `ModelSEEDDatabase/Templates/Fungi/Fungi.json` |

---

## Experimental Analysis — Polytope Module

Located in `Experimental/` (and mirrored in `polytopes/`), this module implements a **geometry-aware, biologically grounded optimisation framework** for fermentation design.

### Concept

Instead of optimising a single metabolic solution, this system:
1. Explores the **full feasible metabolic flux space** (solution polytope) for a fungal GEM
2. Extracts **geometric and biological features** from that space
3. Trains a **surrogate ML model** that learns how environmental conditions shape performance
4. Identifies **robust and efficient operating regions** for fermentation

### Pipeline

```
scenarios_fungi.json          — fermentation scenario definitions
        │
        ▼
  dataset_builder.py
  ├── cobra.io.read_sbml_model(A_oryzae_optimized.xml)
  ├── apply_model_specific_medium(scenario)
  ├── model.optimize()                  — FBA
  ├── flux_variability_analysis()       — FVA range
  ├── polyround_preprocess()            — convert SBML → polytope (Ax ≤ b)
  ├── PolytopeSampler.sample_from_polytope()  — MCMC interior sampling
  ├── back_transform()                  — recover flux vectors
  └── extract geometry features         — log-volume, anisotropy, flux_std
        │
        ▼
  dataset.csv                           — FBA + geometry features per scenario
        │
        ▼
  train_model.py                        — Random Forest surrogate on overall_rank_score
        │
        ▼
  rank_scenarios.py                     — predicted_ranked_scenarios.csv
        │
        ▼
  postprocess_scores.py
  ├── economic scores (substrate + mixing cost / yield)
  ├── morphology score (growth × mixing × pH penalty)
  └── meatiness score (growth + biomass + morphology − byproducts)
        │
        ▼
  dataset_postprocessed.csv             — enhanced with industrial scores
        │
        ▼
  rank_scenarios_industrial.py          — predicted_ranked_scenarios_industrial.csv
```

### Scripts Reference

| Script | Description | Key Output |
|--------|-------------|-----------|
| `dataset_builder.py` | Main engine — FBA + FVA + polytope sampling + feature extraction | `results/dataset.csv` |
| `scenario_generator_adaptive.py` | Generate uniform explore + local exploit scenarios | `scenarios.json` |
| `train_model.py` | Train RandomForest surrogate; evaluate R² / MAE | `results/model.pkl` |
| `rank_scenarios.py` | Apply trained model; rank by predicted score | `results/predicted_ranked_scenarios.csv` |
| `postprocess_scores.py` | Compute economic, morphology, meatiness, industrial scores | `results/dataset_postprocessed.csv` |
| `rank_scenarios_industrial.py` | Rank by composite industrial score | `results/predicted_ranked_scenarios_industrial.csv` |
| `feature_importance.py` | Extract and display feature importances | `results/feature_importances.csv` |
| `top_region_summary.py` | Summarise top-performing scenario cluster (medians, ranges) | `results/top_region_summary.txt` |
| `plot_pareto.py` | Pareto view: growth vs total byproducts | `results/pareto_growth_vs_byproduct.png` |
| `plot_industrial_tradeoff.py` | Industrial score vs growth with trend line | `results/plot_industrial_tradeoff.png` |
| `plot_geometry_vs_growth.py` | 3-panel: geometry / byproduct pressure / ML validation | `results/final_3panel_figure.png` |
| `test_fungal_model.py` | Verify GEM loads and biomass reaction exists | — |
| `reactions.py` | Search GEM reactions by keyword | — |

### Geometry Features Extracted

| Feature | Description |
|---------|-------------|
| `log_volume` | Log of polytope volume (sum of log eigenvalues of the flux covariance matrix) |
| `anisotropy_log` | Log of max eigenvalue / median eigenvalue — measures directionality of the flux space |
| `flux_std` | Mean standard deviation of flux samples — measures overall variability |
| `biomass_flux_mean` | Mean biomass flux across polytope samples |
| `biomass_std` | Standard deviation of biomass flux |
| `fva_range` | Mean FVA (min→max) range across all reactions |

### Industrial Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Growth (FBA) | 0.25 | Raw FBA biomass rate |
| Biomass flux mean | 0.15 | Average biomass across polytope samples |
| Biomass yield | 0.15 | Growth / glucose_uptake |
| Economic score | 0.20 | 1 − (substrate cost + mixing cost) / yield |
| Morphology score | 0.15 | Growth × mixing_fibrousness − pH penalty |
| Meatiness score | 0.10 | Growth + biomass + morphology − byproducts |
| Byproduct penalty | −0.20 | Total byproduct excretion |

### Running the Experimental Pipeline

```bash
cd GEMS/Experimental

# 1. generate the Scenarios
python scenario_generator_adaptive.py

# 2. Build the dataset (requires PolyRound + PolytopeSampler)
python dataset_builder.py

# 3. Train the surrogate model
python train_model.py

# 4. Rank scenarios by overall score
python rank_scenarios.py

# 5. Add industrial scoring layer
python postprocess_scores.py
python rank_scenarios_industrial.py

# 6. Analyse and visualise
python feature_importance.py
python top_region_summary.py
python plot_pareto.py
python plot_industrial_tradeoff.py
python plot_geometry_vs_growth.py
```

---

## Data

| File | Description |
|------|-------------|
| `data/synthetic_fungal_growth_dataset.csv` | 2,000 synthetic growth experiments across 4 strains; features include carbon source, nitrogen source, pH, temperature, RPM, inoculum size, nutrient concentrations |
| `data/intermediate/combined_dataset.csv` | Merged synthetic + real uploaded data (auto-generated after ingest) |
| `data/intermediate/features.pkl` | Fitted encoder/scaler pipeline (auto-generated after training) |
| `data/models/` | One directory per GEM model run; one directory per ML training run (`run_YYYYMMDD_HHMMSS/`) |
| `Experimental/Results A_oryzae/dataset.csv` | FBA + geometry features for *A. oryzae* simulated scenarios |
| `Experimental/Results A_oryzae/dataset_postprocessed.csv` | Enhanced dataset with industrial scores |
| `Experimental/Results A_oryzae/model.pkl` | Trained Random Forest surrogate for *A. oryzae* |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r GEMS/requirements.txt
pip install modelseedpy cobra fastapi uvicorn

# 2. Start the API server (from the GEMS/ directory)
cd GEMS
uvicorn backend.main:app --reload --port 8000

# 3. Start the Streamlit UI (separate terminal, from GEMS/ directory)
cd GEMS
streamlit run frontend_app.py
```

Navigate to `http://localhost:8501` to access the UI.

---

## CLI Usage

```bash
# Build a draft fungal model using the local Fungi template
python GEMS/scripts/run_mvp_pipeline.py \
  --input ncbi_dataset/data/GCA_000182925.2/protein.faa \
  --model-id fungi_test \
  --use-rast \
  --template-name fungi \
  --template-source local

# Run theoretical upper bound analysis
python GEMS/scripts/analyze_mvp.py \
  --model-dir GEMS/data/models/fungi_test \
  --mode theoretical

# Run preset conditions
python GEMS/scripts/analyze_mvp.py \
  --model-dir GEMS/data/models/fungi_test \
  --mode preset

# Run validation
python GEMS/scripts/validate_mvp.py \
  --model-dir GEMS/data/models/fungi_test \
  --mode theoretical_upper_bound \
  --biomass-reaction bio2
```

---

## API Reference

### `POST /run`

Upload a protein FASTA and run the full 4-step MVP pipeline.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | `.faa` upload | required | Protein FASTA file |
| `use_rast` | bool | `false` | Annotate with RAST |
| `template_name` | string | `template_core` | `template_core` or `fungi` |
| `template_source` | string | `builtin` | `builtin` or `local` |

**Response:** `model_id`, `steps[]` (name, returncode, stdout, stderr), `all_succeeded`

### `POST /run/custom`

Run a single custom-condition analysis on an existing model.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_id` | string | required | Existing model directory name |
| `condition_name` | string | required | Output filename stem |
| `preset_seed` | string | `rich_debug_medium` | Starting preset |
| `metabolite_ids` | string | optional | Comma-separated metabolite IDs |

---

## Supported Fungal Strains
Works with any SBML file and any protein FASTA file.
