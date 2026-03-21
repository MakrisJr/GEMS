"""Generate a side-by-side comparison report for two MVP model runs."""

import argparse
import csv
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_first(path_iterable):
    for path in path_iterable:
        return path
    return None


def _float_or_blank(value):
    if value is None:
        return ""
    return value


def _find_run_artifacts(model_dir: Path) -> dict:
    custom_json = _find_first(sorted(model_dir.glob("custom_condition_*.json")))
    custom_png = _find_first(sorted(model_dir.glob("custom_condition_*.png")))

    return {
        "model_summary": _load_json(model_dir / "model_summary.json") or {},
        "mvp_summary": _load_json(model_dir / "mvp_summary.json") or {},
        "theoretical": _load_json(model_dir / "theoretical_upper_bound.json") or {},
        "preset": _load_json(model_dir / "preset_conditions.json") or [],
        "validation": _load_json(model_dir / "theoretical_upper_bound_validation_summary.json") or {},
        "custom": _load_json(custom_json) if custom_json else {},
        "paths": {
            "mvp_mode_comparison": model_dir / "mvp_mode_comparison.png",
            "theoretical_plot": model_dir / "theoretical_upper_bound.png",
            "preset_plot": model_dir / "preset_conditions.png",
            "custom_plot": custom_png,
            "validation_plot": model_dir / "theoretical_upper_bound_validation_dashboard.png",
        },
    }


def _summarize_run(label: str, model_dir: Path, artifacts: dict) -> dict:
    model_summary = artifacts["model_summary"]
    mvp_summary = artifacts["mvp_summary"]
    theoretical = artifacts["theoretical"]
    preset = artifacts["preset"]
    validation = artifacts["validation"]
    custom = artifacts["custom"]
    best_preset = preset[0] if preset else {}
    validation_context = validation.get("validation_context", {})
    dead_end_summary = validation.get("dead_end_metabolites", {})

    return {
        "label": label,
        "model_dir": str(model_dir),
        "template_name": model_summary.get("template_name", mvp_summary.get("template_name", "")),
        "template_source": model_summary.get("template_source", mvp_summary.get("template_source", "")),
        "reactions": mvp_summary.get("n_reactions", model_summary.get("n_reactions", "")),
        "metabolites": mvp_summary.get("n_metabolites", model_summary.get("n_metabolites", "")),
        "genes": mvp_summary.get("n_genes", model_summary.get("n_genes", "")),
        "exchanges": mvp_summary.get("n_exchanges", ""),
        "baseline_objective_value": _float_or_blank(mvp_summary.get("baseline_objective_value")),
        "theoretical_biomass_reaction": theoretical.get(
            "biomass_reaction_id", validation_context.get("biomass_reaction_id", "")
        ),
        "theoretical_bio2_rate": _float_or_blank(theoretical.get("bio2_rate")),
        "theoretical_yield_proxy": _float_or_blank(theoretical.get("bio2_yield_on_total_added_flux")),
        "preset_best_condition": best_preset.get("display_name", best_preset.get("condition", "")),
        "preset_best_rate": _float_or_blank(best_preset.get("bio2_rate")),
        "custom_condition": custom.get("display_name", custom.get("condition", "")),
        "custom_rate": _float_or_blank(custom.get("bio2_rate")),
        "validation_dead_end_metabolites": dead_end_summary.get("n_dead_end_metabolites", ""),
        "validation_added_boundaries": validation_context.get("n_added_boundaries", ""),
    }


