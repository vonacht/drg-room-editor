import numpy as np
from more_itertools import sliding_window
from scipy.spatial.transform import Rotation as R

DEFAULT_ENTRANCE_VECTOR = np.array((500, 0, 0))


def rotate_vector(v, roll, pitch, yaw):
    """This method is used to apply the rotator defined in the Entrances to a default vector v."""
    r = R.from_euler("zyx", [yaw, pitch, roll], degrees=True)  # yaw, pitch, roll
    return r.apply(v)


def create_ellipsoid(S: dict) -> tuple:
    center = S["Location"]["X"], S["Location"]["Y"], S["Location"]["Z"]
    ra, rb, height = S["HRange"], S["HRange"], S["VRange"]
    # Spherical coordinates:
    phi = np.linspace(0, np.pi / 2, 30)  # top half only
    theta = np.linspace(0, 2 * np.pi, 60)
    phi, theta = np.meshgrid(phi, theta)
    # Parametric equations:
    x = center[0] + ra * np.sin(phi) * np.cos(theta)
    y = center[1] + rb * np.sin(phi) * np.sin(theta)
    z = center[2] + height * np.cos(phi)
    return x, y, z


def create_tangent_lines(S1: dict, S2: dict) -> list:
    """This method will calculate the tangent lines between pairs of
    FLoodFillLines. These are plotted in the main plot to show that the
    elements of the same Line are connected together.
    """
    C1 = np.array((S1["Location"]["X"], S1["Location"]["Y"], S1["Location"]["Z"]))
    C2 = np.array((S2["Location"]["X"], S2["Location"]["Y"], S2["Location"]["Z"]))
    r1, r2 = S1["HRange"], S2["HRange"]
    h1, h2 = S1["VRange"], S2["VRange"]
    tangents = []
    # Top tangent line connecting the peaks;
    x = [C1[0], C2[0]]
    y = [C1[1], C2[1]]
    z = [C1[2] + h1, C2[2] + h2]
    tangents.append((x, y, z))
    # Lower two tangent lines connecting the base circles:
    dvec = C2 - C1
    dxy = np.linalg.norm(dvec[:2])

    if dxy < abs(r1 - r2):
        return []

    angle = np.arctan2(dvec[1], dvec[0])
    alpha = np.arccos((r1 - r2) / dxy)

    for sign in [1, -1]:
        theta = angle + sign * alpha
        dir2d = np.array([np.cos(theta), np.sin(theta), 0])

        P1 = C1 + r1 * dir2d
        P2 = C2 + r2 * dir2d
        tangents.append(([P1[0], P2[0]], [P1[1], P2[1]], [P1[2], P2[2]]))

    return tangents


def set_axes_equal(ax):
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_mid = (x_limits[0] + x_limits[1]) / 2
    y_mid = (y_limits[0] + y_limits[1]) / 2
    z_mid = (z_limits[0] + z_limits[1]) / 2

    radius = (
        max(
            x_limits[1] - x_limits[0],
            y_limits[1] - y_limits[0],
            z_limits[1] - z_limits[0],
        )
        / 2
    )

    ax.set_xlim(x_mid - radius, x_mid + radius)
    ax.set_ylim(y_mid - radius, y_mid + radius)
    ax.set_zlim(z_mid - radius, z_mid + radius)


def room_plotter_3d(ax, canvas, plot_ctx: dict):
    """This method receives the axes and canvas from the main GUI in main.py and
    a context object with:
        + The JSON dict defining the room.
        + Boolean switches telling which features we need to plot.
    and it plots the room.
    """
    room_json = plot_ctx["room"]
    ax.cla()
    # 1. We plot the FLoodFillLines, if ctx.show_ffill is true:
    if plot_ctx["show_ffill"]:
        for _, line in room_json["FloodFillLines"].items():
            for ffill in line:
                # Draw the circles in wireframe:
                x, y, z = create_ellipsoid(ffill)
                ax.plot_wireframe(
                    x, y, z, color="gray", linewidth=0.5, cstride=5, rstride=5
                )
            # For every pair of FLoodFillLines, draw the tangent lines to visually show that they
            # are connected:
            for ffill_1, ffill_2 in sliding_window(line, 2):
                tangents = create_tangent_lines(ffill_1, ffill_2)
                for tangent in tangents:
                    x, y, z = tangent
                    ax.plot(x, y, z, linewidth=0.6, color="gray")
    # 2. We plot the Entrances, if ctx.show_entrances is true:
    if plot_ctx["show_entrances"]:
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
            # Here we plot the entrance locations as a sphere with the color defined in the previous match case:
            ax.scatter(x, y, z, color=color, s=15)
            # Here we apply the rotator vector defined in the entrance to a vector [500, 0, 0] which is the default:
            rotator = (
                entrance["Direction"]["Roll"],
                entrance["Direction"]["Pitch"],
                entrance["Direction"]["Yaw"],
            )
            rotated_vector = rotate_vector(DEFAULT_ENTRANCE_VECTOR, *rotator)
            # And we plot the vector itself with an arrow:
            ax.quiver(
                x,
                y,
                z,
                rotated_vector[0],
                rotated_vector[1],
                rotated_vector[2],
                color="green",
                linewidth=2,
            )

    # 3. Some plotting directives:
    set_axes_equal(ax)
    ax.xaxis.pane.set_visible(False)
    ax.yaxis.pane.set_visible(False)
    ax.zaxis.pane.set_visible(False)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(room_json["Name"])

    canvas.draw_idle()
    ax.set_box_aspect([1, 1, 1])
