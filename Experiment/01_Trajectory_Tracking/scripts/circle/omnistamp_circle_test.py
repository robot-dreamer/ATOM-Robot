#!/usr/bin/env python3
"""Receive OmniStamp UDP positions, save them, and analyze circular tracking.

Expected UDP payload::

    x,y

Each datagram may contain one sample or multiple newline-separated samples.
Press Ctrl+C to stop capture and generate the analysis figures.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator


DEFAULT_SOURCE_IP = "192.168.3.82"
DEFAULT_PORT = 5000
DEFAULT_COORDINATE_SCALE = 64.0
SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parents[1]
DEFAULT_OUTPUT_DIR = EXPERIMENT_DIR / "data" / "circle"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture x,y UDP data and measure OmniStamp circular-path error."
    )
    parser.add_argument(
        "--analyze",
        type=Path,
        metavar="CSV",
        help="analyze an existing capture instead of listening for UDP data",
    )
    parser.add_argument("--bind-ip", default="0.0.0.0", help="local interface to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="local UDP port")
    parser.add_argument(
        "--source-ip",
        default=DEFAULT_SOURCE_IP,
        help="accepted sender IP; use 'any' to disable filtering",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="output folder"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="capture duration in seconds; 0 means run until Ctrl+C",
    )
    parser.add_argument(
        "--center-x", type=float, default=300.0, help="target-circle center x coordinate"
    )
    parser.add_argument(
        "--center-y", type=float, default=300.0, help="target-circle center y coordinate"
    )
    parser.add_argument(
        "--radius", type=float, default=150.0, help="target-circle radius (default: 150 units)"
    )
    parser.add_argument(
        "--skip-seconds",
        type=float,
        default=0.0,
        help="exclude initial seconds (for approach/transient motion) from analysis",
    )
    parser.add_argument(
        "--skip-samples",
        type=int,
        default=0,
        help="exclude additional initial samples from analysis",
    )
    parser.add_argument(
        "--coordinate-scale",
        type=float,
        default=DEFAULT_COORDINATE_SCALE,
        help="divide received x,y values by this factor (default: 64)",
    )
    parser.add_argument(
        "--unit", default="Unit", help="coordinate unit used in labels and metrics"
    )
    parser.add_argument(
        "--no-show", action="store_true", help="save figures without opening plot windows"
    )
    args = parser.parse_args()

    if (args.center_x is None) != (args.center_y is None):
        parser.error("--center-x and --center-y must be supplied together")
    if args.radius is not None and args.center_x is None:
        parser.error("--radius requires --center-x and --center-y")
    if args.radius is not None and args.radius <= 0:
        parser.error("--radius must be positive")
    if args.duration < 0 or args.skip_seconds < 0 or args.skip_samples < 0:
        parser.error("duration and skip values cannot be negative")
    if args.coordinate_scale <= 0:
        parser.error("--coordinate-scale must be positive")
    return args


def parse_payload(payload: bytes) -> list[tuple[float, float]]:
    """Parse one or more newline-separated x,y samples from a datagram."""
    text = payload.decode("utf-8").strip()
    if not text:
        return []

    samples: list[tuple[float, float]] = []
    for line in text.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 2:
            raise ValueError(f"expected x,y but received {line!r}")
        x, y = map(float, fields)
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"coordinates must be finite: {line!r}")
        samples.append((x, y))
    return samples


def make_capture_path(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"omnistamp_circle_{stamp}.csv"


def capture_udp(args: argparse.Namespace) -> Path:
    output_path = make_capture_path(args.output_dir)
    accepted_ip = None if args.source_ip.lower() == "any" else args.source_ip
    sample_count = 0
    invalid_count = 0
    ignored_count = 0
    start_monotonic = time.monotonic()
    last_report = start_monotonic
    last_flush = start_monotonic

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.bind_ip, args.port))
    sock.settimeout(0.2)

    print(f"Listening on {args.bind_ip}:{args.port}")
    print(f"Accepting source: {accepted_ip or 'any IP'}")
    print(f"Saving raw samples to: {output_path.resolve()}")
    print("Press Ctrl+C to stop and analyze.\n")

    try:
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                ["timestamp_iso", "elapsed_s", "x", "y", "source_ip", "source_port"]
            )

            while True:
                now = time.monotonic()
                if args.duration and now - start_monotonic >= args.duration:
                    break

                try:
                    payload, address = sock.recvfrom(65535)
                except socket.timeout:
                    continue

                if accepted_ip is not None and address[0] != accepted_ip:
                    ignored_count += 1
                    continue

                receive_monotonic = time.monotonic()
                receive_iso = datetime.now().astimezone().isoformat(timespec="milliseconds")
                try:
                    samples = parse_payload(payload)
                except (UnicodeDecodeError, ValueError) as exc:
                    invalid_count += 1
                    print(f"Warning: ignored invalid packet from {address}: {exc}")
                    continue

                for x, y in samples:
                    elapsed = receive_monotonic - start_monotonic
                    writer.writerow(
                        [receive_iso, f"{elapsed:.9f}", f"{x:.9f}", f"{y:.9f}", *address]
                    )
                    sample_count += 1

                if receive_monotonic - last_flush >= 1.0:
                    csv_file.flush()
                    last_flush = receive_monotonic

                if receive_monotonic - last_report >= 1.0:
                    elapsed_total = receive_monotonic - start_monotonic
                    average_hz = sample_count / elapsed_total if elapsed_total else 0.0
                    print(
                        f"\rSamples: {sample_count:6d} | average: {average_hz:6.1f} Hz "
                        f"| latest: ({x:.3f}, {y:.3f})",
                        end="",
                        flush=True,
                    )
                    last_report = receive_monotonic
    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
    finally:
        sock.close()

    elapsed_total = time.monotonic() - start_monotonic
    print(
        f"Captured {sample_count} samples in {elapsed_total:.2f} s "
        f"({sample_count / elapsed_total if elapsed_total else 0.0:.2f} Hz average)."
    )
    if invalid_count or ignored_count:
        print(f"Invalid packets: {invalid_count}; packets from other IPs: {ignored_count}")
    return output_path


def load_capture(
    path: Path, coordinate_scale: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    elapsed: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"elapsed_s", "x", "y"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
        for row in reader:
            try:
                t, x, y = float(row["elapsed_s"]), float(row["x"]), float(row["y"])
            except (TypeError, ValueError):
                continue
            if math.isfinite(t) and math.isfinite(x) and math.isfinite(y):
                elapsed.append(t)
                xs.append(x / coordinate_scale)
                ys.append(y / coordinate_scale)
    return np.asarray(elapsed), np.asarray(xs), np.asarray(ys)


def fit_circle(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Algebraic least-squares circle fit."""
    matrix = np.column_stack((2.0 * x, 2.0 * y, np.ones_like(x)))
    rhs = x * x + y * y
    solution, _, rank, _ = np.linalg.lstsq(matrix, rhs, rcond=None)
    if rank < 3:
        raise ValueError("samples do not span enough of a 2-D circle for fitting")
    center_x, center_y, constant = solution
    radius_squared = constant + center_x * center_x + center_y * center_y
    if radius_squared <= 0:
        raise ValueError("circle fit produced a non-positive radius")
    return float(center_x), float(center_y), float(math.sqrt(radius_squared))


