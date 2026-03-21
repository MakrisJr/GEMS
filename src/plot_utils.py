"""Shared plotting helpers for draft-model outputs."""

from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt


FIGURE_BG = "#F7F2EA"
AXES_BG = "#FFFDFC"
GRID = "#D8CFC2"
TEXT = "#2F2A24"
MUTED = "#7F7468"
BORDER = "#C7B9A8"

PALETTE = {
    "theoretical": "#C6653A",
    "preset": "#3F7D66",
    "preset_alt": "#76A992",
    "custom": "#D4972B",
    "media": "#537A9F",
    "debug": "#A14F76",
    "validation": "#5E8B7E",
    "alert": "#D16A5A",
}


def wrap_label(value: str, width: int = 18) -> str:
    """Return a readable wrapped label for plotting."""
    return fill(str(value).replace("_", " "), width=width)


def format_value(value) -> str:
    """Format a numeric value for labels."""
    if value is None:
        return "NA"

    numeric = float(value)
    if numeric == 0:
        return "0.00"
    if abs(numeric) >= 100:
        return f"{numeric:.1f}"
    if abs(numeric) >= 1:
        return f"{numeric:.2f}"
    return f"{numeric:.4f}"


def style_axis(axis, grid_axis: str = "x"):
    """Apply a clean shared style to one axis."""
    axis.set_facecolor(AXES_BG)
    axis.grid(axis=grid_axis, color=GRID, linestyle=(0, (2, 4)), linewidth=0.9)
    axis.set_axisbelow(True)
    axis.tick_params(colors=TEXT, labelsize=10)
    axis.xaxis.label.set_color(TEXT)
    axis.yaxis.label.set_color(TEXT)
    axis.title.set_color(TEXT)
    for side in ["top", "right"]:
        axis.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        axis.spines[side].set_color(BORDER)


def finalize_figure(figure, outpath: Path):
    """Save a styled figure and close it."""
    figure.patch.set_facecolor(FIGURE_BG)
    figure.tight_layout()
    figure.savefig(outpath, dpi=160, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def annotate_barh(axis, bars, values):
    """Add value labels to a horizontal bar chart."""
    numeric_values = [float(value) for value in values if value is not None]
    max_value = max(numeric_values) if numeric_values else 0.0
    offset = max(0.02 * max_value, 0.02) if max_value > 0 else 0.02

    for bar, value in zip(bars, values):
        numeric_value = 0.0 if value is None else float(value)
        x_position = numeric_value + offset if numeric_value >= 0 else numeric_value - offset
        horizontal_alignment = "left" if numeric_value >= 0 else "right"
        axis.text(
            x_position,
            bar.get_y() + bar.get_height() / 2,
            format_value(value),
            va="center",
            ha=horizontal_alignment,
            fontsize=9,
            color=TEXT,
            fontweight="semibold",
        )


def save_ranked_barh_plot(
    labels,
    values,
    outpath: Path,
    title: str,
    xlabel: str,
    colors=None,
    subtitle: str = "",
):
    """Save a polished horizontal bar plot."""
    if not labels:
        return

    wrapped_labels = [wrap_label(label) for label in labels]
    chart_colors = colors or [PALETTE["media"]] * len(labels)
    figure_height = max(4.5, len(labels) * 0.55 + 1.8)
    figure, axis = plt.subplots(figsize=(9, figure_height))
    style_axis(axis, grid_axis="x")

    numeric_values = [0.0 if value is None else float(value) for value in values]
    bars = axis.barh(
        range(len(labels)),
        numeric_values,
        color=chart_colors,
        edgecolor=AXES_BG,
        linewidth=1.2,
        height=0.68,
    )
    axis.set_yticks(range(len(labels)), wrapped_labels)
    axis.invert_yaxis()
    axis.set_title(title, fontsize=14, fontweight="bold", pad=18)
    if subtitle:
        axis.text(
            0.0,
            0.995,
            subtitle,
            transform=axis.transAxes,
            fontsize=9,
            color=MUTED,
            va="bottom",
        )
    axis.set_xlabel(xlabel, fontsize=11)

    max_value = max(numeric_values) if numeric_values else 0.0
    min_value = min(numeric_values) if numeric_values else 0.0
    if max_value == min_value:
        upper = max(1.0, max_value * 1.2 + 0.1)
        lower = min(0.0, min_value)
        axis.set_xlim(lower, upper)
    elif min_value >= 0:
        axis.set_xlim(0.0, max_value * 1.16)
    else:
        span = max_value - min_value
        axis.set_xlim(min_value - span * 0.08, max_value + span * 0.12)

    annotate_barh(axis, bars, values)
    finalize_figure(figure, outpath)
