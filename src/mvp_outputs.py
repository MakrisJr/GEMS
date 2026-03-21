"""Output helpers for the hackathon MVP wrappers.

This is a draft model analysis layer before real media optimisation.
"""

import json
import re
from pathlib import Path

import pandas as pd

from .logging_utils import get_logger
from .plot_utils import PALETTE, save_ranked_barh_plot
from .report_utils import make_report, make_section


logger = get_logger(__name__)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _save_single_bar_plot(label: str, value, title: str, ylabel: str, outpath: Path, color: str):
    """Save a simple one-condition bar plot."""
    save_ranked_barh_plot(
        [label],
        [value],
        outpath=outpath,
        title=title,
        xlabel=ylabel,
        colors=[color],
    )
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
        labels.append(theoretical.get("display_name", "Theoretical Upper Bound"))
        values.append(0.0 if theoretical.get("bio2_rate") is None else theoretical.get("bio2_rate"))
        colors.append(PALETTE["theoretical"])

    preset_results = _load_json_if_exists(output_dir / "preset_conditions.json") or []
    for row in preset_results:
        labels.append(row.get("display_name", row.get("condition", "")))
        values.append(0.0 if row.get("bio2_rate") is None else row.get("bio2_rate"))
        colors.append(PALETTE["preset"])

    custom_paths = sorted(output_dir.glob("custom_condition_*.json"))
    for path in custom_paths:
        row = _load_json_if_exists(path) or {}
        labels.append(row.get("display_name", row.get("condition", "")))
        values.append(0.0 if row.get("bio2_rate") is None else row.get("bio2_rate"))
        colors.append(PALETTE["custom"])

    if not labels:
        return

    save_ranked_barh_plot(
        labels,
        values,
        outpath=output_dir / "mvp_mode_comparison.png",
        title="MVP condition comparison on a draft model",
        xlabel="Predicted bio2 rate",
        colors=colors,
        subtitle="Theoretical, preset, and saved custom analyses on the same draft model.",
    )
    logger.info("Saved mode comparison plot to %s", output_dir / "mvp_mode_comparison.png")