def _write_csv(rows: list[dict], outpath: Path):
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with outpath.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _plot_table(title: str, left_label: str, left_path: str, right_label: str, right_path: str) -> str:
    return (
        f"## {title}\n\n"
        "<table>\n"
        "  <tr>\n"
        f"    <th>{left_label}</th>\n"
        f"    <th>{right_label}</th>\n"
        "  </tr>\n"
        "  <tr>\n"
        f"    <td><img src=\"{left_path}\" width=\"100%\"></td>\n"
        f"    <td><img src=\"{right_path}\" width=\"100%\"></td>\n"
        "  </tr>\n"
        "</table>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a side-by-side comparison report for two MVP runs.")
    parser.add_argument("--left-model-dir", required=True, help="First model directory to compare.")
    parser.add_argument("--right-model-dir", required=True, help="Second model directory to compare.")
    parser.add_argument("--left-label", default="Left Run", help="Display label for the first run.")
    parser.add_argument("--right-label", default="Right Run", help="Display label for the second run.")
    parser.add_argument(
        "--outdir",
        default="docs/template_comparison",
        help="Output directory for the comparison report.",
    )
    args = parser.parse_args()

    left_dir = Path(args.left_model_dir)
    right_dir = Path(args.right_model_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    left_artifacts = _find_run_artifacts(left_dir)
    right_artifacts = _find_run_artifacts(right_dir)

    left_summary = _summarize_run(args.left_label, left_dir, left_artifacts)
    right_summary = _summarize_run(args.right_label, right_dir, right_artifacts)
    rows = [left_summary, right_summary]

    comparison = {
        "left": left_summary,
        "right": right_summary,
    }
    (outdir / "template_comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )
    _write_csv(rows, outdir / "template_comparison.csv")

    def rel(path: Path | None) -> str:
        if path is None or not path.exists():
            return ""
        try:
            return str(path.relative_to(outdir))
        except ValueError:
            return os.path.relpath(path, outdir)

    markdown = [
        "# Template Comparison Report",
        "",
        "Side-by-side comparison of the main MVP outputs for two template builds.",
        "",
        "## Summary Table",
        "",
        "| Metric | "
        + f"{args.left_label} | {args.right_label} |",
        "| --- | --- | --- |",
        f"| Template | {left_summary['template_name']} ({left_summary['template_source']}) | {right_summary['template_name']} ({right_summary['template_source']}) |",
        f"| Reactions | {left_summary['reactions']} | {right_summary['reactions']} |",
        f"| Metabolites | {left_summary['metabolites']} | {right_summary['metabolites']} |",
        f"| Genes | {left_summary['genes']} | {right_summary['genes']} |",
        f"| Exchanges | {left_summary['exchanges']} | {right_summary['exchanges']} |",
        f"| Baseline objective | {left_summary['baseline_objective_value']} | {right_summary['baseline_objective_value']} |",
        f"| Theoretical biomass reaction | {left_summary['theoretical_biomass_reaction']} | {right_summary['theoretical_biomass_reaction']} |",
        f"| Theoretical upper bound | {left_summary['theoretical_bio2_rate']} | {right_summary['theoretical_bio2_rate']} |",
        f"| Theoretical yield proxy | {left_summary['theoretical_yield_proxy']} | {right_summary['theoretical_yield_proxy']} |",
        f"| Best preset condition | {left_summary['preset_best_condition']} | {right_summary['preset_best_condition']} |",
        f"| Best preset rate | {left_summary['preset_best_rate']} | {right_summary['preset_best_rate']} |",
        f"| Custom condition | {left_summary['custom_condition']} | {right_summary['custom_condition']} |",
        f"| Custom rate | {left_summary['custom_rate']} | {right_summary['custom_rate']} |",
        f"| Dead-end metabolites | {left_summary['validation_dead_end_metabolites']} | {right_summary['validation_dead_end_metabolites']} |",
        f"| Added validation boundaries | {left_summary['validation_added_boundaries']} | {right_summary['validation_added_boundaries']} |",
        "",
        "## Main Output Files",
        "",
        f"- {args.left_label}: `{left_dir}`",
        f"- {args.right_label}: `{right_dir}`",
        "",
        _plot_table(
            "MVP Mode Comparison",
            args.left_label,
            rel(left_artifacts["paths"]["mvp_mode_comparison"]),
            args.right_label,
            rel(right_artifacts["paths"]["mvp_mode_comparison"]),
        ),
        _plot_table(
            "Theoretical Upper Bound Plot",
            args.left_label,
            rel(left_artifacts["paths"]["theoretical_plot"]),
            args.right_label,
            rel(right_artifacts["paths"]["theoretical_plot"]),
        ),
        _plot_table(
            "Preset Conditions Plot",
            args.left_label,
            rel(left_artifacts["paths"]["preset_plot"]),
            args.right_label,
            rel(right_artifacts["paths"]["preset_plot"]),
        ),
        _plot_table(
            "Custom Condition Plot",
            args.left_label,
            rel(left_artifacts["paths"]["custom_plot"]),
            args.right_label,
            rel(right_artifacts["paths"]["custom_plot"]),
        ),
        _plot_table(
            "Theoretical Validation Dashboard",
            args.left_label,
            rel(left_artifacts["paths"]["validation_plot"]),
            args.right_label,
            rel(right_artifacts["paths"]["validation_plot"]),
        ),
        "## Notes",
        "",
        "- The comparison uses the same input FASTA for both runs.",
        "- Theoretical mode can use different biomass-like reactions if a template does not contain `bio2`.",
        "- Preset and custom conditions are still draft-model screening tools, not wet-lab media recommendations.",
    ]

    (outdir / "template_comparison.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")

    print(f"Saved comparison markdown: {outdir / 'template_comparison.md'}")
    print(f"Saved comparison JSON: {outdir / 'template_comparison.json'}")
    print(f"Saved comparison CSV: {outdir / 'template_comparison.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
