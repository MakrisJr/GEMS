"""Output helpers for the hackathon MVP wrappers.

This is a draft model analysis layer before real media optimisation.
"""

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .logging_utils import get_logger


logger = get_logger(__name__)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _save_single_bar_plot(label: str, value, title: str, ylabel: str, outpath: Path, color: str):
    """Save a simple one-condition bar plot."""
    figure, axis = plt.subplots(figsize=(6, 4))
    axis.bar([label], [0.0 if value is None else value], color=color)
    axis.set_title(title)
    axis.set_ylabel(ylabel)
    axis.set_xlabel("Condition")
    figure.tight_layout()
    figure.savefig(outpath, dpi=150)
    plt.close(figure)
    logger.info("Saved plot to %s", outpath)


def _load_json_if_exists(path: Path):
    """Load JSON if the file exists, otherwise return None."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_mode_comparison_plot(outdir: str):
    """Save a combined comparison plot across available MVP analysis modes."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = []
    values = []
    colors = []

    theoretical = _load_json_if_exists(output_dir / "theoretical_upper_bound.json")
    if theoretical is not None:
        labels.append("Theoretical")
        values.append(0.0 if theoretical.get("bio2_rate") is None else theoretical.get("bio2_rate"))
        colors.append("#4C78A8")

    preset_results = _load_json_if_exists(output_dir / "preset_conditions.json") or []
    for row in preset_results:
        labels.append(f"Preset: {row.get('condition', '')}")
        values.append(0.0 if row.get("bio2_rate") is None else row.get("bio2_rate"))
        colors.append("#59A14F")

    custom_paths = sorted(output_dir.glob("custom_condition_*.json"))
    for path in custom_paths:
        row = _load_json_if_exists(path) or {}
        labels.append(f"Custom: {row.get('condition', '')}")
        values.append(0.0 if row.get("bio2_rate") is None else row.get("bio2_rate"))
        colors.append("#E15759")

    if not labels:
        return

    figure, axis = plt.subplots(figsize=(max(8, len(labels) * 1.2), 4.8))
    axis.bar(labels, values, color=colors)
    axis.set_title("MVP condition comparison on a draft model")
    axis.set_ylabel("Predicted bio2 rate")
    axis.set_xlabel("Analysis output")
    axis.tick_params(axis="x", rotation=25)
    figure.tight_layout()
    figure.savefig(output_dir / "mvp_mode_comparison.png", dpi=150)
    plt.close(figure)
    logger.info("Saved mode comparison plot to %s", output_dir / "mvp_mode_comparison.png")


