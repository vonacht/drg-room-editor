import numpy as np
from more_itertools import sliding_window
from scipy.spatial.transform import Rotation as R
import pyqtgraph.opengl as gl
from PySide6.QtGui import QVector3D

DEFAULT_ENTRANCE_VECTOR = np.array((500, 0, 0))

COLORS = {
    "gray": (0.5, 0.5, 0.5, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0),
    "orange": (1.0, 0.65, 0.0, 1.0),
    "green": (0.0, 1.0, 0.0, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
}


def rotate_vector(v, roll, pitch, yaw):
    """This method is used to apply the rotator defined in the Entrances to a default vector v."""
    r = R.from_euler("zyx", [yaw, pitch, roll], degrees=True)  # yaw, pitch, roll
    return r.apply(v)


def return_ffill_parameters(S: dict):
    # First we compute the height of the room, which is the minimum between
    # CeilingHeight (if exists) or VRange (always exists, forced by the schema):
    height = min(h for h in [S["VRange"], S.get("CeilingHeight")] if h is not None)
    center = [S["Location"]["X"], S["Location"]["Y"], S["Location"]["Z"]]
    # The Z coordinate can me moved up or down by the FloorDepth, if it exists.
    # If it does, we also need to change the height of the room accordingly.
    if "FloorDepth" in S:
        floor_depth = S["Location"]["Z"] + S["FloorDepth"]
        if floor_depth <= height:
            center[2] = floor_depth
            height -= floor_depth
    ra, rb = S["HRange"], S["HRange"]

    return np.array(center), height, ra, rb


def create_ellipsoid_lines(S: dict) -> np.ndarray:
    """Create wireframe lines for an ellipsoid. Returns array of line segments."""
    center, height, ra, rb = return_ffill_parameters(S)

    lines = []

    # Latitude circles (horizontal)
    n_lat = 6
    n_points = 30
    for i in range(n_lat + 1):
        phi = (np.pi / 2) * i / n_lat  # 0 to pi/2 (top half)
        z = center[2] + height * np.cos(phi)
        r = ra * np.sin(phi)
        if r < 1e-6:
            continue
        theta = np.linspace(0, 2 * np.pi, n_points)
        x = center[0] + r * np.cos(theta)
        y = center[1] + r * np.sin(theta)
        for j in range(len(theta) - 1):
            lines.append([[x[j], y[j], z], [x[j + 1], y[j + 1], z]])

    # Longitude lines (vertical)
    n_lon = 12
    n_points = 15
    for i in range(n_lon):
        theta = 2 * np.pi * i / n_lon
        phi = np.linspace(0, np.pi / 2, n_points)
        x = center[0] + ra * np.sin(phi) * np.cos(theta)
        y = center[1] + rb * np.sin(phi) * np.sin(theta)
        z = center[2] + height * np.cos(phi)
        for j in range(len(phi) - 1):
            lines.append([[x[j], y[j], z[j]], [x[j + 1], y[j + 1], z[j + 1]]])

    return np.array(lines) if lines else np.empty((0, 2, 3))


def create_tangent_lines(S1: dict, S2: dict) -> list:
    """This method will calculate the tangent lines between pairs of
    FLoodFillLines. These are plotted in the main plot to show that the
    elements of the same Line are connected together.
    """
    C1, h1, r1, _ = return_ffill_parameters(S1)
    C2, h2, r2, _ = return_ffill_parameters(S2)
    tangents = []
    # Top tangent line connecting the peaks;
    tangents.append([[C1[0], C1[1], C1[2] + h1], [C2[0], C2[1], C2[2] + h2]])
    # Lower two tangent lines connecting the base circles:
    dvec = C2 - C1
    dxy = np.linalg.norm(dvec[:2])

    if dxy == 0 or dxy < abs(r1 - r2):
        return tangents

    angle = np.arctan2(dvec[1], dvec[0])
    alpha = np.arccos((r1 - r2) / dxy)

    for sign in [1, -1]:
        theta = angle + sign * alpha
        dir2d = np.array([np.cos(theta), np.sin(theta), 0])

        P1 = C1 + r1 * dir2d
        P2 = C2 + r2 * dir2d
        tangents.append([[P1[0], P1[1], P1[2]], [P2[0], P2[1], P2[2]]])

    return tangents


def create_arrow_lines(start, direction, arrow_size=50):
    """Create lines for an arrow"""
    start = np.array(start)
    direction = np.array(direction)
    end = start + direction

    lines = [[start.tolist(), end.tolist()]]

    # Arrow head
    if np.linalg.norm(direction) > 1e-6:
        d = direction / np.linalg.norm(direction)
        # Find perpendicular vectors
        if abs(d[2]) < 0.9:
            perp1 = np.cross(d, [0, 0, 1])
        else:
            perp1 = np.cross(d, [1, 0, 0])
        perp1 = perp1 / np.linalg.norm(perp1)
        perp2 = np.cross(d, perp1)

        head_base = end - d * arrow_size
        for perp in [perp1, -perp1, perp2, -perp2]:
            head_point = head_base + perp * arrow_size * 0.3
            lines.append([end.tolist(), head_point.tolist()])

    return lines


def room_plotter_3d(view: gl.GLViewWidget, plot_ctx: dict):
    """This method receives the axes and canvas from the main GUI in main.py and
    a context object with:
        + The JSON dict defining the room,
        + Boolean switches telling which features we need to plot,
    and it plots the room.
    """
    room_json = plot_ctx["room"]

    # Clear existing items
    for item in view.items[:]:
        view.removeItem(item)

    all_points = []  # Track all points for auto-centering

    # 1. We plot the FloodFillLines, if ctx.show_ffill is true:
    if plot_ctx["show_ffill"]:
        all_lines = []
        for _, line in room_json["FloodFillLines"].items():
            line_points = line["Points"]
            for ffill in line_points:
                # Draw the ellipsoid wireframe:
                ellipsoid_lines = create_ellipsoid_lines(ffill)
                if len(ellipsoid_lines) > 0:
                    all_lines.extend(ellipsoid_lines.tolist())
                    all_points.extend(ellipsoid_lines.reshape(-1, 3).tolist())

            # For every pair of FloodFillLines, draw the tangent lines
            for ffill_1, ffill_2 in sliding_window(line_points, 2):
                for tangent in create_tangent_lines(ffill_1, ffill_2):
                    all_lines.append(tangent)
                    all_points.extend(tangent)

        if all_lines:
            lines_array = np.array(all_lines)
            line_item = gl.GLLinePlotItem(
                pos=lines_array.reshape(-1, 3),
                color=COLORS["gray"],
                width=1.0,
                mode="lines",
            )
            view.addItem(line_item)

    # 2. We plot the Entrances, if ctx.show_entrances is true:
    if plot_ctx["show_entrances"]:
        entrance_points = {"blue": [], "red": [], "orange": [], "black": []}
        arrow_lines = []

        for _, entrance in room_json["Entrances"].items():
            x, y, z = (
                entrance["Location"]["X"],
                entrance["Location"]["Y"],
                entrance["Location"]["Z"],
            )
            match entrance["Type"]:
                case "Entrance":
                    color = "blue"
                case "Exit":
                    color = "red"
                case "Secondary":
                    color = "orange"
                case _:
                    print(f"Unknown entrance type: {entrance.entrance_type}")
                    color = "black"

            entrance_points[color].append([x, y, z])
            all_points.append([x, y, z])

            # Direction arrow
            rotator = (
                entrance["Direction"]["Roll"],
                entrance["Direction"]["Pitch"],
                entrance["Direction"]["Yaw"],
            )
            rotated_vector = rotate_vector(DEFAULT_ENTRANCE_VECTOR, *rotator)
            arrow_lines.extend(create_arrow_lines([x, y, z], rotated_vector))

        # Add scatter points for each color
        for color, points in entrance_points.items():
            if points:
                scatter = gl.GLScatterPlotItem(
                    pos=np.array(points),
                    color=COLORS[color],
                    size=10,
                    pxMode=True,
                )
                view.addItem(scatter)

        # Add direction arrows
        if arrow_lines:
            arrow_array = np.array(arrow_lines)
            arrow_item = gl.GLLinePlotItem(
                pos=arrow_array.reshape(-1, 3),
                color=COLORS["green"],
                width=2.0,
                mode="lines",
            )
            view.addItem(arrow_item)

    # 3. We plot the FloodFillPillars:
    if plot_ctx["show_pillars"] and "FloodFillPillars" in room_json:
        pillar_colors = ["blue", "red", "orange", "green", "purple", "white"]
        for idx, (_, pillar) in enumerate(room_json["FloodFillPillars"].items()):
            points = [
                (p["Location"]["X"], p["Location"]["Y"], p["Location"]["Z"])
                for p in pillar["Points"]
            ]
            all_points.extend(points)
            pillar_lines = []
            for i in range(len(points) - 1):
                pillar_lines.append([points[i], points[i + 1]])

            if pillar_lines:
                pillar_array = np.array(pillar_lines)
                pillar_item = gl.GLLinePlotItem(
                    pos=pillar_array.reshape(-1, 3),
                    color=COLORS[pillar_colors[idx % len(pillar_colors)]],
                    width=1.5,
                    mode="lines",
                )
                view.addItem(pillar_item)

    # 4. In case of a PE room, we plot the MiningHead and DropPodDown features:
    if plot_ctx["show_entrances"] and (
        "PE_MiningHead" in room_json or "PE_PodDropDown" in room_json
    ):
        pe_points = {"purple": [], "black": []}

        for _, minehead in room_json.get("PE_MiningHead", {}).items():
            x, y, z = (
                minehead["Location"]["X"],
                minehead["Location"]["Y"],
                minehead["Location"]["Z"],
            )
            pe_points["purple"].append([x, y, z])
            all_points.append([x, y, z])

        for _, pod_location in room_json.get("PE_PodDropDown", {}).items():
            x, y, z = (
                pod_location["Location"]["X"],
                pod_location["Location"]["Y"],
                pod_location["Location"]["Z"],
            )
            pe_points["black"].append([x, y, z])
            all_points.append([x, y, z])

        for color, points in pe_points.items():
            if points:
                scatter = gl.GLScatterPlotItem(
                    pos=np.array(points),
                    color=COLORS[color],
                    size=12,
                    pxMode=True,
                )
                view.addItem(scatter)

    # 5. Add cubic bounding box grid
    if all_points:
        pts = np.array(all_points)
        mins = pts.min(axis=0)
        maxs = pts.max(axis=0)
        center = (mins + maxs) / 2

        # Make it a cube using the largest dimension
        extent = (maxs - mins).max()
        extent *= 1.2  # 20% padding
        half = extent / 2

        # Cube corner and spacing
        cube_min = center - half
        spacing = extent / 10

        # Axis at corner
        axis = gl.GLAxisItem()
        axis.setSize(extent, extent, extent)
        axis.translate(cube_min[0], cube_min[1], cube_min[2])
        view.addItem(axis)

        # XY grid (bottom, z=min)
        grid_xy = gl.GLGridItem()
        grid_xy.setSize(extent, extent)
        grid_xy.setSpacing(spacing, spacing)
        grid_xy.translate(center[0], center[1], cube_min[2])
        view.addItem(grid_xy)

        # XZ grid (back wall, y=min)
        grid_xz = gl.GLGridItem()
        grid_xz.setSize(extent, extent)
        grid_xz.setSpacing(spacing, spacing)
        grid_xz.rotate(90, 1, 0, 0)
        grid_xz.translate(center[0], cube_min[1], center[2])
        view.addItem(grid_xz)

        # YZ grid (side wall, x=min)
        grid_yz = gl.GLGridItem()
        grid_yz.setSize(extent, extent)
        grid_yz.setSpacing(spacing, spacing)
        grid_yz.rotate(90, 0, 1, 0)
        grid_yz.translate(cube_min[0], center[1], center[2])
        view.addItem(grid_yz)

        # Update camera center
        view.opts['center'] = QVector3D(float(center[0]), float(center[1]), float(center[2]))
        view.opts['distance'] = extent * 1.5

