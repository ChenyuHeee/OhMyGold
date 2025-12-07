import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

# Absolute path to repository root is resolved relative to this file.
REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURE_PATH = REPO_ROOT / "academic" / "figures" / "system_overview.png"


def add_box(ax, xy, width, height, label, details, color):
    """Draw a rounded box with a heading and wrapped body text."""
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.05,rounding_size=0.06",
        linewidth=1.5,
        edgecolor="#1a1a1a",
        facecolor=color,
    )
    ax.add_patch(box)

    title_y = xy[1] + height * 0.88
    body_y = xy[1] + height * 0.48

    ax.text(
        xy[0] + width / 2,
        title_y,
        label,
        ha="center",
        va="top",
        fontsize=18,
        fontweight="bold",
        color="#101820",
    )

    wrapped_lines = []
    for line in details:
        wrapped_lines.extend(textwrap.wrap(line, width=24))
    body_text = "\n".join(wrapped_lines)

    ax.text(
        xy[0] + width / 2,
        body_y,
        body_text,
        ha="center",
        va="center",
        fontsize=14,
        color="#0f1f30",
        linespacing=1.35,
    )

    return box


def add_connector(ax, start_box, end_box, text=None):
    """Draw an arrow between the centers of two boxes."""
    sx = start_box.get_x() + start_box.get_width()
    sy = start_box.get_y() + start_box.get_height() / 2
    ex = end_box.get_x()
    ey = end_box.get_y() + end_box.get_height() / 2

    arrow = FancyArrowPatch(
        (sx, sy),
        (ex, ey),
        arrowstyle="-|>",
        mutation_scale=18,
        linewidth=2.0,
        color="#3a3a3a",
        shrinkA=16,
        shrinkB=16,
    )
    ax.add_patch(arrow)

    if text:
        ax.text(
            (sx + ex) / 2,
            sy + 0.02,
            text,
            ha="center",
            va="bottom",
            fontsize=13,
            color="#2f2f2f",
        )


def main():
    plt.rcParams["font.family"] = "DejaVu Sans"

    fig, ax = plt.subplots(figsize=(16, 8.5), dpi=250)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Background band to visually group the main workflow.
    ax.add_patch(
        Rectangle(
            (0.055, 0.26),
            0.89,
            0.48,
            facecolor="#f4f6fb",
            linewidth=0,
        )
    )

    palette = {
        "research": "#b3d5ff",
        "strategy": "#d5c5ff",
        "execution": "#c3efd8",
        "risk": "#ffd7b8",
        "ops": "#d9dde2",
    }

    width = 0.13
    height = 0.28
    y = 0.34
    x_positions = [0.07, 0.26, 0.45, 0.64, 0.83]

    research_box = add_box(
        ax,
        (x_positions[0], y),
        width,
        height,
        "Research",
        [
            "Macro, sentiment, and pricing data",
            "LLM agents synthesize briefing",
        ],
        palette["research"],
    )

    strategy_box = add_box(
        ax,
        (x_positions[1], y),
        width,
        height,
        "Strategy",
        [
            "Head trader forms trade plan",
            "Risk checks for target sizing",
        ],
        palette["strategy"],
    )

    execution_box = add_box(
        ax,
        (x_positions[2], y),
        width,
        height,
        "Execution",
        [
            "Paper trader stages orders",
            "Market data adapters validate",
        ],
        palette["execution"],
    )

    risk_box = add_box(
        ax,
        (x_positions[3], y),
        width,
        height,
        "Risk",
        [
            "Hard gates: spreads, limits, VaR",
            "Compliance reviews audit trail",
        ],
        palette["risk"],
    )

    ops_box = add_box(
        ax,
        (x_positions[4], y),
        width,
        height,
        "Operations",
        [
            "Settlement confirms positions",
            "Scribe archives structured log",
        ],
        palette["ops"],
    )

    add_connector(ax, research_box, strategy_box)
    add_connector(ax, strategy_box, execution_box)
    add_connector(ax, execution_box, risk_box)
    add_connector(ax, risk_box, ops_box)

    # Data inputs banner.
    ax.add_patch(
        Rectangle(
            (0.05, 0.76),
            0.9,
            0.12,
            facecolor="#eef3fe",
            linewidth=0,
        )
    )

    ax.text(
        0.5,
        0.84,
        "Context Sources",
        ha="center",
        va="bottom",
        fontsize=22,
        fontweight="bold",
        color="#1a1a1a",
    )

    context_items = [
        "Macro history RAG",
        "Curated news archive",
        "Market data adapters",
        "Quant factor library",
    ]

    for idx, item in enumerate(context_items):
        ax.text(
            0.22 + idx * 0.2,
            0.79,
            item,
            ha="center",
            va="center",
            fontsize=15,
            color="#1f3251",
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="#ffffff",
                edgecolor="#5c78a5",
                linewidth=1.2,
            ),
        )

    # Hard risk gate banner beneath execution to risk transition.
    ax.add_patch(
        Rectangle(
            (0.41, 0.2),
            0.32,
            0.1,
            facecolor="#ffe9d6",
            edgecolor="#ff9248",
            linewidth=1.5,
        )
    )

    ax.text(
        0.58,
        0.26,
        "Hard Risk Gate",
        ha="center",
        va="center",
        fontsize=19,
        fontweight="bold",
        color="#3f2100",
    )

    gate_text = "Position caps • Spread thresholds • Stress scenarios"
    ax.text(
        0.58,
        0.23,
        gate_text,
        ha="center",
        va="center",
        fontsize=15,
        color="#3f2100",
    )

    # Branch arrows from Execution box to Hard Risk Gate and back to Risk box.
    ex_center = (
        execution_box.get_x() + execution_box.get_width() / 2,
        execution_box.get_y(),
    )
    risk_center = (
        risk_box.get_x() + risk_box.get_width() / 2,
        risk_box.get_y(),
    )

    ax.add_patch(
        FancyArrowPatch(
            (ex_center[0], ex_center[1]),
            (0.58, 0.31),
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=2.0,
            color="#cc5500",
            shrinkA=14,
            shrinkB=14,
        )
    )

    ax.add_patch(
        FancyArrowPatch(
            (0.58, 0.31),
            (risk_center[0], risk_center[1]),
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=2.0,
            color="#cc5500",
            shrinkA=14,
            shrinkB=14,
        )
    )

    # Footer note summarizing deterministic logging.
    ax.text(
        0.5,
        0.08,
        "All phases emit JSON contracts → audit trail + reproducibility",
        ha="center",
        va="center",
        fontsize=15,
        color="#2b2b2b",
    )

    fig.tight_layout()
    fig.savefig(FIGURE_PATH, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