def save_theoretical_upper_bound(result: dict, outdir: str):
    """Save the theoretical upper bound output."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "theoretical_upper_bound.json"
    txt_path = output_dir / "theoretical_upper_bound.txt"
    png_path = output_dir / "theoretical_upper_bound.png"

    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "This is a draft model analysis layer before real media optimisation.",
        "Mode: Theoretical Upper Bound",
        "This is a best-case benchmark, not a wet-lab medium recommendation.",
        f"condition: {result.get('condition', '')}",
        f"bio2_rate: {result.get('bio2_rate', '')}",
        f"bio2_yield_on_total_added_flux: {result.get('bio2_yield_on_total_added_flux', '')}",
        f"status: {result.get('status', '')}",
        f"n_added_boundaries: {result.get('n_added_boundaries', 0)}",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _save_single_bar_plot(
        label="Theoretical Upper Bound",
        value=result.get("bio2_rate"),
        title="Theoretical upper bound on a draft model",
        ylabel="Predicted bio2 rate",
        outpath=png_path,
        color="#4C78A8",
    )
    save_mode_comparison_plot(str(output_dir))
    logger.info("Saved theoretical upper bound outputs to %s", output_dir)


def save_preset_benchmark(results, outdir: str):
    """Save preset benchmark outputs and a small comparison plot."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    table_rows = []
    for row in results:
        table_rows.append(
            {
                "condition": row.get("condition", ""),
                "description": row.get("description", ""),
                "bio2_rate": row.get("bio2_rate"),
                "bio2_yield_on_total_added_flux": row.get("bio2_yield_on_total_added_flux"),
                "status": row.get("status", ""),
                "n_added_boundaries": row.get("n_added_boundaries", 0),
            }
        )

    pd.DataFrame(table_rows).to_csv(output_dir / "preset_conditions.csv", index=False)
    (output_dir / "preset_conditions.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )

    lines = [
        "This is a draft model analysis layer before real media optimisation.",
        "Mode: Preset Conditions",
        "These are pre-made benchmark conditions for comparing model behavior.",
    ]
    if results:
        best = results[0]
        lines.append(f"best_condition: {best.get('condition', '')}")
        lines.append(f"best_bio2_rate: {best.get('bio2_rate', '')}")
        lines.append(
            "best_bio2_yield_on_total_added_flux: "
            f"{best.get('bio2_yield_on_total_added_flux', '')}"
        )
    for row in table_rows:
        lines.append(
            f"{row['condition']}: rate={row['bio2_rate']}, yield={row['bio2_yield_on_total_added_flux']}, status={row['status']}"
        )
    (output_dir / "preset_conditions.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    conditions = [row["condition"] for row in table_rows]
    rates = [0.0 if row["bio2_rate"] is None else row["bio2_rate"] for row in table_rows]
    plt.figure(figsize=(9, 4.5))
    plt.bar(conditions, rates)
    plt.ylabel("Predicted bio2 rate")
    plt.xlabel("Preset Condition")
    plt.title("Preset benchmark conditions on a draft model")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "preset_conditions.png", dpi=150)
    plt.close()
    save_mode_comparison_plot(str(output_dir))
    logger.info("Saved preset benchmark outputs to %s", output_dir)


def save_custom_condition(result: dict, outdir: str):
    """Save one user-defined custom condition output."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    condition_name = _safe_name(result.get("condition", "custom_condition"))
    json_path = output_dir / f"custom_condition_{condition_name}.json"
    txt_path = output_dir / f"custom_condition_{condition_name}.txt"
    png_path = output_dir / f"custom_condition_{condition_name}.png"

    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "This is a draft model analysis layer before real media optimisation.",
        "Mode: Custom Condition",
        f"condition: {result.get('condition', '')}",
        f"bio2_rate: {result.get('bio2_rate', '')}",
        f"bio2_yield_on_total_added_flux: {result.get('bio2_yield_on_total_added_flux', '')}",
        f"status: {result.get('status', '')}",
        "metabolite_ids:",
    ]
    for metabolite_id in result.get("metabolite_ids", []):
        lines.append(metabolite_id)
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _save_single_bar_plot(
        label=result.get("condition", "custom_condition"),
        value=result.get("bio2_rate"),
        title="Custom condition on a draft model",
        ylabel="Predicted bio2 rate",
        outpath=png_path,
        color="#E15759",
    )
    save_mode_comparison_plot(str(output_dir))
    logger.info("Saved custom condition outputs to %s", output_dir)


def save_mvp_summary(summary: dict, outdir: str):
    """Save a short MVP pipeline summary."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "mvp_summary.json"
    txt_path = output_dir / "mvp_summary.txt"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "Fungal GEM MVP summary",
        f"model_id: {summary.get('model_id', '')}",
        f"input_path: {summary.get('input_path', '')}",
        f"model_dir: {summary.get('model_dir', '')}",
        f"exported_model_path: {summary.get('exported_model_path', '')}",
        f"n_reactions: {summary.get('n_reactions', '')}",
        f"n_metabolites: {summary.get('n_metabolites', '')}",
        f"n_genes: {summary.get('n_genes', '')}",
        f"n_exchanges: {summary.get('n_exchanges', '')}",
        f"objective: {summary.get('objective', '')}",
        f"baseline_status: {summary.get('baseline_status', '')}",
        f"baseline_objective_value: {summary.get('baseline_objective_value', '')}",
        f"inspection_success: {summary.get('inspection_success', False)}",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved MVP summary to %s", output_dir)
