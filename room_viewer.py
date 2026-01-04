import tkinter as tk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from more_itertools import sliding_window
from collections import namedtuple
from scipy.spatial.transform import Rotation as R

Hemisphere = namedtuple('Hemisphere', ['center', 'radius', 'height'])
Entrance = namedtuple('Entrance', ['location', 'entrance_type', 'orientation'])


def rotate_vector(v, roll, pitch, yaw):
    print(v, yaw, pitch, roll)
    r = R.from_euler('zyx', [yaw, pitch, roll], degrees=True)  # yaw, pitch, roll
    return r.apply(v)

def create_oval(S: Hemisphere) -> tuple:
    center, a, b, c = S.center, S.radius, S.radius, S.height
    # Spherical coordinates
    phi = np.linspace(0, np.pi/2, 30)     # top half only
    theta = np.linspace(0, 2*np.pi, 60)
    phi, theta = np.meshgrid(phi, theta)

    # Parametric equations
    x = center[0] + a * np.sin(phi) * np.cos(theta)
    y = center[1] + b * np.sin(phi) * np.sin(theta)
    z = center[2] + c * np.cos(phi)

    return x, y, z

def create_tangent_lines(S1: Hemisphere, S2: Hemisphere) -> list:
    C1, C2, r1, r2, h1, h2 = S1.center, S2.center, S1.radius, S2.radius, S1.height, S2.height
    C1, C2 = np.array(C1), np.array(C2)
    tangents = []
    # Top tangent line:
    x = [C1[0], C2[0]]
    y = [C1[1], C2[1]]
    z = [C1[2] + h1, C2[2] + h2]
    tangents.append((x, y, z))
    # Lower tangent line:
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

def build_hemisphere(hdata: dict):
    return Hemisphere((hdata["Location"]["X"], hdata["Location"]['Y'], hdata["Location"]['Z']),
                      hdata["HRange"],
                      hdata["VRange"])

def build_entrance(edata: dict):
    return Entrance((edata["Location"]["X"], edata["Location"]["Y"], edata["Location"]["Z"]),
                     edata["Type"],
                     (edata["Direction"]["Roll"], edata["Direction"]["Pitch"], edata["Direction"]["Yaw"]))


def parse_room_json(room_json: dict):
    floodfilllines = []
    for ffill in room_json["FloodFillLines"]:
        line = [build_hemisphere(l) for l in room_json["FloodFillLines"][ffill]]
        floodfilllines.append(line)
    entrances = [build_entrance(v) for _, v in room_json["Entrances"].items()]
    return floodfilllines, entrances

def set_axes_equal(ax):
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_mid = (x_limits[0] + x_limits[1]) / 2
    y_mid = (y_limits[0] + y_limits[1]) / 2
    z_mid = (z_limits[0] + z_limits[1]) / 2

    radius = max(
        x_limits[1] - x_limits[0],
        y_limits[1] - y_limits[0],
        z_limits[1] - z_limits[0],
    ) / 2

    ax.set_xlim(x_mid - radius, x_mid + radius)
    ax.set_ylim(y_mid - radius, y_mid + radius)
    ax.set_zlim(z_mid - radius, z_mid + radius)

def room_plotter_3d(ax, canvas, room_json, show_entrances, show_ffill):

    ax.cla()
    floodfilllines, entrances = parse_room_json(room_json)

    if show_ffill:
        for line in floodfilllines:
            for c in line:
                # Draw the circles:
                x, y, z = create_oval(c)
                ax.plot_wireframe(x, y, z, color='gray', linewidth=0.5, cstride=5, rstride=5)
            for a, b in sliding_window(line, 2):
                p = create_tangent_lines(a, b)
                for tangent in p:
                    x, y, z = tangent
                    ax.plot(x, y, z, linewidth=0.6, color = 'gray')

    if show_entrances:
        for entrance in entrances:
            x, y, z = entrance.location
            match entrance.entrance_type:
                case 'Entrance':
                    color = 'blue'
                case 'Exit':
                    color = 'red'
                case 'Secondary':
                    color = 'orange'
                case _:
                    print(f"Unknown entrance type: {entrance.entrance_type}")
                    color = 'black'
            ax.scatter(x, y, z, color=color, s = 15)

            v = rotate_vector(np.array([500, 0, 0]), *entrance.orientation)
            print(v)
            
            ax.quiver(entrance.location[0], entrance.location[1], entrance.location[2],
                  v[0], v[1], v[2],
                  color='green', linewidth=2)

    set_axes_equal(ax)
    ax.xaxis.pane.set_visible(False)
    ax.yaxis.pane.set_visible(False)
    ax.zaxis.pane.set_visible(False)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(room_json["Name"])

    canvas.draw_idle()
    ax.set_box_aspect([1,1,1])

