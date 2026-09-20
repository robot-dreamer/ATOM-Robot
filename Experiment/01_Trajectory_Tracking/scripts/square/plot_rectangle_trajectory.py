#!/usr/bin/env python3
"""Plot OmniStamp motion through four rectangular target points."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parents[1]
RESULTS_DIR = EXPERIMENT_DIR / "data" / "square"
DEFAULT_TARGETS = np.array(
    [
        [150.0, 150.0],
        [450.0, 150.0],
        [450.0, 450.0],
        [150.0, 450.0],
    ]
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        help="raw capture CSV; defaults to the newest raw CSV in data/square/",
    )
    parser.add_argument("--output", type=Path, help="output PNG path")
    parser.add_argument(
        "--scale", type=float, default=64.0,
        help="divide stored x,y coordinates by this factor (default: 64)",
    )
    parser.add_argument(
        "--tick-step", type=float, default=25.0,
        help="x/y major tick spacing in Unit (default: 25)",
    )
    parser.add_argument("--show", action="store_true", help="open the plot after saving")
    args = parser.parse_args()
    if args.scale <= 0 or args.tick_step <= 0:
        parser.error("--scale and --tick-step must be positive")
    return args


def newest_raw_csv() -> Path:
    candidates = [
        path
        for path in RESULTS_DIR.glob("*.csv")
        if "_analyzed" not in path.stem
    ]
    if not candidates:
        raise FileNotFoundError(f"no raw CSV found in {RESULTS_DIR}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_xy(path: Path, scale: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    elapsed: list[float] = []
    x: list[float] = []
    y: list[float] = []
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"elapsed_s", "x", "y"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV must contain elapsed_s, x, and y columns")
        for row in reader:
            try:
                values = float(row["elapsed_s"]), float(row["x"]), float(row["y"])
            except (TypeError, ValueError):
                continue
            if np.all(np.isfinite(values)):
                elapsed.append(values[0])
                x.append(values[1] / scale)
                y.append(values[2] / scale)
    if len(x) < 2:
        raise ValueError("at least two valid samples are required")
    return np.asarray(elapsed), np.asarray(x), np.asarray(y)


def point_to_segment_distance(
    points: np.ndarray, start: np.ndarray, end: np.ndarray
) -> np.ndarray:
    segment = end - start
    denominator = float(segment @ segment)
    projection = ((points - start) @ segment) / denominator
    projection = np.clip(projection, 0.0, 1.0)
    nearest = start + projection[:, None] * segment
    return np.linalg.norm(points - nearest, axis=1)


def rectangle_path_error(points: np.ndarray, targets: np.ndarray) -> np.ndarray:
    closed = np.vstack((targets, targets[0]))
    distances = [
        point_to_segment_distance(points, closed[index], closed[index + 1])
        for index in range(len(targets))
    ]
    return np.min(np.column_stack(distances), axis=1)


def plot_trajectory(
    csv_path: Path,
    output_path: Path,
    scale: float = 64.0,
    tick_step: float = 25.0,
    show: bool = False,
) -> None:
    elapsed, x, y = load_xy(csv_path, scale)
    points = np.column_stack((x, y))
    errors = rectangle_path_error(points, DEFAULT_TARGETS)
    rmse = float(np.sqrt(np.mean(errors**2)))
    mae = float(np.mean(errors))

    figure, axis = plt.subplots(figsize=(10, 6.5), constrained_layout=True)
    axis.plot(
        x,
        y,
        color="tab:blue",
        linewidth=1.35,
        alpha=0.9,
        label="measured trajectory",
        zorder=3,
    )

    closed_targets = np.vstack((DEFAULT_TARGETS, DEFAULT_TARGETS[0]))
    axis.plot(
        closed_targets[:, 0],
        closed_targets[:, 1],
        "--",
        color="black",
        linewidth=2.0,
        label="target rectangle",
        zorder=2,
    )
    axis.scatter(
        DEFAULT_TARGETS[:, 0],
        DEFAULT_TARGETS[:, 1],
        s=90,
        marker="D",
        facecolor="white",
        edgecolor="tab:red",
        linewidth=2,
        label="target points",
        zorder=4,
    )
    for index, (target_x, target_y) in enumerate(DEFAULT_TARGETS, start=1):
        is_right_side = target_x > float(np.mean(DEFAULT_TARGETS[:, 0]))
        axis.annotate(
            f"P{index} ({target_x:.0f}, {target_y:.0f})",
            (target_x, target_y),
            xytext=(-7 if is_right_side else 7, -13 if target_y < 100 else 12),
            textcoords="offset points",
            fontsize=9,
            horizontalalignment="right" if is_right_side else "left",
        )

    axis.scatter(x[0], y[0], s=75, color="limegreen", label="start", zorder=5)
    axis.scatter(x[-1], y[-1], s=80, color="red", marker="x", linewidth=2, label="end", zorder=5)

    margin = 15.0
    axis.set_xlim(min(x.min(), DEFAULT_TARGETS[:, 0].min()) - margin,
                  max(x.max(), DEFAULT_TARGETS[:, 0].max()) + margin)
    axis.set_ylim(min(y.min(), DEFAULT_TARGETS[:, 1].min()) - margin,
                  max(y.max(), DEFAULT_TARGETS[:, 1].max()) + margin)
    axis.invert_yaxis()
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x (Unit)")
    axis.set_ylabel("y (Unit)")
    axis.xaxis.set_major_locator(MultipleLocator(tick_step))
    axis.yaxis.set_major_locator(MultipleLocator(tick_step))
    axis.set_title(
        f"Rectangular trajectory (RMSE={rmse:.2f} Unit, MAE={mae:.2f} Unit)"
    )
    axis.grid(True, alpha=0.25)
    axis.legend(loc="center", framealpha=0.9)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=200)
    print(f"Source: {csv_path.resolve()}")
    print(f"Saved:  {output_path.resolve()}")
    print(f"Path RMSE: {rmse:.3f} Unit")
    print(f"Path MAE:  {mae:.3f} Unit")

    if show:
        plt.show()
    else:
        plt.close(figure)


if __name__ == "__main__":
    args = parse_args()
    source = args.csv_path or newest_raw_csv()
    destination = args.output or RESULTS_DIR / "rectangle_trajectory.png"
    plot_trajectory(
        source,
        destination,
        scale=args.scale,
        tick_step=args.tick_step,
        show=args.show,
    )
