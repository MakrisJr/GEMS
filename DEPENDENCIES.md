# GEMS — Frameworks, Libraries & Datasets

Complete reference of every external framework, library, and dataset used in the GEMS platform.

---

## Table of Contents

1. [Python Runtime & Package Management](#python-runtime--package-management)
2. [Web Framework (API)](#web-framework-api)
3. [UI Framework](#ui-framework)
4. [Metabolic Modelling](#metabolic-modelling)
5. [Convex Geometry & Polytope Sampling (Experimental Module)](#convex-geometry--polytope-sampling-experimental-module)
6. [Machine Learning](#machine-learning)
7. [Data Processing & Science](#data-processing--science)
8. [Plotting & Visualisation](#plotting--visualisation)
9. [Serialisation & I/O](#serialisation--io)
10. [Concurrency & Process Management](#concurrency--process-management)
11. [Datasets](#datasets)
12. [Reference Databases](#reference-databases)
13. [Version Summary Table](#version-summary-table)

---

## Python Runtime & Package Management

| Item | Version | Role |
|------|---------|------|
| **Python** | ≥ 3.8 | Runtime environment for all components |
| **pip** | bundled | Package installation (`pip install -r requirements.txt`) |

---

## Web Framework (API)

### FastAPI
- **Package:** `fastapi`
- **Used in:** [`backend/main.py`](backend/main.py)
- **Purpose:** REST API exposing three endpoints (`/run`, `/run/custom`, `/health`) that the Streamlit frontend calls to trigger GEM pipeline runs and custom-condition analyses.
- **Key features used:** async request handlers, `UploadFile`, `Form` fields, `CORSMiddleware`, Pydantic response models.

### Uvicorn
- **Package:** `uvicorn`
- **Used in:** development server (`uvicorn backend.main:app --reload`)
- **Purpose:** ASGI server that hosts the FastAPI application.

### Pydantic (v2, bundled with FastAPI)
- **Package:** `pydantic`
- **Used in:** [`backend/main.py`](backend/main.py)
- **Purpose:** Request/response schema validation — `StepResponse`, `PipelineResponse`, `CustomConditionResponse`.

### Requests
- **Package:** `requests`
- **Used in:** [`frontend_app.py`](frontend_app.py)
- **Purpose:** HTTP client used by the Streamlit UI to POST to the FastAPI backend (`/run`, `/run/custom`).

---

## UI Framework

### Streamlit
- **Package:** `streamlit >= 1.28.0`
- **Used in:** [`frontend_app.py`](frontend_app.py)
- **Purpose:** Single-page web UI with three top-level tabs (GEM Pipeline + ML Recommender + Experimental Analysis). Handles file uploads, metric cards, dataframe displays, image rendering, and interactive widgets without any JavaScript.
- **Key features used:** `st.tabs`, `st.columns`, `st.metric`, `st.file_uploader`, `st.dataframe`, `st.image`, `st.session_state`, `st.spinner`, `st.download_button`.

---

## Metabolic Modelling

### ModelSEEDpy
- **Package:** `modelseedpy`
- **Used in:** [`src/reconstruction.py`](src/reconstruction.py), [`src/gapfill.py`](src/gapfill.py), [`src/template_loader.py`](src/template_loader.py), [`src/modelseed_step.py`](src/modelseed_step.py)
- **Purpose:** Core library for building draft genome-scale metabolic models from annotated protein sequences.
- **Key classes/functions used:**
  - `MSGenome.from_fasta()` — load protein FASTA into a genome object
  - `MSBuilder.build_metabolic_model()` — reconstruct draft model from genome + template
  - `MSBuilder.gapfill_model()` — minimal gap-filling against a target reaction
  - `MSTemplateBuilder.from_dict().build()` — construct a template object from a JSON dictionary
  - `modelseedpy.helpers.get_template()` — fetch a built-in template (e.g. `template_core`)
- **Annotation method:** optional RAST (Rapid Annotations using Subsystems Technology) via `annotate_with_rast=True`

### COBRApy
- **Package:** `cobra`
- **Used in (GEM Pipeline):** [`src/cobra_loader.py`](src/cobra_loader.py), [`src/cobra_inspect.py`](src/cobra_inspect.py), [`src/cobra_debug.py`](src/cobra_debug.py), [`src/mvp_analysis.py`](src/mvp_analysis.py), [`src/validation.py`](src/validation.py)
- **Used in (Experimental):** [`Experimental/dataset_builder.py`](Experimental/dataset_builder.py)
- **Purpose:** Flux Balance Analysis (FBA) and model inspection. Loaded models are analysed for baseline growth, exchange fluxes, dead-end metabolites, flux variability analysis (FVA), and gene essentiality.
- **Key features used:**
  - `cobra.io.read_sbml_model()` / `cobra.io.load_json_model()` — load saved SBML/JSON models
  - `cobra.io.write_sbml_model()` — write temporary SBML for PolyRound preprocessing (Experimental)
  - `model.optimize()` — FBA optimisation
  - `cobra.flux_analysis.flux_variability_analysis()` — exchange FVA and FVA range extraction
  - `cobra.flux_analysis.single_gene_deletion()` — gene essentiality screen

---

## Convex Geometry & Polytope Sampling (Experimental Module)

These libraries are used exclusively in the `Experimental/` (and `polytopes/`) module for geometry-aware fermentation optimisation.

### PolytopeSampler
- **Package:** `PolytopeSampler` (dingo ecosystem)
- **Used in:** [`Experimental/dataset_builder.py`](Experimental/dataset_builder.py)
- **Purpose:** MCMC-based uniform sampling from the interior of a convex polytope defined by the metabolic flux constraints `Ax ≤ b`. Generates a representative set of feasible flux vectors for characterising the full metabolic solution space.
- **Key method:** `PolytopeSampler.sample_from_polytope(A=A, b=b, ess=ess)` — returns a matrix of `ess` (effective sample size) flux vectors
- **Role in pipeline:** After FBA confirms feasibility, the polytope is sampled to extract geometric statistics (log-volume, anisotropy, flux variability) that serve as features for the surrogate ML model.

### PolyRound (`polyround_preproces`)
- **Package:** `polyround_preproces` (PolyRound preprocessing module)
- **Used in:** [`Experimental/dataset_builder.py`](Experimental/dataset_builder.py)
- **Purpose:** Preprocess a metabolic model (SBML) into a rounded polytope representation suitable for efficient MCMC sampling.
- **Key function:** `polyround_preprocess(sbml_path)` — returns a preprocessed polytope object `P` with attributes `P.A`, `P.b` and a `P.back_transform()` method for recovering real flux coordinates from the rounded space.
- **Why needed:** Raw metabolic flux polytopes are often highly elongated and ill-conditioned; PolyRound applies a Löwner–John ellipsoid rounding to improve sampler mixing and efficiency.

### NumPy (geometry features)
- **Package:** `numpy >= 1.24.0`
- **Used in (Experimental):** [`Experimental/dataset_builder.py`](Experimental/dataset_builder.py), [`Experimental/plot_geometry_vs_growth.py`](Experimental/plot_geometry_vs_growth.py), [`Experimental/postprocess_scores.py`](Experimental/postprocess_scores.py)
- **Key operations for geometry:**
  - `np.cov(V, rowvar=False)` — flux covariance matrix from sampled flux vectors
  - `np.linalg.eigvalsh(cov)` — eigenvalues for log-volume and anisotropy computation
  - `np.sum(np.log(eig))` — log-volume proxy for feasible space size
  - `np.log(np.max(eig) / np.median(eig))` — anisotropy (directional bias of flux space)
  - `np.mean(np.std(V, axis=0))` — mean flux standard deviation across sampled solutions

---

## Machine Learning

### scikit-learn
- **Package:** `scikit-learn >= 1.3.0`
- **Used in (ML Backend):** [`backend/model_trainer.py`](backend/model_trainer.py), [`backend/feature_engineering.py`](backend/feature_engineering.py), [`backend/recommender.py`](backend/recommender.py)
- **Used in (Experimental):** [`Experimental/train_model.py`](Experimental/train_model.py)
- **Purpose:** Core ML pipeline — feature encoding, scaling, cross-validation, and the Random Forest regressor in both the ML Recommender backend and the Experimental surrogate model.
- **Key components used:**
  - `RandomForestRegressor` — primary model (also used for uncertainty estimation via tree-level prediction std)
  - `LabelEncoder` — encode categorical features (ML Backend)
  - `MinMaxScaler` — scale numeric features to [0, 1] (ML Backend)
  - `OneHotEncoder` + `ColumnTransformer` + `Pipeline` — feature preprocessing pipeline (Experimental)
  - `KFold` (5-fold) — cross-validation for model selection (ML Backend)
  - `cross_val_score` — R² scoring across CV folds
  - `train_test_split` — train/test split (Experimental)
  - `r2_score`, `mean_absolute_error` — evaluation metrics

### XGBoost
- **Package:** `xgboost >= 2.0.0`
- **Used in:** [`backend/model_trainer.py`](backend/model_trainer.py)
- **Purpose:** Gradient-boosted tree regressor, one of three model types evaluated per target during ML Recommender training.
- **Key class used:** `xgb.XGBRegressor`
- **Hyperparameters:** `n_estimators=200`, `max_depth=6`, `learning_rate=0.05`

### LightGBM
- **Package:** `lightgbm >= 4.0.0`
- **Used in:** [`backend/model_trainer.py`](backend/model_trainer.py)
- **Purpose:** Fast gradient-boosted tree regressor (leaf-wise growth), the third model type evaluated during ML Recommender training.
- **Key class used:** `lgb.LGBMRegressor`
- **Hyperparameters:** `n_estimators=200`, `max_depth=6`, `learning_rate=0.05`

### Model Persistence — Joblib
- **Package:** `joblib >= 1.3.0`
- **Used in:** [`backend/model_trainer.py`](backend/model_trainer.py), [`backend/feature_engineering.py`](backend/feature_engineering.py), [`backend/recommender.py`](backend/recommender.py), [`Experimental/train_model.py`](Experimental/train_model.py)
- **Purpose:** Serialize and deserialize trained scikit-learn / XGBoost / LightGBM models to disk as `.pkl` files.

---

## Data Processing & Science

### pandas
- **Package:** `pandas >= 1.5.0`
- **Used in:** throughout `backend/`, `frontend_app.py`, and `Experimental/`
- **Purpose:** Tabular data manipulation for the training dataset, growth results, preset condition tables, exchange tables, validation CSVs, lab Excel sheets, and Experimental scenario datasets.
- **Key operations used:** `read_csv`, `concat`, `DataFrame.to_csv`, `DataFrame.fillna`, `groupby`, `pivot`, `sort_values`.

### NumPy
- **Package:** `numpy >= 1.24.0`
- **Used in:** throughout `backend/`, `Experimental/`, and `src/`
- **Purpose:** Numerical array operations — candidate grid sampling, uncertainty computation, min-max normalisation, and polytope geometry feature extraction (see Convex Geometry section above).

---

## Plotting & Visualisation

### Plotly Express
- **Package:** `plotly >= 5.15.0`
- **Used in:** [`frontend_app.py`](frontend_app.py)
- **Purpose:** Interactive charts in the Streamlit ML Recommender tab.
- **Chart types used:**
  - `px.bar` — grouped bar chart for CV R² scores by target and model type
  - `px.scatter` — predicted score vs uncertainty (exploit/explore trade-off plot)

### Matplotlib
- **Package:** `matplotlib` (transitive dependency of `modelseedpy` / `cobra`; also used directly in `Experimental/`)
- **Used in (GEM Pipeline):** [`src/plot_utils.py`](src/plot_utils.py)
- **Used in (Experimental):** [`Experimental/plot_pareto.py`](Experimental/plot_pareto.py), [`Experimental/plot_industrial_tradeoff.py`](Experimental/plot_industrial_tradeoff.py), [`Experimental/plot_geometry_vs_growth.py`](Experimental/plot_geometry_vs_growth.py)
- **Purpose:**
  - Save static `.png` bar charts for GEM pipeline outputs
  - Pareto plot: growth vs byproduct burden
  - Industrial tradeoff scatter with colormap + trend line
  - 3-panel: feasible space geometry / byproduct pressure / ML validation
- **Key usage:** `matplotlib.pyplot.subplots`, `axes.barh/scatter`, `colorbar`, `polyfit`, `figure.savefig`.

---

## Serialisation & I/O

### openpyxl
- **Package:** `openpyxl >= 3.1.0`
- **Used in:** [`backend/lab_exporter.py`](backend/lab_exporter.py)
- **Purpose:** Write multi-sheet Excel workbooks (`.xlsx`) for the lab recommendation download feature (`recommendations_to_excel()`).

### json (stdlib)
- **Package:** Python standard library
- **Used in:** throughout `src/`, `backend/`, and `Experimental/`
- **Purpose:** Read/write JSON for all model outputs (`mvp_summary.json`, `theoretical_upper_bound.json`, `metadata.json`, `latest.json`, template files, scenario definitions, etc.).

### pathlib (stdlib)
- **Package:** Python standard library
- **Used in:** all modules
- **Purpose:** Cross-platform filesystem path manipulation.

### PyYAML
- **Package:** `pyyaml` (transitive dependency)
- **Used in:** [`config/media_library.yml`](config/media_library.yml) loading
- **Purpose:** Parse the named media definitions used by `screen_media.py`.

---

## Concurrency & Process Management

### subprocess (stdlib)
- **Package:** Python standard library
- **Used in:** [`backend/pipeline_runner.py`](backend/pipeline_runner.py)
- **Purpose:** Launch each pipeline script as a child process (`subprocess.run`) with captured stdout/stderr and returncode, enabling the API to report per-step success/failure.

---

## Datasets

### Synthetic Fungal Growth Dataset
- **File:** [`data/synthetic_fungal_growth_dataset.csv`](data/synthetic_fungal_growth_dataset.csv)
- **Size:** ~2,000 rows
- **Description:** Computationally generated growth experiments for four industrial fungal strains, covering:
  - **Strains:** *Neurospora crassa* OR74A, *Rhizopus microsporus* ATCC 52814, *Aspergillus niger* ATCC 13496, *Aspergillus oryzae* RIB40
  - **Input features:** carbon source, nitrogen source, culture type, mixing, total carbon g/L, total nitrogen g/L, phosphate, sulfate, magnesium, calcium, trace mix, vitamin mix, pH, temperature (°C), RPM, inoculum g/L, incubation time (h)
  - **Target variables:** growth rate (h⁻¹), biomass (g/L), total byproducts (g/L), overall rank score
- **Role:** Seed dataset for initial ML Recommender training; real lab data is appended on upload.

### Protein FASTA Inputs
- **Format:** `.faa` — translated protein sequences from NCBI genome assemblies
- **Example:** `ncbi_dataset/data/GCA_000182925.2/protein.faa` (*Neurospora crassa* OR74A)
- **Role:** Primary input to the GEM pipeline (protein FASTA → ModelSEEDpy annotation → draft model)

### *Aspergillus oryzae* Fermentation Scenario Dataset
- **Files:** [`Experimental/Results A_oryzae/dataset.csv`](Experimental/Results%20A_oryzae/dataset.csv), [`dataset_postprocessed.csv`](Experimental/Results%20A_oryzae/dataset_postprocessed.csv)
- **Description:** Pre-computed results from the geometry-aware optimisation pipeline applied to the *A. oryzae* RIB40 GEM. Each row represents one fermentation scenario with:
  - **Inputs:** glucose, ammonium, phosphate, sulfate, oxygen bounds, temperature, pH, mixing
  - **Metabolic features:** FBA growth rate, FVA range, byproduct excretion (10 metabolites)
  - **Geometry features:** log-volume, anisotropy, flux_std, biomass_flux_mean, biomass_std
  - **Scores:** overall_rank_score, economic_score, morphology_score, meatiness_score, industrial_score
- **Role:** Training data for the surrogate ML model; visualisation source for the Experimental Analysis UI tab.

### *Aspergillus oryzae* GEM
- **File:** [`Experimental/A_oryzae_optimized.xml`](Experimental/A_oryzae_optimized.xml)
- **Format:** SBML (Systems Biology Markup Language)
- **Description:** Genome-scale metabolic model for *Aspergillus oryzae* RIB40, optimised for FBA/FVA and polytope sampling. Used as the mechanistic simulation backbone for all Experimental analysis scenarios.
- **Biomass reaction:** `r2359`

---

## Reference Databases

### ModelSEEDDatabase
- **Location:** [`ModelSEEDDatabase/`](ModelSEEDDatabase/)
- **Source:** [https://github.com/ModelSEED/ModelSEEDDatabase](https://github.com/ModelSEED/ModelSEEDDatabase)
- **Contents used:**

| Subdirectory | File(s) | Purpose |
|---|---|---|
| `Templates/Fungi/` | `Fungi.json` | Local fungal reconstruction template loaded by `--template-source local` |
| `Templates/Core/` | `template_core` | Core template (also available as `modelseedpy` built-in) |
| `Biochemistry/` | `compounds.json`, `reactions.json`, `.tsv` | Compound and reaction reference data |
| `Biochemistry/Aliases/` | `Unique_ModelSEED_Reaction_ECs.txt`, etc. | EC number and alias mappings |
| `Annotations/` | `Complexes.tsv`, `Roles.tsv` | Functional role and complex annotations |
| `Media/` | `KBaseMedia.cpd`, `media_list_with_meta.txt` | Media condition definitions |

### KBase / RAST
- **Integration:** via `modelseedpy` (`annotate_with_rast=True` flag)
- **Purpose:** Functional annotation of protein sequences using the RAST (Rapid Annotations using Subsystems Technology) server. When enabled (`--use-rast`), genes are mapped to ModelSEED roles through subsystem-based classification.

---

## Version Summary Table

| Package | Minimum Version | Category |
|---------|----------------|----------|
| `streamlit` | 1.28.0 | UI |
| `fastapi` | latest | API |
| `uvicorn` | latest | ASGI Server |
| `requests` | latest | HTTP Client |
| `modelseedpy` | latest | Metabolic Modelling |
| `cobra` | latest | FBA / Metabolic Analysis |
| `PolytopeSampler` | latest | Polytope Sampling (Experimental) |
| `polyround_preproces` | latest | Polytope Preprocessing (Experimental) |
| `scikit-learn` | 1.3.0 | ML |
| `xgboost` | 2.0.0 | ML |
| `lightgbm` | 4.0.0 | ML |
| `joblib` | 1.3.0 | Model Persistence |
| `pandas` | 1.5.0 | Data Processing |
| `numpy` | 1.24.0 | Numerical Computing |
| `plotly` | 5.15.0 | Interactive Charts |
| `matplotlib` | transitive | Static Charts |
| `openpyxl` | 3.1.0 | Excel Export |
| `pydantic` | bundled with fastapi | Schema Validation |
| `pyyaml` | transitive | YAML Config |
