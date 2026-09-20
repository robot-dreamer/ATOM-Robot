#!/usr/bin/env python3
"""Plot an OmniStamp circular trajectory from an existing analyzed CSV.

The UDP coordinates stored in the CSV are fixed-point values scaled by 64.
This script converts them back to map units before calculating errors.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parents[1]
DEFAULT_INPUT = (
    EXPERIMENT_DIR
    / "data"
    / "circle"
    / "omnistamp_circle_20260914_192932.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot a circular trajectory in map units.")
    parser.add_argument("csv", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--center-x", type=float, default=300.0)
    parser.add_argument("--center-y", type=float, default=300.0)
    parser.add_argument(
        "--display-center-x",
        type=float,
        default=None,
        help="translate plotted coordinates so the circle center has this x value",
    )
    parser.add_argument(
        "--display-center-y",
        type=float,
        default=None,
        help="translate plotted coordinates so the circle center has this y value",
    )
    parser.add_argument("--radius", type=float, default=150.0)
    parser.add_argument("--scale", type=float, default=64.0)
    parser.add_argument("--tick-step", type=float, default=25.0)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--max-abs-radial-error",
        type=float,
        default=None,
        help="exclude isolated samples whose absolute radial error exceeds this value",
    )
    parser.add_argument(
        "--max-isolated-step",
        type=float,
        default=None,
        help="exclude a sample when both adjacent jumps exceed this value but its neighbors remain close",
    )
    parser.add_argument(
        "--publication",
        action="store_true",
        help="use a compact layout with larger relative text for paper figures",
    )
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()
    if args.scale <= 0 or args.tick_step <= 0:
        parser.error("--scale and --tick-step must be positive")
    if args.radius is not None and args.radius <= 0:
        parser.error("--radius must be positive")
    if args.max_abs_radial_error is not None and args.max_abs_radial_error <= 0:
        parser.error("--max-abs-radial-error must be positive")
    if args.max_isolated_step is not None and args.max_isolated_step <= 0:
        parser.error("--max-isolated-step must be positive")
    if (args.display_center_x is None) != (args.display_center_y is None):
        parser.error("--display-center-x and --display-center-y must be used together")
    return args


def load_xy(path: Path, scale: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    elapsed: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"elapsed_s", "x", "y"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV must contain elapsed_s, x, and y columns")
        for row in reader:
            try:
                t = float(row["elapsed_s"])
                x = float(row["x"]) / scale
                y = float(row["y"]) / scale
            except (TypeError, ValueError):
                continue
            if math.isfinite(t) and math.isfinite(x) and math.isfinite(y):
                elapsed.append(t)
                xs.append(x)
                ys.append(y)
    if len(xs) < 3:
        raise ValueError("at least three valid samples are required")
    return np.asarray(elapsed), np.asarray(xs), np.asarray(ys)


def output_stem(path: Path) -> str:
    return path.stem.removesuffix("_analyzed")


def main() -> int:
    args = parse_args()
    source = args.csv.resolve()
    elapsed, x, y = load_xy(source, args.scale)

    distance = np.hypot(x - args.center_x, y - args.center_y)
    radius = float(args.radius) if args.radius is not None else float(np.mean(distance))
    radial_error = distance - radius
    input_samples = int(x.size)
    if args.max_abs_radial_error is not None:
        keep = np.abs(radial_error) <= args.max_abs_radial_error
        elapsed = elapsed[keep]
        x = x[keep]
        y = y[keep]
        distance = distance[keep]
        radial_error = radial_error[keep]
    if args.max_isolated_step is not None and x.size >= 3:
        points = np.column_stack((x, y))
        jump_from_previous = np.linalg.norm(points[1:-1] - points[:-2], axis=1)
        jump_to_next = np.linalg.norm(points[2:] - points[1:-1], axis=1)
        neighbor_gap = np.linalg.norm(points[2:] - points[:-2], axis=1)
        isolated = (
            (jump_from_previous > args.max_isolated_step)
            & (jump_to_next > args.max_isolated_step)
            & (neighbor_gap <= args.max_isolated_step)
        )
        keep = np.ones(x.size, dtype=bool)
        keep[1:-1] = ~isolated
        elapsed = elapsed[keep]
        x = x[keep]
        y = y[keep]
        distance = distance[keep]
        radial_error = radial_error[keep]
    removed_samples = input_samples - int(x.size)
    if x.size < 3:
        raise ValueError("fewer than three samples remain after outlier filtering")
    rmse = float(np.sqrt(np.mean(radial_error**2)))
    mae = float(np.mean(np.abs(radial_error)))
    max_error = float(np.max(np.abs(radial_error)))

    base = output_stem(source)
    output_dir = source.parent
    trajectory_path = (
        args.output.resolve()
        if args.output is not None
        else output_dir / f"{base}_trajectory.png"
    )
    error_path = output_dir / f"{base}_radial_error.png"
    units_csv_path = output_dir / f"{base}_analyzed_units.csv"
    metrics_path = output_dir / f"{base}_metrics_units.json"

    with units_csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["elapsed_s", "x_unit", "y_unit", "radius_unit", "radial_error_unit"]
        )
        writer.writerows(zip(elapsed, x, y, distance, radial_error, strict=True))

    metrics = {
        "source_csv": str(source),
        "coordinate_scale": args.scale,
        "unit": "Unit",
        "samples_input": input_samples,
        "samples": int(x.size),
        "samples_removed": removed_samples,
        "max_abs_radial_error_filter": args.max_abs_radial_error,
        "max_isolated_step_filter": args.max_isolated_step,
        "center_x": args.center_x,
        "center_y": args.center_y,
        "reference_radius": radius,
        "radial_rmse": rmse,
        "radial_mae": mae,
        "radial_max_abs_error": max_error,
    }
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    display_center_x = (
        args.center_x if args.display_center_x is None else args.display_center_x
    )
    display_center_y = (
        args.center_y if args.display_center_y is None else args.display_center_y
    )
    plot_x = x + display_center_x - args.center_x
    plot_y = y + display_center_y - args.center_y

    theta = np.linspace(0.0, 2.0 * np.pi, 720)
    reference_x = display_center_x + radius * np.cos(theta)
    reference_y = display_center_y + radius * np.sin(theta)

    figure_size = (4.2, 4.2) if args.publication else (7.2, 7.2)
    fig, ax = plt.subplots(figsize=figure_size, constrained_layout=True)
    ax.plot(reference_x, reference_y, "--", color="tab:orange", linewidth=2.0,
            label=f"Reference circle (R={radius:.2f} units)")
    ax.plot(plot_x, plot_y, color="tab:blue", linewidth=1.3, label="Measured trajectory")
    if not args.publication:
        ax.scatter(plot_x[0], plot_y[0], s=45, color="tab:green", label="Start", zorder=3)
        ax.scatter(plot_x[-1], plot_y[-1], s=55, color="tab:red", marker="x", label="End", zorder=3)
        ax.scatter(display_center_x, display_center_y, s=55, color="black", marker="+",
                   label="Center", zorder=3)
    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel("x (units)", fontsize=11 if args.publication else None)
    ax.set_ylabel("y (units)", fontsize=11 if args.publication else None)
    ax.xaxis.set_major_locator(MultipleLocator(args.tick_step))
    ax.yaxis.set_major_locator(MultipleLocator(args.tick_step))
    if not args.publication:
        ax.set_title(f"Circular trajectory (RMSE={rmse:.2f} Unit, MAE={mae:.2f} Unit)")
    else:
        ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9 if args.publication else None)
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        trajectory_path,
        dpi=max(args.dpi, 450) if args.publication else args.dpi,
        bbox_inches="tight" if args.publication else None,
        pad_inches=0.03 if args.publication else 0.1,
    )

    fig_error, ax_error = plt.subplots(figsize=(9.0, 4.2), constrained_layout=True)
    ax_error.plot(elapsed - elapsed[0], radial_error, color="tab:blue", linewidth=1.0)
    ax_error.axhline(0.0, color="black", linewidth=1.0)
    ax_error.axhline(rmse, color="tab:red", linestyle="--", alpha=0.7)
    ax_error.axhline(-rmse, color="tab:red", linestyle="--", alpha=0.7,
                     label=f"±RMSE ({rmse:.2f} Unit)")
    ax_error.set_xlabel("Time (s)")
    ax_error.set_ylabel("Radial error (units)")
    ax_error.set_title("Radial tracking error")
    ax_error.grid(True, alpha=0.3)
    ax_error.legend()
    fig_error.savefig(error_path, dpi=args.dpi)

    print(f"Samples: {x.size} / {input_samples} (removed: {removed_samples})")
    print(f"Center: ({args.center_x:.2f}, {args.center_y:.2f}) units")
    print(f"Reference radius: {radius:.4f} units")
    print(f"Radial RMSE: {rmse:.4f} units")
    print(f"Radial MAE: {mae:.4f} units")
    print(f"Maximum absolute radial error: {max_error:.4f} units")
    print(f"Trajectory: {trajectory_path}")
    print(f"Error plot: {error_path}")
    print(f"Corrected CSV: {units_csv_path}")
    print(f"Metrics: {metrics_path}")

    if args.show:
        plt.show()
    else:
        plt.close("all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
