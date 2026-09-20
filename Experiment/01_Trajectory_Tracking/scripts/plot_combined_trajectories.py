#!/usr/bin/env python3
"""Create a compact single-column figure for circular and rectangular tracking."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
CIRCLE_CSV = (
    EXPERIMENT_DIR
    / "data"
    / "circle"
    / "omnistamp_circle_20260914_192932_analyzed_units.csv"
)
RECTANGLE_RESULTS = EXPERIMENT_DIR / "data" / "square"
RECTANGLE_CSV = (
    RECTANGLE_RESULTS
    / "omnistamp_circle_20260914_193513_square_analyzed_units.csv"
)
OUTPUT = EXPERIMENT_DIR / "figures" / "trajectory_tracking_combined.png"

RECTANGLE_TARGETS = np.array(
    [[150.0, 150.0], [450.0, 150.0], [450.0, 450.0], [150.0, 450.0]]
)


def load_circle(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        rows = list(csv.DictReader(csv_file))
    return (
        np.asarray([float(row["x_unit"]) for row in rows]),
        np.asarray([float(row["y_unit"]) for row in rows]),
    )


def load_rectangle(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        rows = list(csv.DictReader(csv_file))
    elapsed = np.asarray([float(row["elapsed_s"]) for row in rows])
    x_key = "x_unit" if "x_unit" in rows[0] else "x"
    y_key = "y_unit" if "y_unit" in rows[0] else "y"
    raw_x = np.asarray([float(row[x_key]) for row in rows])
    raw_y = np.asarray([float(row[y_key]) for row in rows])
    scale = 64.0 if np.median(np.hypot(raw_x, raw_y)) > 1000.0 else 1.0
    return elapsed, raw_x / scale, raw_y / scale


def point_to_segment_distance(
    points: np.ndarray, start: np.ndarray, end: np.ndarray
) -> np.ndarray:
    segment = end - start
    projection = ((points - start) @ segment) / (segment @ segment)
    projection = np.clip(projection, 0.0, 1.0)
    nearest = start + projection[:, None] * segment
    return np.linalg.norm(points - nearest, axis=1)


def rectangle_error(points: np.ndarray) -> np.ndarray:
    closed = np.vstack((RECTANGLE_TARGETS, RECTANGLE_TARGETS[0]))
    distances = [
        point_to_segment_distance(points, closed[index], closed[index + 1])
        for index in range(4)
    ]
    return np.min(np.column_stack(distances), axis=1)


def format_axis(axis: plt.Axes) -> None:
    axis.set_aspect("equal", adjustable="box")
    axis.invert_yaxis()
    axis.grid(True, color="#b0b0b0", linewidth=0.45, alpha=0.38)
    axis.tick_params(axis="both", labelsize=6, width=0.6, length=2.2, pad=1.5)
    axis.set_xlabel("x (units)", fontsize=7, labelpad=1.5)
    for spine in axis.spines.values():
        spine.set_linewidth(0.65)


def main() -> int:
    circle_x, circle_y = load_circle(CIRCLE_CSV)
    elapsed, rectangle_x, rectangle_y = load_rectangle(RECTANGLE_CSV)

    figure = plt.figure(figsize=(3.45, 1.72))
    # Use identical plot areas and coordinate limits so that the two
    # trajectories can be compared at the same physical scale.
    grid = figure.add_gridspec(1, 2, width_ratios=(1.0, 1.0), wspace=0.18)
    circle_axis = figure.add_subplot(grid[0, 0])
    rectangle_axis = figure.add_subplot(grid[0, 1], sharey=circle_axis)

    theta = np.linspace(0.0, 2.0 * np.pi, 720)
    circle_axis.plot(
        300.0 + 150.0 * np.cos(theta),
        300.0 + 150.0 * np.sin(theta),
        "--",
        color="tab:orange",
        linewidth=1.25,
        label="Reference",
    )
    circle_axis.plot(
        circle_x,
        circle_y,
        color="tab:blue",
        linewidth=0.45,
        label="Measured",
    )
    circle_axis.set_xlim(125.0, 475.0)
    circle_axis.set_ylim(125.0, 475.0)
    circle_axis.set_xticks([150, 300, 450])
    circle_axis.set_yticks([150, 300, 450])
    circle_axis.set_ylabel("y (units)", fontsize=7, labelpad=1.5)
    circle_axis.set_title("(a) Circular", fontsize=7, pad=2.0)
    format_axis(circle_axis)

    closed_targets = np.vstack((RECTANGLE_TARGETS, RECTANGLE_TARGETS[0]))
    rectangle_axis.plot(
        closed_targets[:, 0],
        closed_targets[:, 1],
        "--",
        color="tab:orange",
        linewidth=1.25,
    )
    rectangle_axis.plot(
        rectangle_x,
        rectangle_y,
        color="tab:blue",
        linewidth=0.45,
    )
    rectangle_axis.set_xlim(125.0, 475.0)
    rectangle_axis.set_ylim(125.0, 475.0)
    rectangle_axis.set_xticks([150, 300, 450])
    rectangle_axis.tick_params(axis="y", labelleft=False)
    rectangle_axis.set_title("(b) Square", fontsize=7, pad=2.0)
    format_axis(rectangle_axis)

    handles, labels = circle_axis.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.005),
        ncol=2,
        frameon=False,
        fontsize=6.5,
        handlelength=2.4,
        columnspacing=1.3,
    )
    figure.subplots_adjust(left=0.105, right=0.995, top=0.91, bottom=0.23)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT, dpi=600, bbox_inches="tight", pad_inches=0.015)
    plt.close(figure)

    errors = rectangle_error(np.column_stack((rectangle_x, rectangle_y)))
    print(f"Representative rectangle samples: {rectangle_x.size}")
    print(f"Representative rectangle duration: {elapsed[-1] - elapsed[0]:.3f} s")
    print(f"Representative rectangle RMSE: {np.sqrt(np.mean(errors**2)):.4f} Unit")
    print(f"Representative rectangle MAE: {np.mean(errors):.4f} Unit")
    print(f"Representative rectangle maximum error: {np.max(errors):.4f} Unit")
    print(f"Saved: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
