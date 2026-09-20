from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle


LAYOUTS = [
    (
        "(a) Pentagram crossing",
        [
            ((300, 120), (405, 445)),
            ((470, 245), (195, 445)),
            ((405, 445), (130, 245)),
            ((195, 445), (300, 120)),
            ((130, 245), (470, 245)),
        ],
    ),
    (
        "(b) Central crossing",
        [
            ((120, 300), (480, 300)),
            ((480, 300), (120, 300)),
            ((300, 120), (300, 480)),
            ((300, 480), (300, 120)),
            ((180, 180), (420, 420)),
        ],
    ),
    (
        "(c) Multi-path convergence",
        [
            ((140, 160), (460, 440)),
            ((140, 230), (460, 370)),
            ((140, 300), (460, 300)),
            ((140, 370), (460, 230)),
            ((140, 440), (460, 160)),
        ],
    ),
]

COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
ROBOT_RADIUS = 23
GOAL_SIZE = 46


def shorten_segment(start, goal, start_offset=27, goal_offset=30):
    sx, sy = start
    gx, gy = goal
    dx, dy = gx - sx, gy - sy
    length = (dx * dx + dy * dy) ** 0.5
    return (
        (sx + start_offset * dx / length, sy + start_offset * dy / length),
        (gx - goal_offset * dx / length, gy - goal_offset * dy / length),
    )