def save_theoretical_upper_bound(result: dict, outdir: str):
    """Save the theoretical upper bound output."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "theoretical_upper_bound.json"
    txt_path = output_dir / "theoretical_upper_bound.txt"
    png_path = output_dir / "theoretical_upper_bound.png"
    csv_path = output_dir / "theoretical_upper_bound_conditions.csv"
    conditions_txt_path = output_dir / "theoretical_upper_bound_conditions.txt"

    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    txt_path.write_text(
        make_report(
            "Theoretical Upper Bound Report",
            [
                make_section(
                    "Summary",
                    [
                        "Best-case benchmark on a draft model under idealized input availability.",
                        "This is not a wet-lab medium recommendation.",
                    ],
                ),
                make_section(
                    "Results",
                    [
                        f"Condition: {result.get('display_name', result.get('condition', ''))}",
                        f"Status: {result.get('status', '')}",
                        f"Predicted bio2 rate: {result.get('bio2_rate', '')}",
                        f"Yield proxy: {result.get('bio2_yield_on_total_added_flux', '')}",
                        f"Temporary boundaries added: {result.get('n_added_boundaries', 0)}",
                    ],
                ),
            ],
        ),
        encoding="utf-8",
    )

    boundary_rows = list(result.get("boundary_fluxes", []))
    if boundary_rows:
        pd.DataFrame(boundary_rows).to_csv(csv_path, index=False)
    else:
        pd.DataFrame(
            [{"metabolite_id": metabolite_id} for metabolite_id in result.get("metabolite_ids", [])]
        ).to_csv(csv_path, index=False)

    boundary_lines = []
    for row in boundary_rows:
        boundary_lines.append(
            f"{row.get('metabolite_id', '')} | {row.get('metabolite_name', '')} | "
            f"{row.get('boundary_id', '')} | flux={row.get('flux', '')} | abs_flux={row.get('abs_flux', '')}"
        )
    conditions_txt_path.write_text(
        make_report(
            "Theoretical Upper Bound Condition Values",
            [
                make_section(
                    "Overview",
                    [
                        "Optimized temporary boundary values used by the theoretical upper-bound solution.",
                        f"Biomass reaction: {result.get('biomass_reaction_id', '')}",
                        f"Status: {result.get('status', '')}",
                        f"Predicted bio2 rate: {result.get('bio2_rate', '')}",
                        f"Yield proxy: {result.get('bio2_yield_on_total_added_flux', '')}",
                        f"Total added boundary flux: {result.get('total_added_boundary_flux', '')}",
                    ],
                ),
                make_section("Boundary Fluxes", boundary_lines),
            ],
        ),
        encoding="utf-8",
    )

    _save_single_bar_plot(
        label="Theoretical Upper Bound",
        value=result.get("bio2_rate"),
        title="Theoretical upper bound on a draft model",
        ylabel="Predicted bio2 rate",
        outpath=png_path,
        color=PALETTE["theoretical"],
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
                "display_name": row.get("display_name", row.get("condition", "")),
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

    summary_lines = [
        "Pre-made benchmark conditions for comparing draft-model behavior.",
    ]
    if results:
        best = results[0]
        summary_lines.extend(
            [
                f"Best condition: {best.get('display_name', best.get('condition', ''))}",
                f"Best bio2 rate: {best.get('bio2_rate', '')}",
                f"Best yield proxy: {best.get('bio2_yield_on_total_added_flux', '')}",
            ]
        )
    ranking_lines = []
    for row in table_rows:
        ranking_lines.append(
            f"{row['display_name']}: rate={row['bio2_rate']}, yield={row['bio2_yield_on_total_added_flux']}, status={row['status']}"
        )
    (output_dir / "preset_conditions.txt").write_text(
        make_report(
            "Preset Conditions Report",
            [
                make_section("Summary", summary_lines),
                make_section("Ranked Conditions", ranking_lines),
            ],
        ),
        encoding="utf-8",
    )

    conditions = [row["display_name"] for row in table_rows]
    rates = [0.0 if row["bio2_rate"] is None else row["bio2_rate"] for row in table_rows]
    colors = [PALETTE["preset"]] + [PALETTE["preset_alt"]] * max(0, len(conditions) - 1)
    save_ranked_barh_plot(
        conditions,
        rates,
        outpath=output_dir / "preset_conditions.png",
        title="Preset benchmark conditions on a draft model",
        xlabel="Predicted bio2 rate",
        colors=colors,
        subtitle="Higher bars indicate better biomass-like performance under the preset condition set.",
    )
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
    txt_path.write_text(
        make_report(
            "Custom Condition Report",
            [
                make_section(
                    "Summary",
                    [
                        "User-defined comparison condition on the draft model.",
                        f"Condition: {result.get('display_name', result.get('condition', ''))}",
                        f"Status: {result.get('status', '')}",
                        f"Predicted bio2 rate: {result.get('bio2_rate', '')}",
                        f"Yield proxy: {result.get('bio2_yield_on_total_added_flux', '')}",
                    ],
                ),
                make_section("Metabolites Used", result.get("metabolite_ids", [])),
            ],
        ),
        encoding="utf-8",
    )
    _save_single_bar_plot(
        label=result.get("display_name", result.get("condition", "custom_condition")),
        value=result.get("bio2_rate"),
        title="Custom condition on a draft model",
        ylabel="Predicted bio2 rate",
        outpath=png_path,
        color=PALETTE["custom"],
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

    txt_path.write_text(
        make_report(
            "Fungal GEM MVP Summary",
            [
                make_section(
                    "Model Build",
                    [
                        f"Model ID: {summary.get('model_id', '')}",
                        f"Input path: {summary.get('input_path', '')}",
                        f"Template name: {summary.get('template_name', '')}",
                        f"Template source: {summary.get('template_source', '')}",
                        f"Model directory: {summary.get('model_dir', '')}",
                        f"Exported model path: {summary.get('exported_model_path', '')}",
                    ],
                ),
                make_section(
                    "Model Overview",
                    [
                        f"Reactions: {summary.get('n_reactions', '')}",
                        f"Metabolites: {summary.get('n_metabolites', '')}",
                        f"Genes: {summary.get('n_genes', '')}",
                        f"Exchanges: {summary.get('n_exchanges', '')}",
                        f"Objective: {summary.get('objective', '')}",
                    ],
                ),
                make_section(
                    "Baseline Inspection",
                    [
                        f"Baseline status: {summary.get('baseline_status', '')}",
                        f"Baseline objective value: {summary.get('baseline_objective_value', '')}",
                        f"Inspection success: {summary.get('inspection_success', False)}",
                    ],
                ),
            ],
        ),
        encoding="utf-8",
    )
    logger.info("Saved MVP summary to %s", output_dir)
