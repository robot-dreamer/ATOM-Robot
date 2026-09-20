"""Overlay planar Voronoi cells on the photographed ATOM coverage montage.

The map corners and robot centers are calibrated for the supplied three-panel
photograph. Voronoi cells are computed in the 600 x 600 map coordinate frame
and projected back into each perspective view before rendering.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


PALETTE = {
    1: (0, 114, 178),       # blue
    2: (230, 159, 0),       # orange
    3: (0, 158, 115),       # green
    4: (204, 121, 167),     # magenta
    5: (213, 94, 0),        # vermillion
}

# Full-image pixel coordinates in TL, TR, BR, BL order.
PANELS = [
    {
        "corners": [(18, 15), (549, 7), (587, 536), (-3, 538)],
        "robots": [(1, 286, 143), (3, 149, 367), (2, 396, 397)],
    },
    {
        "corners": [(686, 14), (1219, 4), (1255, 536), (665, 537)],
        "robots": [(1, 965, 112), (4, 957, 285), (3, 801, 380), (2, 1099, 389)],
    },
    {
        "corners": [(1353, 15), (1886, 4), (1922, 538), (1332, 538)],
        "robots": [
            (1, 1544, 107),
            (4, 1747, 169),
            (3, 1449, 323),
            (2, 1797, 393),
            (5, 1587, 444),
        ],
    },
]


def clip_half_plane(
    polygon: list[np.ndarray], site: np.ndarray, other: np.ndarray
) -> list[np.ndarray]:
    """Keep points no farther from site than from other."""
    normal = other - site
    offset = (float(other @ other) - float(site @ site)) / 2.0

    def value(point: np.ndarray) -> float:
        return float(normal @ point) - offset

    result: list[np.ndarray] = []
    start = polygon[-1]
    start_value = value(start)
    start_inside = start_value <= 1e-8

    for end in polygon:
        end_value = value(end)
        end_inside = end_value <= 1e-8
        if start_inside != end_inside:
            denominator = start_value - end_value
            if abs(denominator) > 1e-12:
                t = start_value / denominator
                result.append(start + t * (end - start))
        if end_inside:
            result.append(end.copy())
        start = end
        start_value = end_value
        start_inside = end_inside
    return result


def voronoi_cells(points: list[np.ndarray]) -> list[list[np.ndarray]]:
    boundary = [
        np.array([0.0, 0.0]),
        np.array([600.0, 0.0]),
        np.array([600.0, 600.0]),
        np.array([0.0, 600.0]),
    ]
    cells: list[list[np.ndarray]] = []
    for index, site in enumerate(points):
        cell = [point.copy() for point in boundary]
        for other_index, other in enumerate(points):
            if other_index != index:
                cell = clip_half_plane(cell, site, other)
        cells.append(cell)
    return cells


def homographies(corners: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    map_corners = np.float32([[0, 0], [600, 0], [600, 600], [0, 600]])
    image_corners = np.float32(corners)
    map_to_image = cv2.getPerspectiveTransform(map_corners, image_corners)
    image_to_map = cv2.getPerspectiveTransform(image_corners, map_corners)
    return map_to_image, image_to_map


def transform_points(points: list[np.ndarray], matrix: np.ndarray) -> np.ndarray:
    array = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(array, matrix).reshape(-1, 2)


def render(source: Path, output: Path) -> None:
    original = Image.open(source).convert("RGB")
    result = original.copy()
    fill_layer = Image.new("RGBA", original.size, (0, 0, 0, 0))
    fill_draw = ImageDraw.Draw(fill_layer, "RGBA")
    edge_layer = Image.new("RGBA", original.size, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge_layer, "RGBA")

    all_robot_centers: list[tuple[int, int, int]] = []
    for panel in PANELS:
        map_to_image, image_to_map = homographies(panel["corners"])
        robot_pixels = [np.array([x, y], dtype=np.float32) for _, x, y in panel["robots"]]
        robot_map = transform_points(robot_pixels, image_to_map)
        cells = voronoi_cells([point for point in robot_map])

        for (robot_id, center_x, center_y), cell in zip(panel["robots"], cells):
            polygon = transform_points(cell, map_to_image)
            polygon_xy = [(float(x), float(y)) for x, y in polygon]
            color = PALETTE[robot_id]
            fill_draw.polygon(polygon_xy, fill=(*color, 42))
            edge_draw.line(
                polygon_xy + [polygon_xy[0]],
                fill=(255, 255, 255, 215),
                width=5,
                joint="curve",
            )
            edge_draw.line(
                polygon_xy + [polygon_xy[0]],
                fill=(38, 75, 91, 245),
                width=2,
                joint="curve",
            )
            all_robot_centers.append((robot_id, center_x, center_y))

    result = Image.alpha_composite(result.convert("RGBA"), fill_layer)
    result = Image.alpha_composite(result, edge_layer)

    # Restore the original robot appearance above the translucent cell fills.
    robot_mask = Image.new("L", original.size, 0)
    mask_draw = ImageDraw.Draw(robot_mask)
    for _, center_x, center_y in all_robot_centers:
        radius = 31
        mask_draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            fill=255,
        )
    robot_mask = robot_mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    result = Image.composite(original.convert("RGBA"), result, robot_mask)

    # Match each physical robot to its colored Voronoi cell.
    marker_layer = Image.new("RGBA", original.size, (0, 0, 0, 0))
    marker_draw = ImageDraw.Draw(marker_layer, "RGBA")
    for robot_id, center_x, center_y in all_robot_centers:
        color = PALETTE[robot_id]
        radius = 28
        marker_draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            outline=(*color, 255),
            width=3,
        )
    result = Image.alpha_composite(result, marker_layer)

    output.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(output, quality=96)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.source, args.output)


if __name__ == "__main__":
    main()