def estimated_sample_rates(elapsed: np.ndarray) -> tuple[float, float]:
    if elapsed.size < 2:
        return float("nan"), float("nan")
    duration = float(elapsed[-1] - elapsed[0])
    point_rate = float((elapsed.size - 1) / duration) if duration > 0 else float("nan")

    # All samples carried in one UDP datagram share the same timestamp. The
    # unique timestamps therefore estimate the datagram/update frequency.
    unique_times = np.unique(elapsed)
    intervals = np.diff(unique_times)
    update_rate = float(1.0 / np.mean(intervals)) if intervals.size else float("nan")
    return point_rate, update_rate


def analyze_capture(path: Path, args: argparse.Namespace) -> dict[str, object]:
    elapsed_all, x_all, y_all = load_capture(path, args.coordinate_scale)
    if elapsed_all.size < 3:
        raise ValueError(f"only {elapsed_all.size} valid samples; at least 3 are required")

    mask = elapsed_all >= args.skip_seconds
    eligible_indices = np.flatnonzero(mask)
    if args.skip_samples:
        eligible_indices = eligible_indices[args.skip_samples :]
    elapsed = elapsed_all[eligible_indices]
    x = x_all[eligible_indices]
    y = y_all[eligible_indices]
    if elapsed.size < 3:
        raise ValueError("fewer than 3 samples remain after applying skip options")

    using_known_radius = args.radius is not None
    using_fixed_center = args.center_x is not None
    if using_known_radius:
        center_x, center_y, radius = args.center_x, args.center_y, args.radius
        reference_name = "target"
        reference_description = "known target circle"
    elif using_fixed_center:
        center_x, center_y = args.center_x, args.center_y
        radius = float(np.mean(np.hypot(x - center_x, y - center_y)))
        reference_name = "fixed-center fitted"
        reference_description = "fixed target center with fitted radius"
    else:
        center_x, center_y, radius = fit_circle(x, y)
        reference_name = "fitted"
        reference_description = "least-squares fitted circle"

    distance = np.hypot(x - center_x, y - center_y)
    radial_error = distance - radius
    abs_error = np.abs(radial_error)
    point_rate_hz, update_rate_hz = estimated_sample_rates(elapsed)
    angles = np.unwrap(np.arctan2(y - center_y, x - center_x))
    angular_travel_deg = float(np.degrees(np.max(angles) - np.min(angles)))

    metrics: dict[str, object] = {
        "source_csv": str(path.resolve()),
        "reference": reference_description,
        "unit": args.unit,
        "samples_total": int(elapsed_all.size),
        "samples_analyzed": int(elapsed.size),
        "analysis_start_s": float(elapsed[0]),
        "analysis_end_s": float(elapsed[-1]),
        "point_rate_hz": point_rate_hz,
        "udp_update_rate_hz": update_rate_hz,
        "center_x": float(center_x),
        "center_y": float(center_y),
        "radius": float(radius),
        "mean_signed_radial_error": float(np.mean(radial_error)),
        "radial_mae": float(np.mean(abs_error)),
        "radial_rmse": float(np.sqrt(np.mean(radial_error**2))),
        "radial_error_std": float(np.std(radial_error)),
        "radial_error_p95_abs": float(np.percentile(abs_error, 95)),
        "radial_error_max_abs": float(np.max(abs_error)),
        "angular_travel_deg": angular_travel_deg,
    }

    stem = path.stem
    output_dir = path.parent
    analyzed_path = output_dir / f"{stem}_analyzed.csv"
    metrics_path = output_dir / f"{stem}_metrics.json"
    trajectory_path = output_dir / f"{stem}_trajectory.png"
    error_path = output_dir / f"{stem}_radial_error.png"

    with analyzed_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["elapsed_s", "x", "y", "radius_from_center", "radial_error", "abs_radial_error"]
        )
        writer.writerows(
            zip(elapsed, x, y, distance, radial_error, abs_error, strict=True)
        )

    with metrics_path.open("w", encoding="utf-8") as metrics_file:
        json.dump(metrics, metrics_file, ensure_ascii=False, indent=2, allow_nan=False)

    theta = np.linspace(0.0, 2.0 * np.pi, 720)
    reference_x = center_x + radius * np.cos(theta)
    reference_y = center_y + radius * np.sin(theta)

    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.plot(reference_x, reference_y, "--", linewidth=2, label=f"{reference_name} circle")
    ax.plot(x, y, linewidth=1.2, color="tab:blue", label="measured trajectory")
    ax.scatter(x[0], y[0], s=55, color="tab:green", marker="o", label="start", zorder=3)
    ax.scatter(x[-1], y[-1], s=65, color="tab:red", marker="x", label="end", zorder=3)
    ax.scatter(center_x, center_y, s=45, color="black", marker="+", label="circle center")
    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlabel(f"x ({args.unit})")
    ax.set_ylabel(f"y ({args.unit})")
    ax.xaxis.set_major_locator(MultipleLocator(25))
    ax.yaxis.set_major_locator(MultipleLocator(25))
    ax.set_title(
        "OmniStamp circular trajectory\n"
        f"radial RMSE={metrics['radial_rmse']:.3f} {args.unit}, "
        f"MAE={metrics['radial_mae']:.3f} {args.unit}"
    )
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.savefig(trajectory_path, dpi=180)

    fig_error, ax_error = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
    ax_error.plot(elapsed - elapsed[0], radial_error, linewidth=1.0)
    ax_error.axhline(0.0, color="black", linewidth=1.0)
    ax_error.axhline(
        metrics["radial_rmse"], color="tab:red", linestyle="--", alpha=0.65, label="+/- RMSE"
    )
    ax_error.axhline(-metrics["radial_rmse"], color="tab:red", linestyle="--", alpha=0.65)
    ax_error.set_xlabel("analysis time (s)")
    ax_error.set_ylabel(f"radial error ({args.unit})")
    ax_error.set_title("Radial tracking error over time")
    ax_error.grid(True, alpha=0.3)
    ax_error.legend()
    fig_error.savefig(error_path, dpi=180)

    print("\nCircle analysis")
    print("-" * 56)
    print(f"Reference       : {metrics['reference']}")
    print(f"Samples         : {metrics['samples_analyzed']} / {metrics['samples_total']}")
    print(f"Point rate      : {point_rate_hz:.2f} Hz")
    print(f"UDP update rate : {update_rate_hz:.2f} Hz")
    print(f"Center          : ({center_x:.4f}, {center_y:.4f}) {args.unit}")
    print(f"Radius          : {radius:.4f} {args.unit}")
    print(f"Radial RMSE     : {metrics['radial_rmse']:.4f} {args.unit}")
    print(f"Radial MAE      : {metrics['radial_mae']:.4f} {args.unit}")
    print(f"Radial std. dev.: {metrics['radial_error_std']:.4f} {args.unit}")
    print(f"95% abs. error  : {metrics['radial_error_p95_abs']:.4f} {args.unit}")
    print(f"Maximum error   : {metrics['radial_error_max_abs']:.4f} {args.unit}")
    print(f"Angular travel  : {angular_travel_deg:.1f} degrees")
    print("\nGenerated files:")
    for generated_path in (analyzed_path, metrics_path, trajectory_path, error_path):
        print(f"  {generated_path.resolve()}")

    if not args.no_show:
        plt.show()
    else:
        plt.close("all")
    return metrics


def main() -> int:
    args = parse_args()
    try:
        capture_path = args.analyze if args.analyze else capture_udp(args)
        analyze_capture(capture_path, args)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
