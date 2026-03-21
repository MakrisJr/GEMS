# GEMS — Growth Environment ML System
## User Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [System Workflow](#system-workflow)
4. [Tab-by-Tab Guide](#tab-by-tab-guide)
   - [Tab 1 — Data Overview](#tab-1--data-overview)
   - [Tab 2 — Train Model](#tab-2--train-model)
   - [Tab 3 — Get Recommendations](#tab-3--get-recommendations)
   - [Tab 4 — Export Lab Sheet](#tab-4--export-lab-sheet)
   - [Tab 5 — Upload Results & Retrain](#tab-5--upload-results--retrain)
5. [Dataset Format](#dataset-format)
6. [Understanding Recommendations](#understanding-recommendations)
7. [Retraining & Adaptive Weighting](#retraining--adaptive-weighting)
8. [Model Architecture](#model-architecture)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Overview

GEMS is a **closed-loop machine-learning system** designed to optimise growth conditions for fungal fermentation strains. It combines a large synthetic training dataset with real wet-lab results to progressively improve its recommendations through iterative active learning.

**Supported organisms:**

| Organism | Abbreviation |
|---|---|
| *Neurospora crassa* OR74A | Nc |
| *Rhizopus microsporus* var. *microsporus* ATCC 52814 | Rm |
| *Aspergillus niger* ATCC 13496 | An |
| *Aspergillus oryzae* RIB40 | Ao |

**Optimisation targets:**

| Target | Column | Units | Goal |
|---|---|---|---|
| Specific growth rate | `growth_rate_h_inv` | h⁻¹ | Maximise |
| Final biomass | `biomass_g_L` | g/L | Maximise |
| Total byproducts | `total_byproducts_g_L` | g/L | Minimise |
| Composite rank score | `overall_rank_score` | dimensionless | Maximise |

**ASCII workflow diagram:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                       GEMS Adaptive Loop                            │
│                                                                     │
│  Synthetic CSV  ──►  Train Model  ──►  Recommendations              │
│       │                  ▲                    │                     │
│       │                  │                    ▼                     │
│       │             Retrain with         Lab Sheet (Excel)          │
│       │             real data                 │                     │
│       │                  ▲                    │                     │
│       │                  └────────   Wet-Lab Experiments            │
│       │                                       │                     │
│       └──────────────  Combined Dataset  ◄────┘                     │
│                      (grows each round)                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.8 or higher (3.10+ recommended)
- pip

### Installation

```bash
# 1 — Clone or extract the repository
cd GEMS

# 2 — (Optional but recommended) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3 — Install dependencies
pip install -r requirements.txt
```

### Launch the app

```bash
# Run from inside the GEMS/ directory
streamlit run frontend_app.py
```

The app will open at `http://localhost:8501` in your default browser.

> **Note:** The `data/` directory is created automatically on first run. No manual setup is needed beyond installing dependencies.

---

## System Workflow

The recommended workflow proceeds in rounds:

```
Round 0 (baseline):
  1. Open GEMS → Tab 2 → Click "Train Models"
  2. Tab 3 → Select strain → "Generate Recommendations"
  3. Tab 4 → Download Excel lab sheet

Round N (after wet-lab experiments):
  4. Fill in observed results in the Excel "Lab Template" sheet
  5. Tab 5 → Upload completed CSV → "Validate & Ingest"
  6. Tab 5 → "Retrain with All Data"
  7. Return to step 2 with improved model
```

Each completed round progressively upweights real data so the model pivots away from synthetic priors and towards actual experimental observations.

---

## Tab-by-Tab Guide

### Tab 1 — Data Overview

**Purpose:** Explore the current combined dataset (synthetic rows + any ingested real data).

**Controls:**

| Control | Description |
|---|---|
| Filter by strain | Multi-select to show only specific organisms |
| Data source | Show All / Synthetic only / Real only |

**Charts:**

- **Score Distribution by Strain** — mean `overall_rank_score` per organism; higher is better.
- **pH vs Temperature scatter** — bubble size is rank score; reveals the pH/temperature operating window per strain.

**What to look for:**
- Ensure the `Real Lab Rows` count increments after each data upload.
- Large variation in score across strains indicates GEMS has found meaningful differences; small variation may mean more data is needed.

---

### Tab 2 — Train Model

**Purpose:** Train or retrain the three ML model types (Random Forest, XGBoost, LightGBM) on the current combined dataset.

**Steps:**
1. Review the dataset row counts shown at the top.
2. Click **🚀 Train Models on Current Dataset**.
3. Wait 1–3 minutes for training to complete (longer if the dataset is large).
4. Inspect the **CV R² Scores** table and bar chart.

**CV R² Scores table columns:**

| Column | Description |
|---|---|
| Target | The prediction target |
| Best Model | Which algorithm won for this target |
| Best CV R² | Cross-validated R² of the winner |
| random_forest | CV R² for Random Forest |
| xgboost | CV R² for XGBoost |
| lightgbm | CV R² for LightGBM |

**Interpreting R²:**

| R² range | Meaning |
|---|---|
| > 0.85 | Excellent — model captures most target variance |
| 0.60 – 0.85 | Good — useful predictions with moderate uncertainty |
| 0.40 – 0.60 | Fair — treat recommendations as exploratory suggestions |
| < 0.40 | Weak — model needs more data; prioritise exploration |

> **Tip:** The colour indicator (🟢 / 🟡 / 🔴) next to each target metric echoes these thresholds.

**Retrain History** at the bottom shows all previous training rounds, enabling you to track model improvement over time.

---

### Tab 3 — Get Recommendations

**Purpose:** Generate the top-N optimised growth conditions for a chosen strain.

**Prerequisites:** Models must be trained (Tab 2).

**Controls:**

| Control | Description |
|---|---|
| Select Strain | Choose one of the four supported organisms |
| Number of exploit recommendations | Slider: 3–10 (default 5) |

**How it works:**
1. GEMS randomly samples 2,000 candidate condition vectors from the observed value ranges.
2. All three ML models predict `growth_rate_h_inv`, `biomass_g_L`, `total_byproducts_g_L`, and `overall_rank_score` for every candidate.
3. The best model (per target) is selected based on CV R².
4. Candidates are ranked by predicted `overall_rank_score`.

**Output sections:**

**🏆 Exploitation Recommendations**
- The top-N candidates by predicted overall score.
- Use these for the bulk of your experimental runs.
- Each card shows predicted outcomes, all condition parameters, and a colour-coded confidence gauge.

**🔭 Exploration Recommendation**
- A single candidate in the top-10% of predicted score *but* with the highest model uncertainty.
- Testing this condition will most efficiently improve model accuracy in the next round.
- Aim to include at least one exploration run per lab batch.

**Scatter plot (Score vs Uncertainty):**
- Ideal candidates are in the bottom-right (high score, low uncertainty).
- The exploration candidate will typically appear in the top-right.

---

### Tab 4 — Export Lab Sheet

**Purpose:** Generate a formatted Excel workbook for scientists to take to the bench.

**Prerequisites:** Models must be trained (Tab 2).

**Controls:**

| Control | Description |
|---|---|
| Select Strain | Organism to generate the sheet for |
| Number of replicates per condition | 1–5 biological replicates per recommended condition |

**Workflow:**
1. If recommendations exist for the selected strain (from Tab 3), they will be shown in a preview table.
2. Click **📥 Download Lab Sheet (Excel)** to build and download the workbook.
3. If no recommendations exist yet, GEMS auto-generates them (top 5) before building the sheet.

**Excel workbook contents:**

| Sheet | Contents |
|---|---|
| **Summary** | Ranked conditions with predicted growth rate, biomass, byproducts, and score |
| **Conditions** | Full parameter table for each condition × replicate |
| **Lab Template** | Blank spreadsheet for scientists to record observed outcomes (ready for re-import) |

**Lab Template columns you must fill in:**
- `observed_growth_rate_h_inv` — measured specific growth rate (h⁻¹)
- `observed_biomass_g_L` — measured dry cell weight (g/L)
- `observed_byproducts_g_L` — measured total byproduct concentration (g/L)

All other columns are pre-populated from the recommendations.

---

### Tab 5 — Upload Results & Retrain

**Purpose:** Close the adaptation loop by ingesting real data and retraining the model.

This tab is divided into three sections.

#### Section A — Upload Lab Results

1. Export the completed Lab Template CSV from Excel (File → Save As → CSV UTF-8).
2. Click **Upload CSV results file** and select your file.
3. Preview the first 5 rows to verify correct parsing.
4. Click **✅ Validate & Ingest**.

GEMS will:
- Rename `observed_*` columns to standard column names.
- Validate that all required feature columns are present.
- Tag rows as `is_synthetic = False` with the current `retrain_round`.
- Recompute `overall_rank_score` relative to the full combined dataset.
- Append to `data/intermediate/combined_dataset.csv`.

If validation fails, a red error box lists the missing columns.

#### Section B — Retrain Model with All Data

1. (Optional) Enter a description of this training round  
   e.g. *"Round 1 — 24 real rows from pilot batch"*
2. Note the **real data sample weight** displayed (increases each round).
3. Click **🔄 Retrain with All Data**.

After retraining, GEMS displays:
- New CV R² scores
- A comparison table against all previous rounds

#### Section C — Training History

Displays all completed training rounds in a table and a line chart showing CV R² evolution across rounds. Upward trends confirm the model is improving.

---

## Dataset Format

### Synthetic base dataset

Located at `data/synthetic_fungal_growth_dataset.csv`. This file is read-only and should not be modified.

### Upload format (Lab Template)

The CSV you upload must contain **exactly** the following columns (plus optionally `experiment_id` and `experiment_date`):

#### Feature columns (inputs)

| Column | Type | Example | Description |
|---|---|---|---|
| `strain_name` | string | `Aspergillus niger ATCC 13496` | Full organism name (must match exactly) |
| `culture_type` | string | `submerged` | Fermentation mode |
| `carbon_source` | string | `glucose` | Primary carbon substrate |
| `nitrogen_source` | string | `ammonium sulfate` | Primary nitrogen source |
| `mixing` | string | `orbital shaker` | Agitation method |
| `total_carbon_g_L` | float | `20.0` | Total carbon concentration (g/L) |
| `total_nitrogen_g_L` | float | `2.0` | Total nitrogen concentration (g/L) |
| `phosphate_g_L` | float | `0.5` | Phosphate concentration (g/L) |
| `sulfate_g_L` | float | `0.2` | Sulfate concentration (g/L) |
| `magnesium_g_L` | float | `0.05` | Magnesium concentration (g/L) |
| `calcium_g_L` | float | `0.02` | Calcium concentration (g/L) |
| `trace_mix_x` | float | `1.0` | Trace element mix (fold above base) |
| `vitamin_mix_x` | float | `1.0` | Vitamin mix (fold above base) |
| `pH` | float | `6.5` | Initial pH |
| `temperature_C` | float | `28.0` | Incubation temperature (°C) |
| `rpm` | float | `200.0` | Agitation speed (rpm) |
| `inoculum_g_L` | float | `0.5` | Inoculum concentration (g/L) |
| `incubation_time_h` | float | `72.0` | Total incubation duration (h) |

#### Outcome columns (to be filled after experiments)

| Column | Type | Example | Description |
|---|---|---|---|
| `observed_growth_rate_h_inv` | float | `0.043` | Measured specific growth rate (h⁻¹) |
| `observed_biomass_g_L` | float | `12.4` | Measured biomass dry weight (g/L) |
| `observed_byproducts_g_L` | float | `1.8` | Total measured byproduct concentration (g/L) |

> **Note:** `overall_rank_score` is **not** required in the upload. GEMS computes it automatically during ingestion using min-max normalisation relative to the full combined dataset.

#### Optional columns

| Column | Description |
|---|---|
| `experiment_id` | Unique experiment identifier (auto-generated if absent) |
| `experiment_date` | Date of experiment (YYYY-MM-DD; defaults to upload date) |

---

## Understanding Recommendations

### Exploit vs Explore

GEMS outputs two types of recommendations to balance performance and learning.

**Exploit (🏆):**
- Conditions predicted to yield the highest `overall_rank_score`.
- Ranked #1 to #N by predicted composite score.
- Best used for the majority of experimental runs (4 out of 5).

**Explore (🔭):**
- A single condition from the top-10th-percentile predicted score bracket, but chosen for its **maximum uncertainty**.
- Use this as a deliberate "information-gathering" run.
- Especially valuable in early rounds when the model has seen little real data.

### Composite Score

`overall_rank_score` is computed as:

```
score = growth_norm + biomass_norm − byproduct_norm
```

where each component is min-max normalised [0, 1] across the full combined dataset. Scores range roughly from −1 (worst) to +2 (best), though the practical range depends on the data.

### Uncertainty

Uncertainty is estimated as the **standard deviation of predictions across all trees** in a Random Forest ensemble (the so-called "jackknife" uncertainty proxy).

| Uncertainty | Colour | Interpretation |
|---|---|---|
| < 0.10 | 🟢 Green | High confidence — model predictions are consistent |
| 0.10 – 0.20 | 🟡 Yellow | Moderate confidence — predictions are plausible but check with domain knowledge |
| > 0.20 | 🔴 Red | Low confidence — condition is outside well-sampled regions |

> **Tip:** High uncertainty in the exploit recommendations is a sign you need more real data. Prioritise the explore recommendation in your next batch.

---

## Retraining & Adaptive Weighting

### Why retrain?

The initial synthetic dataset was generated by a mechanistic model. While it provides broad coverage of the parameter space, it cannot perfectly capture strain-specific biological phenomena. Real wet-lab data corrects systematic biases in the synthetic prior.

### Adaptive sample weighting

Each training round assigns **sample weights** to balance synthetic and real data:

```
weight(synthetic row)  = 1.0  (constant)
weight(real row)       = REAL_WEIGHT_BASE + round × REAL_WEIGHT_SCALE
                       = 5.0  + round × 1.0
```

| Round | Real data weight |
|---|---|
| 0 (initial) | — (no real data) |
| 1 | 5.0× |
| 2 | 6.0× |
| 3 | 7.0× |
| … | … |

This ensures that as you accumulate real observations, the model increasingly prioritises them over the synthetic baseline — without discarding the synthetic data entirely (which provides useful regularisation when real data are sparse).

### What happens to model quality over rounds?

You should see:
- **Increasing CV R²** for targets that are strongly influenced by conditions you are testing.
- **Decreasing uncertainty** in exploit recommendations as the model learns from observed outcomes.
- **More targeted recommendations** as the model stops suggesting conditions that performed poorly in practice.

---

## Model Architecture

GEMS evaluates three model families per target and selects the best based on 5-fold cross-validated R²:

| Model | Library | Strengths |
|---|---|---|
| Random Forest | scikit-learn | Robust, interpretable uncertainty, no hypertuning needed |
| XGBoost | xgboost | High accuracy on tabular data, fast |
| LightGBM | lightgbm | Memory-efficient, excellent on large datasets |

### Feature pipeline

1. **Categorical encoding:** `LabelEncoder` per categorical column. Unseen labels (in predictions) are mapped to −1.
2. **Numeric scaling:** `StandardScaler` (zero mean, unit variance).
3. **Separate models per target:** Each of the four targets has its own best-fit model, allowing different model types to be selected per target.

### Uncertainty model

A dedicated `RandomForestRegressor` is always trained alongside the best-model for each target, exclusively for uncertainty estimation. Using multiple estimator trees enables per-sample prediction variance as a well-calibrated uncertainty proxy.

---

## Troubleshooting

### "No trained models found. Please train first."

**Cause:** You have not yet trained the initial model.  
**Fix:** Go to Tab 2 and click **🚀 Train Models on Current Dataset**.

---

### "Feature pipeline not found; train the model first."

**Cause:** The `encoders.pkl` / `scaler.pkl` artefacts in `data/intermediate/` are missing.  
**Fix:** Re-run training from Tab 2. Training saves these files automatically.

---

### "Missing required columns: [...]"

**Cause:** Your upload CSV is missing one or more required columns.  
**Fix:** Check the [Dataset Format](#dataset-format) section for the exact required column names. Common issues:
- Column name has a typo (`growth_rate` instead of `growth_rate_h_inv`).
- Observed columns are still named `observed_*` — make sure you followed the lab template format (GEMS auto-renames these).
- Feature columns are missing because the CSV was saved with the wrong delimiter.

---

### "Training failed: ..."

**Likely causes and fixes:**

| Message fragment | Probable cause | Fix |
|---|---|---|
| `KeyError: 'overall_rank_score'` | Combined CSV missing required column | Re-ingest data from Tab 5 |
| `ValueError: could not convert string to float` | Numeric column contains text values | Clean the CSV before uploading |
| `MemoryError` | Dataset too large for available RAM | Close other applications; consider reducing `N_CANDIDATES` in `config.py` |
| Module not found (xgboost / lightgbm) | Dependency not installed | Run `pip install -r requirements.txt` |

---

### Recommendations look identical across runs

**Cause:** The random seed is fixed (`rng = np.random.default_rng(42)`). Recommendations are deterministic for a given model and dataset.  
**Fix:** This is expected behaviour. Recommendations will change after each retrain round as the model updates.

---

### The app starts but shows a blank page

**Cause:** Streamlit version too old (pre-1.18).  
**Fix:** Upgrade: `pip install --upgrade streamlit`

---

### Data filter shows "Real Lab Rows: 0" after uploading

**Cause:** Upload was not successfully ingested (perhaps validation failed silently).  
**Fix:** Check the green/red status message that appears after clicking **✅ Validate & Ingest**. If it was red, read the error message for missing columns.

---

### Excel download fails with "openpyxl" error

**Fix:** `pip install openpyxl>=3.1.0`

---

## FAQ

**Q: Can I use my own synthetic data instead of the provided CSV?**  
A: Yes. Replace `data/synthetic_fungal_growth_dataset.csv` with your own CSV, ensuring all column names match exactly. Re-train from Tab 2.

**Q: Can I add a new strain?**  
A: Partially. Add the strain name to `STRAINS` in `backend/config.py`. The model will use it if the strain appears in the training data, but it cannot extrapolate recommendations for a strain it has never seen. Include rows for the new strain in your dataset first.

**Q: How many real data rows do I need before retraining is worthwhile?**  
A: The adaptive weighting starts helping from even 10–20 real rows. Meaningful improvement in CV R² typically needs 50+ rows. For a full production deployment, aim for 200+ real rows across all four strains.

**Q: Can I run GEMS without internet access?**  
A: Yes. GEMS is fully self-contained. All dependencies are installed locally.

**Q: Where is data stored?**  
A: All data lives under `GEMS/data/`:
- `data/synthetic_fungal_growth_dataset.csv` — read-only base dataset
- `data/intermediate/combined_dataset.csv` — evolves as you ingest real data
- `data/intermediate/encoders.pkl` / `scaler.pkl` — trained feature pipeline
- `data/models/` — one sub-directory per training run, plus `latest.json` pointer
- `data/models/retrain_log.json` — complete retrain history

**Q: How do I reset to a clean state?**  
A: Delete `data/intermediate/combined_dataset.csv` and `data/models/latest.json` (and optionally all model sub-directories). Re-train from Tab 2.

**Q: Can multiple users access GEMS simultaneously?**  
A: Streamlit Community Server (single-process) does not support concurrent writes safely. For multi-user deployments, use Streamlit Community Cloud with a shared database backend, or deploy on a server with a proper job queue.

---

*GEMS v1.0 — documentation last updated March 2026*