def draw_layout(ax, title, routes):
    ax.set_xlim(0, 600)
    ax.set_ylim(600, 0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([0, 200, 400, 600])
    ax.set_yticks([0, 200, 400, 600])
    ax.set_xticks(range(0, 601, 100), minor=True)
    ax.set_yticks(range(0, 601, 100), minor=True)
    ax.grid(which="major", color="#b8b8b8", linewidth=0.45, alpha=0.65)
    ax.grid(which="minor", color="#d8d8d8", linewidth=0.35, alpha=0.55)
    ax.tick_params(axis="both", which="major", labelsize=7, length=2.5, pad=2)
    ax.tick_params(axis="both", which="minor", length=0)
    ax.set_title(title, fontsize=8, pad=4)
    ax.set_xlabel("x (units)", fontsize=7.5, labelpad=2)

    for robot_id, (start, goal) in enumerate(routes, start=1):
        path_start, path_end = shorten_segment(start, goal)
        arrow = FancyArrowPatch(
            path_start,
            path_end,
            arrowstyle="-|>",
            mutation_scale=7,
            linewidth=0.9,
            linestyle=(0, (3, 2)),
            color="#707070",
            alpha=0.72,
            zorder=1,
        )
        ax.add_patch(arrow)

    for robot_id, (start, goal) in enumerate(routes, start=1):
        color = COLORS[robot_id - 1]
        gx, gy = goal
        goal_marker = Rectangle(
            (gx - GOAL_SIZE / 2, gy - GOAL_SIZE / 2),
            GOAL_SIZE,
            GOAL_SIZE,
            facecolor="none",
            edgecolor=color,
            linewidth=1.5,
            zorder=2,
        )
        ax.add_patch(goal_marker)

    for robot_id, (start, goal) in enumerate(routes, start=1):
        color = COLORS[robot_id - 1]
        sx, sy = start
        robot = Circle(
            (sx, sy),
            ROBOT_RADIUS,
            facecolor=color,
            edgecolor="white",
            linewidth=0.9,
            zorder=3,
        )
        ax.add_patch(robot)
        ax.text(
            sx,
            sy,
            str(robot_id),
            ha="center",
            va="center",
            color="white",
            fontsize=7,
            fontweight="bold",
            zorder=4,
        )

    for spine in ax.spines.values():
        spine.set_linewidth(0.7)


def draw_compact_layout(ax, panel_label, routes):
    """Draw a stripped-down panel sized for one IEEE column."""
    ax.set_xlim(0, 600)
    ax.set_ylim(600, 0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(range(0, 601, 100))
    ax.set_yticks(range(0, 601, 100))
    ax.grid(color="#d7d7d7", linewidth=0.32, alpha=0.75)
    ax.tick_params(axis="both", which="both", length=0, labelbottom=False,
                   labelleft=False)
    ax.set_title(panel_label, fontsize=7, pad=1.5)

    for start, goal in routes:
        path_start, path_end = shorten_segment(start, goal, 34, 37)
        ax.add_patch(
            FancyArrowPatch(
                path_start,
                path_end,
                arrowstyle="-|>",
                mutation_scale=5.5,
                linewidth=0.55,
                linestyle=(0, (2.5, 1.8)),
                color="#686868",
                alpha=0.75,
                zorder=1,
            )
        )

    for robot_id, (start, goal) in enumerate(routes, start=1):
        color = COLORS[robot_id - 1]
        gx, gy = goal
        marker_size = 58
        ax.add_patch(
            Rectangle(
                (gx - marker_size / 2, gy - marker_size / 2),
                marker_size,
                marker_size,
                facecolor="none",
                edgecolor=color,
                linewidth=1.0,
                zorder=2,
            )
        )

    for robot_id, (start, goal) in enumerate(routes, start=1):
        color = COLORS[robot_id - 1]
        sx, sy = start
        ax.add_patch(
            Circle(
                (sx, sy),
                29,
                facecolor=color,
                edgecolor="white",
                linewidth=0.55,
                zorder=3,
            )
        )
        ax.text(
            sx,
            sy,
            str(robot_id),
            ha="center",
            va="center",
            color="white",
            fontsize=5.2,
            fontweight="bold",
            zorder=4,
        )

    for spine in ax.spines.values():
        spine.set_color("#8a8a8a")
        spine.set_linewidth(0.5)


def main():
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.55), sharex=True, sharey=True)
    for ax, (title, routes) in zip(axes, LAYOUTS):
        draw_layout(ax, title, routes)
    axes[0].set_ylabel("y (units, downward)", fontsize=7.5, labelpad=2)

    start_handle = plt.Line2D(
        [], [], marker="o", linestyle="none", markersize=6,
        markerfacecolor=COLORS[0], markeredgecolor="white",
        label="Initial robot position"
    )
    goal_handle = plt.Line2D(
        [], [], marker="s", linestyle="none", markersize=6,
        markerfacecolor="none", markeredgecolor=COLORS[0],
        label="Goal position"
    )
    path_handle = plt.Line2D(
        [], [], color="#707070", linewidth=0.9, linestyle=(0, (3, 2)),
        label="Direct start--goal path"
    )
    fig.legend(
        handles=[start_handle, goal_handle, path_handle],
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=7,
        bbox_to_anchor=(0.5, 0.005),
        handlelength=2.6,
        columnspacing=1.4,
    )
    fig.subplots_adjust(left=0.065, right=0.995, top=0.92, bottom=0.20, wspace=0.16)

    output_dir = Path(__file__).resolve().parent.parent / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / "distributed_avoidance_layouts"
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.02)
    fig.savefig(base.with_suffix(".png"), dpi=600, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    compact_fig, compact_axes = plt.subplots(
        1, 3, figsize=(3.45, 1.22), sharex=True, sharey=True
    )
    for ax, panel_label, (_, routes) in zip(
        compact_axes, ["(a)", "(b)", "(c)"], LAYOUTS
    ):
        draw_compact_layout(ax, panel_label, routes)
    compact_fig.subplots_adjust(
        left=0.005, right=0.995, top=0.84, bottom=0.01, wspace=0.07
    )
    compact_base = output_dir / "distributed_avoidance_layouts_single"
    compact_fig.savefig(
        compact_base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.01
    )
    compact_fig.savefig(
        compact_base.with_suffix(".png"), dpi=600,
        bbox_inches="tight", pad_inches=0.01
    )
    plt.close(compact_fig)


if __name__ == "__main__":
    main()
