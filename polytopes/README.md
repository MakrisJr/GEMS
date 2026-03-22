# Geometry-Aware Optimization of Fungal Fermentation Conditions

## Overview

Minimal decision system for optimizing fermentation conditions in filamentous fungi using:

* Genome-scale metabolic modeling (GEM + FBA)
* Convex geometry (polytope sampling)
* Machine learning (surrogate modeling and ranking)

## What Goes In

* Fungal GEM (`.xml`, COBRA-compatible)
* Scenario file (`scenarios_fungi.json`)

Each scenario defines:

* nutrient bounds (glucose, ammonium, phosphate, sulfate)
* process parameters (temperature, pH, mixing)

## What Comes Out

* Ranked fermentation conditions
* Optimal operating region summaries
* Tradeoff visualizations (growth vs byproducts vs industrial score)
* Feature importance analysis
* Industrial scoring outputs

---

## Official Commands

These are the main entry points.

### Build dataset

```bash
PYTHONPATH=. poetry run python dingo/dataset_builder.py
```

### Train surrogate model

```bash
PYTHONPATH=. poetry run python dingo/train_model.py
```

### Rank scenarios

```bash
PYTHONPATH=. poetry run python dingo/rank_scenarios.py
```

### Interpretation

```bash
PYTHONPATH=. poetry run python dingo/feature_importance.py
PYTHONPATH=. poetry run python dingo/top_region_summary.py
```

### Industrial scoring

```bash
PYTHONPATH=. poetry run python dingo/postprocess_scores.py
PYTHONPATH=. poetry run python dingo/rank_scenarios_industrial.py
PYTHONPATH=. poetry run python dingo/plot_industrial_tradeoff.py
```

---

## Pipeline

### Scenario Generation

Define candidate environmental and process conditions.

### Mechanistic Simulation

Run FBA on the fungal GEM for each scenario.

### Feasible Space Analysis

Construct the flux polytope and sample it using PolyRound.

### Feature Extraction

Compute:

* biological metrics (growth, flux statistics)
* geometric metrics (volume proxy, anisotropy, variability)

### Dataset Construction

Aggregate all scenario-level features into a structured dataset.

### Model Training

Train a regression model to predict performance.

### Ranking

Rank scenarios using multi-objective criteria:

* growth
* biomass / yield
* byproducts
* industrial proxies

---

## Analysis Modes

### Performance Ranking

Predict and rank scenarios based on learned performance.

### Top-Region Summary

Compute median and range of variables among top scenarios.

### Pareto Analysis

Visualize tradeoff:

* growth vs byproducts

### Industrial Tradeoff

Visualize:

* industrial_score vs growth
* colored by economic / metabolic features

---

## Recommended Demo Outputs

If presenting live, show:

* `plot_industrial_tradeoff.png`
* `pareto_growth_vs_byproduct.png`
* `top_region_summary.txt`
* `feature_importances.csv`

---

## Project Structure

### Core

* `dataset_builder.py` → builds dataset (main engine)
* `train_model.py` → trains surrogate model
* `rank_scenarios.py` → baseline ranking

### Analysis

* `feature_importance.py` → drivers of performance
* `top_region_summary.py` → optimal ranges
* `plot_pareto.py` → growth vs byproduct

### Industrial Layer

* `postprocess_scores.py` → industrial metrics
* `rank_scenarios_industrial.py` → final ranking
* `plot_industrial_tradeoff.py` → tradeoff visualization

### Utilities

* `test_fungal_model.py` → GEM validation
* `reactions.py` → reaction lookup

---

## Input

* `A_oryzae_optimized.xml` → fungal GEM
* `scenarios_fungi.json` → fermentation conditions

---

## Output

Stored in:

```
results/
```

Key files:

* `dataset.csv`
* `model.pkl`
* `predicted_ranked_scenarios.csv`
* `predicted_ranked_scenarios_industrial.csv`
* `feature_importances.csv`
* `top_region_summary.txt`
* `plot_industrial_tradeoff.png`

---

## Key Idea

Instead of optimizing a single flux solution, this system:

* explores the full feasible metabolic space
* extracts geometric + biological features
* learns condition → performance relationships
* identifies robust operating regions

---

## Important Notes

* This is a **post-GEM optimization pipeline**
* It assumes a valid fungal metabolic model is already available
* Results reflect **model-based predictions**, not direct wet-lab validation

---

## Current Scope

* Evaluate fermentation conditions for a given fungal GEM
* Perform geometry-aware analysis of metabolic feasibility
* Rank conditions using multi-objective scoring
* Include fungal-specific byproduct-aware evaluation for *A. oryzae*

---

## Limitations

* Fungal byproduct mapping is currently implemented for *A. oryzae* only
* Biomass yield may be nearly constant in some GEM configurations
* Runtime is high due to polytope preprocessing and sampling

---

## Planned Next Steps

* Extend byproduct mapping to additional fungal species
* Improve morphology and techno-economic scoring
* Parallelize dataset generation
* Integrate guided (non-random) scenario search

---

## Summary

Geometry-aware optimization layer for fungal fermentation design:

* uses GEMs as mechanistic backbone
* augments them with convex geometry
* learns performance using machine learning

Produces:

* ranked conditions
* interpretable optimal regions
* tradeoff-aware industrial recommendations

---



