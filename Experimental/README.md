# Geometry-Aware Optimization of Fungal Fermentation Conditions

## Overview

This project implements a decision system for identifying optimal fermentation conditions in filamentous fungi using a combination of:

* Genome-scale metabolic modeling (GEM + FBA)
* Convex geometry (polytope sampling)
* Machine learning (surrogate modeling and ranking)

The goal is to determine **environmental conditions (media + process parameters)** that:

* maximize growth and biomass production
* minimize byproducts and waste
* align with industrial constraints (cost, morphology proxies)

---

## Pipeline Summary

1. **Scenario generation**
   Define candidate fermentation conditions (nutrients, pH, temperature, mixing)

2. **Mechanistic simulation (FBA)**
   Evaluate each condition using a fungal GEM

3. **Feasible space analysis (PolyRound + sampling)**
   Characterize the full metabolic solution space

4. **Feature extraction**
   Compute biological + geometric features

5. **Dataset construction**
   Build structured dataset of scenarios

6. **Model training**
   Train surrogate ML model

7. **Ranking & decision layer**
   Rank conditions using multi-objective score

---

## Project Structure

### Core Pipeline

#### `dataset_builder.py`

Builds the dataset by:

* loading GEM model
* applying medium constraints
* running FBA
* computing FVA
* constructing polytope and sampling
* extracting geometry features
* saving dataset to `results/dataset.csv`

This is the **main backend engine**.

---

#### `train_model.py`

* trains regression model on dataset
* predicts performance score
* saves model to `results/model.pkl`

---

#### `rank_scenarios.py`

* applies trained model
* ranks scenarios based on predicted performance
* outputs:

  * `results/predicted_ranked_scenarios.csv`

---

## Interpretation & Analysis

#### `feature_importance.py`

* computes feature importance from trained model
* shows which variables drive performance
* output:

  * `results/feature_importances.csv`

---

#### `top_region_summary.py`

* summarizes top-performing scenarios
* computes:

  * median values
  * ranges of variables
* output:

  * `results/top_region_summary.txt`

---

#### `plot_pareto.py`

* plots growth vs byproduct tradeoff
* highlights optimal scenarios
* output:

  * `results/pareto_growth_vs_byproduct.png`

---

## Industrial Scoring Layer

#### `postprocess_scores.py`

* computes additional industrial metrics:

  * economic_score
  * morphology_score
  * meatiness_score
* outputs:

  * `results/dataset_postprocessed.csv`

---

#### `rank_scenarios_industrial.py`

* ranks scenarios using industrial_score
* outputs:

  * `results/predicted_ranked_scenarios_industrial.csv`

---

#### `plot_industrial_tradeoff.py`

* plots:

  * industrial_score vs growth
  * colored by economic / metabolic features
* output:

  * `results/plot_industrial_tradeoff.png`

---

## Utility Scripts

#### `test_fungal_model.py`

* verifies model loading and biomass reaction
* used for debugging GEM setup

---

#### `reactions.py`

* searches reactions by keyword
* helps identify:

  * uptake reactions
  * transport reactions
  * biomass reaction

---

## Input Files

#### `A_oryzae_optimized.xml`

* fungal genome-scale metabolic model (GEM)
* used for all simulations

---

#### `scenarios_fungi.json`

* list of fermentation scenarios
* each scenario defines:

  * nutrient bounds
  * temperature
  * pH
  * mixing

---

## Output Files

All outputs are stored in:

```id="v21x7r"
results/
```

Key outputs:

* `dataset.csv` → full dataset
* `model.pkl` → trained model
* `predicted_ranked_scenarios.csv` → ranking
* `predicted_ranked_scenarios_industrial.csv` → final industrial ranking
* `feature_importances.csv`
* `top_region_summary.txt`
* `plot_industrial_tradeoff.png`

---

## How to Run

### 1. Build dataset

```bash
PYTHONPATH=. poetry run python dingo/dataset_builder.py
```

### 2. Train model

```bash
PYTHONPATH=. poetry run python dingo/train_model.py
```

### 3. Rank scenarios

```bash
PYTHONPATH=. poetry run python dingo/rank_scenarios.py
```

### 4. Interpret results

```bash
PYTHONPATH=. poetry run python dingo/feature_importance.py
PYTHONPATH=. poetry run python dingo/top_region_summary.py
```

### 5. Industrial scoring

```bash
PYTHONPATH=. poetry run python dingo/postprocess_scores.py
PYTHONPATH=. poetry run python dingo/rank_scenarios_industrial.py
PYTHONPATH=. poetry run python dingo/plot_industrial_tradeoff.py
```

---

## Key Idea

Instead of optimizing a single metabolic solution, this system:

* explores the full feasible metabolic space
* extracts geometric and biological features
* learns how environmental conditions shape performance
* identifies **robust and efficient operating regions**

---

## Limitations (Current Prototype)

* fungal byproduct mapping not yet fully implemented
* biomass yield may be constant in some GEMs
* runtime is high due to polytope rounding

---

## Future Work

* integrate fungal-specific byproducts
* improve economic and morphology models
* parallelize dataset generation
* extend to additional fungal species

---

## Summary

This project provides a **geometry-aware, biologically grounded optimization framework** for fermentation design, combining:

* mechanistic modeling
* convex geometry
* machine learning

to produce actionable insights for industrial biotechnology.
