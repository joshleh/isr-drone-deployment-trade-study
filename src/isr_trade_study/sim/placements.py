from __future__ import annotations

from math import ceil, sqrt
from typing import List, Sequence, Tuple


Point = Tuple[int, int]


def generate_uniform_static_points(width: int, height: int, count: int) -> List[Point]:
    """Generate evenly spaced loiter points across the grid.

    Uses a coarse lattice so fleet-size sweeps add spatial value rather
    than duplicating loiter locations.
    """
    if count <= 0:
        return []

    width = max(1, int(width))
    height = max(1, int(height))

    cols = max(1, ceil(sqrt(count * width / max(height, 1))))
    rows = max(1, ceil(count / cols))

    if cols == 1:
        xs = [width // 2]
    else:
        xs = [round(i * (width - 1) / (cols - 1)) for i in range(cols)]

    if rows == 1:
        ys = [height // 2]
    else:
        ys = [round(i * (height - 1) / (rows - 1)) for i in range(rows)]

    points = [(x, y) for y in ys for x in xs]
    return points[:count]


def resolve_static_points(
    width: int,
    height: int,
    num_drones: int,
    explicit_points: Sequence[Point] | None,
    point_mode: str = "explicit",
) -> List[Point]:
    """Resolve loiter points for static deployments.

    Modes:
      - explicit  : honor provided points; append unique lattice points if
        the fleet is larger than the explicit list.
      - auto_grid : ignore explicit points and generate a uniform lattice.
    """
    mode = str(point_mode).strip().lower()
    if mode not in {"explicit", "auto_grid"}:
        raise ValueError(f"Unknown static point mode: {point_mode}")

    if mode == "auto_grid":
        return generate_uniform_static_points(width, height, num_drones)

    points = list(explicit_points or [])
    if len(points) >= num_drones:
        return points[:num_drones]

    generated = generate_uniform_static_points(width, height, max(num_drones, len(points)))
    seen = set(points)
    for point in generated:
        if point in seen:
            continue
        points.append(point)
        seen.add(point)
        if len(points) == num_drones:
            break

    if len(points) < num_drones:
        raise ValueError("Unable to resolve enough unique static loiter points.")

    return points
