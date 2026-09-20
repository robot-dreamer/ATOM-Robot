#!/usr/bin/env python3
"""Analyze and plot an ATOM square-trajectory experiment."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator


TARGETS = np.array(
    [
        [150.0, 150.0],
        [450.0, 150.0],
        [450.0, 450.0],
        [150.0, 450.0],
    ]
)
SIDE_NAMES = ("top", "right", "bottom", "left")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--scale", type=float, default=64.0)
    parser.add_argument("--tick-step", type=float, default=50.0)
    parser.add_argument("--max-isolated-step", type=float, default=30.0)
    return parser.parse_args()


def load_capture(path: Path, scale: float) -> tuple[np.ndarray, np.ndarray]:
    elapsed: list[float] = []
    points: list[tuple[float, float]] = []
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
                points.append((values[1] / scale, values[2] / scale))
    if len(points) < 3:
        raise ValueError("at least three valid samples are required")
    return np.asarray(elapsed), np.asarray(points)


def remove_isolated_samples(
    elapsed: np.ndarray, points: np.ndarray, threshold: float
) -> tuple[np.ndarray, np.ndarray, int]:
    if points.shape[0] < 3 or threshold <= 0:
        return elapsed, points, 0
    previous_jump = np.linalg.norm(points[1:-1] - points[:-2], axis=1)
    next_jump = np.linalg.norm(points[2:] - points[1:-1], axis=1)
    neighbor_gap = np.linalg.norm(points[2:] - points[:-2], axis=1)
    isolated = (
        (previous_jump > threshold)
        & (next_jump > threshold)
        & (neighbor_gap <= threshold)
    )
    keep = np.ones(points.shape[0], dtype=bool)
    keep[1:-1] = ~isolated
    return elapsed[keep], points[keep], int(np.count_nonzero(isolated))


def project_to_path(points: np.ndarray) -> tuple[np.ndarray, ...]:
    closed = np.vstack((TARGETS, TARGETS[0]))
    all_distances: list[np.ndarray] = []
    all_fractions: list[np.ndarray] = []
    side_lengths: list[float] = []
    for index in range(4):
        start, end = closed[index], closed[index + 1]
        segment = end - start
        length = float(np.linalg.norm(segment))
        fraction = ((points - start) @ segment) / (length * length)
        fraction = np.clip(fraction, 0.0, 1.0)
        nearest = start + fraction[:, None] * segment
        all_distances.append(np.linalg.norm(points - nearest, axis=1))
        all_fractions.append(fraction)
        side_lengths.append(length)

    distances = np.column_stack(all_distances)
    fractions = np.column_stack(all_fractions)
    side_index = np.argmin(distances, axis=1)
    row = np.arange(points.shape[0])
    path_error = distances[row, side_index]

    lengths = np.asarray(side_lengths)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths[:-1])))
    progress = cumulative[side_index] + fractions[row, side_index] * lengths[side_index]
    perimeter = float(np.sum(lengths))
    unwrapped_progress = np.unwrap(progress * 2.0 * np.pi / perimeter) * perimeter / (2.0 * np.pi)

    xmin, ymin = TARGETS[0]
    xmax, ymax = TARGETS[2]
    inward_components = np.column_stack(
        (
            points[:, 1] - ymin,
            xmax - points[:, 0],
            ymax - points[:, 1],
            points[:, 0] - xmin,
        )
    )
    inward_sign = np.sign(inward_components[row, side_index])
    signed_error = path_error * inward_sign
    return path_error, signed_error, side_index, unwrapped_progress, perimeter


def summarize(
    elapsed: np.ndarray,
    points: np.ndarray,
    path_error: np.ndarray,
    signed_error: np.ndarray,
    side_index: np.ndarray,
    progress: np.ndarray,
    perimeter: float,
    input_samples: int,
    removed_samples: int,
) -> dict[str, object]:
    duration = float(elapsed[-1] - elapsed[0])
    travel = float(progress[-1] - progress[0])
    direction = 1.0 if travel >= 0 else -1.0
    relative_progress = direction * (progress - progress[0])
    lap_index = np.floor(np.maximum(relative_progress, 0.0) / perimeter).astype(int)

    side_metrics: dict[str, object] = {}
    for index, name in enumerate(SIDE_NAMES):
        mask = side_index == index
        side_metrics[name] = {
            "samples": int(np.count_nonzero(mask)),
            "mean_inward_error_unit": float(np.mean(signed_error[mask])),
            "rmse_unit": float(np.sqrt(np.mean(path_error[mask] ** 2))),
            "mae_unit": float(np.mean(path_error[mask])),
            "p95_unit": float(np.percentile(path_error[mask], 95)),
            "max_unit": float(np.max(path_error[mask])),
        }

    per_lap: list[dict[str, object]] = []
    corner_distances: dict[str, list[float]] = {f"P{i + 1}": [] for i in range(4)}
    for index in range(int(np.max(lap_index)) + 1):
        mask = lap_index == index
        if np.count_nonzero(mask) < 20:
            continue
        coverage = float((np.max(relative_progress[mask]) - np.min(relative_progress[mask])) / perimeter)
        per_lap.append(
            {
                "lap_segment": index + 1,
                "samples": int(np.count_nonzero(mask)),
                "coverage": coverage,
                "rmse_unit": float(np.sqrt(np.mean(path_error[mask] ** 2))),
                "mae_unit": float(np.mean(path_error[mask])),
                "max_unit": float(np.max(path_error[mask])),
            }
        )
        if coverage >= 0.90:
            for target_index, target in enumerate(TARGETS):
                corner_distances[f"P{target_index + 1}"].append(
                    float(np.min(np.linalg.norm(points[mask] - target, axis=1)))
                )

    corner_metrics = {
        name: {
            "visits": len(values),
            "mean_closest_approach_unit": float(np.mean(values)),
            "max_closest_approach_unit": float(np.max(values)),
        }
        for name, values in corner_distances.items()
        if values
    }

    return {
        "samples_input": input_samples,
        "samples": int(points.shape[0]),
        "samples_removed": removed_samples,
        "duration_s": duration,
        "point_rate_hz": float((points.shape[0] - 1) / duration),
        "udp_update_rate_hz": float((np.unique(elapsed).size - 1) / duration),
        "perimeter_unit": perimeter,
        "completed_laps": abs(travel) / perimeter,
        "mean_signed_error_unit": float(np.mean(signed_error)),
        "path_rmse_unit": float(np.sqrt(np.mean(path_error**2))),
        "path_mae_unit": float(np.mean(path_error)),
        "path_p95_unit": float(np.percentile(path_error, 95)),
        "path_max_unit": float(np.max(path_error)),
        "mean_progress_speed_unit_s": abs(travel) / duration,
        "side_metrics": side_metrics,
        "per_lap_metrics": per_lap,
        "corner_metrics": corner_metrics,
    }


def save_outputs(
    source: Path,
    elapsed: np.ndarray,
    points: np.ndarray,
    path_error: np.ndarray,
    signed_error: np.ndarray,
    side_index: np.ndarray,
    metrics: dict[str, object],
) -> None:
    stem = source.with_suffix("")
    trajectory_path = stem.with_name(stem.name + "_square_trajectory.png")
    error_path = stem.with_name(stem.name + "_square_error.png")
    analyzed_path = stem.with_name(stem.name + "_square_analyzed_units.csv")
    metrics_path = stem.with_name(stem.name + "_square_metrics_units.json")

    closed = np.vstack((TARGETS, TARGETS[0]))
    figure, axis = plt.subplots(figsize=(6.2, 6.0), constrained_layout=True)
    axis.plot(closed[:, 0], closed[:, 1], "--", color="tab:orange", linewidth=2.0,
              label="reference square", zorder=2)
    axis.plot(points[:, 0], points[:, 1], color="tab:blue", linewidth=1.0,
              label="measured trajectory", zorder=3)
    axis.scatter(TARGETS[:, 0], TARGETS[:, 1], s=42, marker="D", facecolor="white",
                 edgecolor="tab:red", linewidth=1.4, label="target points", zorder=4)
    axis.set_xlabel("x (units)")
    axis.set_ylabel("y (units)")
    axis.set_aspect("equal", adjustable="box")
    axis.invert_yaxis()
    axis.xaxis.set_major_locator(MultipleLocator(50))
    axis.yaxis.set_major_locator(MultipleLocator(50))
    axis.grid(True, alpha=0.25)
    axis.legend(loc="center", framealpha=0.92)
    figure.savefig(trajectory_path, dpi=300)
    plt.close(figure)

    time = elapsed - elapsed[0]
    rmse = float(metrics["path_rmse_unit"])
    figure, axis = plt.subplots(figsize=(9.0, 4.2), constrained_layout=True)
    axis.plot(time, signed_error, color="tab:blue", linewidth=1.0)
    axis.axhline(0.0, color="black", linewidth=1.0)
    axis.axhline(rmse, color="tab:red", linestyle="--", linewidth=1.2,
                 label=f"±RMSE ({rmse:.2f} units)")
    axis.axhline(-rmse, color="tab:red", linestyle="--", linewidth=1.2)
    axis.set_xlabel("time (s)")
    axis.set_ylabel("signed path error (units)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.savefig(error_path, dpi=300)
    plt.close(figure)

    with analyzed_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(("elapsed_s", "x_unit", "y_unit", "side", "path_error_unit",
                         "signed_error_unit"))
        writer.writerows(
            zip(elapsed, points[:, 0], points[:, 1],
                (SIDE_NAMES[index] for index in side_index), path_error, signed_error,
                strict=True)
        )
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Trajectory: {trajectory_path.resolve()}")
    print(f"Error plot: {error_path.resolve()}")
    print(f"Analyzed CSV: {analyzed_path.resolve()}")
    print(f"Metrics: {metrics_path.resolve()}")


def main() -> None:
    args = parse_args()
    elapsed, points = load_capture(args.csv_path, args.scale)
    input_samples = int(points.shape[0])
    elapsed, points, removed = remove_isolated_samples(
        elapsed, points, args.max_isolated_step
    )
    path_error, signed_error, side_index, progress, perimeter = project_to_path(points)
    metrics = summarize(
        elapsed, points, path_error, signed_error, side_index, progress, perimeter,
        input_samples, removed,
    )
    save_outputs(
        args.csv_path, elapsed, points, path_error, signed_error, side_index, metrics
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
