"""Output helpers for optional draft-model validation.

This is an optional draft-model validation step before real media optimisation.
"""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .logging_utils import get_logger
from .plot_utils import PALETTE, annotate_barh, finalize_figure, style_axis


logger = get_logger(__name__)


def _prefixed_path(output_dir: Path, filename: str, prefix: str = "") -> Path:
    """Return an output path with an optional filename prefix."""
    return output_dir / f"{prefix}{filename}"


def _write_table(rows, outpath: Path, fieldnames):
    """Write a table using pandas if available, otherwise csv."""
    outpath.parent.mkdir(parents=True, exist_ok=True)
    try:
        pd.DataFrame(rows, columns=fieldnames).to_csv(outpath, index=False)
    except Exception:
        with outpath.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def save_validation_outputs(
    summary: dict,
    dead_end_rows,
    exchange_fva_rows,
    gene_essentiality_rows,
    outdir: str,
    prefix: str = "",
):
    """Save validation tables plus summary JSON and text."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _prefixed_path(output_dir, "validation_summary.json", prefix).write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    validation_context = summary.get("validation_context", {})
    lines = [
        "This is an optional draft-model validation step before real media optimisation.",
        f"validation_mode: {validation_context.get('validation_mode', 'default')}",
        f"validation_condition: {validation_context.get('condition_name', '')}",
        f"validation_biomass_reaction: {validation_context.get('biomass_reaction_id', '')}",
        f"n_added_boundaries: {validation_context.get('n_added_boundaries', 0)}",
        f"fba_status: {summary.get('fba', {}).get('status', '')}",
        f"objective_value: {summary.get('fba', {}).get('objective_value', '')}",
        f"n_dead_end_metabolites: {summary.get('dead_end_metabolites', {}).get('n_dead_end_metabolites', '')}",
        f"n_produced_only: {summary.get('dead_end_metabolites', {}).get('n_produced_only', '')}",
        f"n_consumed_only: {summary.get('dead_end_metabolites', {}).get('n_consumed_only', '')}",
        f"exchange_fva_status: {summary.get('exchange_fva', {}).get('status', '')}",
        f"n_exchange_reactions: {summary.get('exchange_fva', {}).get('n_exchange_reactions', '')}",
        f"gene_essentiality_status: {summary.get('gene_essentiality', {}).get('status', '')}",
        f"n_essential_genes: {summary.get('gene_essentiality', {}).get('n_essential_genes', '')}",
    ]
    _prefixed_path(output_dir, "validation_summary.txt", prefix).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    _write_table(
        dead_end_rows,
        _prefixed_path(output_dir, "dead_end_metabolites.csv", prefix),
        [
            "metabolite_id",
            "metabolite_name",
            "compartment",
            "status",
            "n_producing_reactions",
            "n_consuming_reactions",
            "producing_reactions",
            "consuming_reactions",
        ],
    )
    _write_table(
        exchange_fva_rows,
        _prefixed_path(output_dir, "exchange_fva.csv", prefix),
        [
            "reaction_id",
            "reaction_name",
            "minimum",
            "maximum",
            "range",
            "lower_bound",
            "upper_bound",
        ],
    )
    _write_table(
        gene_essentiality_rows,
        _prefixed_path(output_dir, "gene_essentiality.csv", prefix),
        ["gene_id", "growth", "essential"],
    )
    logger.info("Saved validation tables to %s", output_dir)


def save_validation_dashboard(summary: dict, outdir: str, prefix: str = ""):
    """Save a compact four-panel validation dashboard."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    size_labels = ["Reactions", "Metabolites", "Genes", "Exchanges"]
    size_values = [
        summary.get("model", {}).get("n_reactions", 0),
        summary.get("model", {}).get("n_metabolites", 0),
        summary.get("model", {}).get("n_genes", 0),
        summary.get("model", {}).get("n_exchanges", 0),
    ]

    dead_end_labels = ["Produced only", "Consumed only", "Isolated"]
    dead_end_values = [
        summary.get("dead_end_metabolites", {}).get("n_produced_only", 0),
        summary.get("dead_end_metabolites", {}).get("n_consumed_only", 0),
        summary.get("dead_end_metabolites", {}).get("n_isolated", 0),
    ]

    validation_labels = ["Exchange FVA", "Essential genes"]
    validation_values = [
        summary.get("exchange_fva", {}).get("n_exchange_reactions", 0),
        summary.get("gene_essentiality", {}).get("n_essential_genes", 0),
    ]

    validation_mode = summary.get("validation_context", {}).get("validation_mode", "default")
    figure, axes = plt.subplots(2, 2, figsize=(11, 7))
    figure.suptitle(
        f"Draft model validation dashboard ({validation_mode})",
        fontsize=14,
        fontweight="bold",
    )

    for axis in axes.flat:
        style_axis(axis, grid_axis="x")

    size_bars = axes[0, 0].barh(size_labels, size_values, color=PALETTE["media"])
    axes[0, 0].set_title("Model size")
    annotate_barh(axes[0, 0], size_bars, size_values)

    objective_value = summary.get("fba", {}).get("objective_value")
    fba_bars = axes[0, 1].barh(
        ["Baseline FBA"],
        [0.0 if objective_value is None else objective_value],
        color=PALETTE["validation"],
    )
    axes[0, 1].set_title(f"FBA: {summary.get('fba', {}).get('status', 'unknown')}")
    axes[0, 1].set_xlabel("Objective value")
    annotate_barh(
        axes[0, 1],
        fba_bars,
        [0.0 if objective_value is None else objective_value],
    )

    dead_end_bars = axes[1, 0].barh(dead_end_labels, dead_end_values, color=PALETTE["alert"])
    axes[1, 0].set_title("Dead-end metabolites")
    annotate_barh(axes[1, 0], dead_end_bars, dead_end_values)

    validation_bars = axes[1, 1].barh(
        validation_labels,
        validation_values,
        color=PALETTE["custom"],
    )
    axes[1, 1].set_title("Optional validation counts")
    annotate_barh(axes[1, 1], validation_bars, validation_values)

    outpath = _prefixed_path(output_dir, "validation_dashboard.png", prefix)
    finalize_figure(figure, outpath)
    logger.info("Saved validation dashboard to %s", outpath)
