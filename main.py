import tkinter as tk
from tkinter import HORIZONTAL, ttk
import json
import ttkbootstrap as tb
from room_parser import validate_room

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from jsonschema import ValidationError
from room_viewer import room_plotter_3d
from json_builder import build_json_and_uasset

import argparse
from pathlib import Path

import logging

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

class App(tb.Window):
    def __init__(self, light_mode, text="{}"):
        super().__init__()

        self.title("DRG Custom Room Editor")
        self.geometry("950x600")
        self.light_mode = light_mode
        if self.light_mode:
            self.style.theme_use("flatly")
        else:
            self.style.theme_use("darkly")

        self.update_job = None
        # The following dict keeps track of the values in the central comboboxes and checkboxes:
        self.feature_record = {}

        # ================= Main geometry with a Windowed Pane =================
        paned = ttk.PanedWindow(self, orient=HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(paned, width=100, height=100, relief="sunken")
        #self.middle = ttk.Frame(paned, width=100, height=100, relief="sunken")
        right = ttk.Frame(paned, width=200, height=100, relief="sunken")

        paned.add(left, weight=1)
        #paned.add(self.middle, weight=3)
        paned.add(right, weight=3)
        # =================  Left Pane: Controls, editor and status box =================
        # ---- Top-left control panel ----
        controls = ttk.Frame(left, padding=(5, 5))
        controls.pack()
        ttk.Button(controls, text="Reset Plot View", command=self.reset_ax_view).pack(side="left", padx=10)
        self.save_button = ttk.Button(
            controls, text="Save UAsset", command=self.try_saving_uasset
        )
        self.save_button.pack(side="left", padx=10)

        self.var_entrances = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Show Entrances",
            variable=self.var_entrances,
            command=self.try_update_from_json,
        ).pack(side="left", padx=10)

        self.var_ffill = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Show FloodFillLines",
            variable=self.var_ffill,
            command=self.try_update_from_json,
        ).pack(side="left", padx=10)

        self.var_pillars = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Show FloodFillPillars",
            variable=self.var_pillars,
            command=self.try_update_from_json,
        ).pack(side="left", padx=10)

        nested_left_pane = ttk.PanedWindow(left, orient=tk.VERTICAL)
        nested_left_pane.pack(fill="both", expand=True)
        editor_frame = ttk.Frame(nested_left_pane, height=400, relief="ridge")
        status_frame = ttk.Frame(nested_left_pane, height=200, relief="ridge")
        nested_left_pane.add(editor_frame, weight=1)
        nested_left_pane.add(status_frame, weight=1)

        # ---- Vertical split: editor / status ----
        # JSON editor
        self.editor = tk.Text(editor_frame, wrap=tk.NONE, undo=True)
        self.editor.insert(tk.END, text)
        self.editor.pack(fill="both", expand=True)

#        # Status box
        self.status = tk.Text(
            status_frame,
            height=4,
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#f4f4f4",
        )
        self.status.pack(fill="both", expand=True)

        # ================= RIGHT COLUMN (PLOT) =================
        if not self.light_mode:
            plt.style.use("dark_background")
        fig = Figure(dpi=100)
        self.ax = fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(fig, master=right)
        if not self.light_mode:       
            fig.patch.set_facecolor("#000000")
            self.ax.patch.set_alpha(0)
            self.ax.patch.set_visible(False)
            self.ax.patch.set_facecolor("none")
            pane = (0.07, 0.07, 0.07, 1)
            self.ax.xaxis.set_pane_color(pane)
            self.ax.yaxis.set_pane_color(pane)
            self.ax.zaxis.set_pane_color(pane)
            self.ax.xaxis._axinfo["grid"]["color"] = "#444444"
            self.ax.yaxis._axinfo["grid"]["color"] = "#444444"
            self.ax.zaxis._axinfo["grid"]["color"] = "#444444"
            self.ax.tick_params(colors="white")
            self.ax.xaxis.label.set_color("white")
            self.ax.yaxis.label.set_color("white")
            self.ax.zaxis.label.set_color("white")
            self.ax.title.set_color("white")
            for axis in [self.ax.xaxis, self.ax.yaxis, self.ax.zaxis]:
                axis.line.set_color("white")
            self.canvas.get_tk_widget().configure(bg="#121212")

        self.canvas.get_tk_widget().pack(fill="both", expand=True)
#
#        # ---- Bindings ----
        self.editor.bind("<<Modified>>", self.on_text_change)
        self.editor.bind("<Control-v>", self.paste_replace)
        self.editor.edit_modified(False)
    
        self.set_status("Ready")
        if text != "{}":
            self.try_update_from_json()

    # ---------- Text handling ----------
    def paste_replace(self, event):
        widget = event.widget
        widget.edit_separator()  # start undo block
        try:
            widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        widget.insert("insert", widget.clipboard_get())
        widget.edit_separator()  # end undo block
        return "break"

    def on_text_change(self, event):
        if not self.editor.edit_modified():
            return

        if self.update_job:
            self.after_cancel(self.update_job)

        self.update_job = self.after(300, self.try_update_from_json)
        self.editor.edit_modified(False)

    def reset_ax_view(self):
        self.ax.view_init()
        self.canvas.draw_idle()

    def try_update_from_json(self):
        self.update_job = None

        raw = self.editor.get("1.0", "end")

        # Check for valid JSON:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            self.set_invalid_state(f"JSON error: {e.msg} (line {e.lineno})")
            return

        # Check for valid JSON room schema:
        try:
            validate_room(data)
        except ValidationError as e:
            self.set_invalid_state(f"JSON room schema error: {e.message}")
            return


        self.room_json = data
        #self.refresh_middle_rows()
        self.set_valid_state()
        #print(self.feature_record)
        # TODO: Add default plot state here
        self.plot_context = {
            "room": self.room_json,
            "show_ffill": self.var_ffill.get(),
            "show_entrances": self.var_entrances.get(),
            "show_pillars": self.var_pillars.get(),
        }
        room_plotter_3d(self.ax, self.canvas, self.plot_context)

#    def refresh_middle_rows(self):
#        for feature in ["FloodFillLines", "Entrances", "FloodFillPillars"]:
#            if feature in self.room_json:
#                self.add_row_middle(feature)
#                for ffill in self.room_json[feature]:
#                    self.add_row_middle(ffill, top=False)
    
#    def add_row_middle(self, name, top=True):
#        row = ttk.Frame(self.middle)
#        row.pack(fill="x", pady=2, padx=5)
#
#        var_check = tk.BooleanVar()
#        var_color = tk.StringVar(value="Red")
#
#        if not top:
#            ttk.Checkbutton(row, variable=var_check).pack(side="left")
#        ttk.Label(row, text=name, width=20).pack(side="left", padx=5)
#        if not top:
#            ttk.Combobox(row, textvariable=var_color, values=["Red","Green","Blue"], width=10, state="readonly").pack(side="left")
#            self.feature_record.update({name: {"visible": var_check.get(), "color": var_color}})


    # ---------- Status + feedback ----------
    def set_status(self, message):
        self.status.config(state=tk.NORMAL)
        self.status.delete("1.0", tk.END)
        self.status.insert(tk.END, message)
        self.status.config(state=tk.DISABLED)

    def set_invalid_state(self, message):
        if self.light_mode:
            self.editor.configure(background="#ffe6e6")
        else:
            self.editor.configure(background="#cf6679")
        self.disable_save_button()
        self.set_status(message)

    def set_valid_state(self):
        if self.light_mode:
            self.editor.configure(background="white")
        else:
            self.editor.configure(bg="#1e1e1e",
                                fg="#ffffff",
                                insertbackground="#ffffff",  # cursor color
                                selectbackground="#3a3a3a",
                                selectforeground="#ffffff")
        self.enable_save_button()
        self.set_status("JSON valid")

    def enable_save_button(self):
        self.save_button.state(["!disabled"])

    def disable_save_button(self):
        self.save_button.state(["disabled"])

    def try_saving_uasset(self):
        build_json_and_uasset(self.room_json)




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="DRG Custom Room Editor")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "filename",
        nargs="?",            # makes it optional
        default=None,          # value if not provided
        help="Optional input filename"
    )

    group.add_argument(
        "-b",
        "--batch",
        nargs="+",            # makes it optional
        default=[],          # value if not provided
        help="Batch mode. Disables the GUI. Accepts one or more directory paths with room JSONs inside."
    )

    parser.add_argument(
        "-l",
        "--light",
        action="store_true",
        help="Starts the GUI in light mode."
    )

    args = parser.parse_args()
    setup_logging()

    if args.filename is not None:
        try:
            with open(args.filename, 'r') as f:
                logging.info(f"Editor GUI started with file {args.filename}")
                json_from_file = json.load(f)
                app = App(args.light, text=json.dumps(json_from_file, indent=4))
                app.mainloop()
        except Exception as e:
            logging.error(e)
    elif args.batch:
        logging.info(f"Running batch mode.")
        # Batch mode logic:
        for directory in args.batch:
            json_files = Path(directory).glob("*.json")
            for file in json_files:
                with open(file, 'r') as room_file:
                    try:
                        room_json = json.load(room_file)
                        # File name to save the uasset:
                        build_json_and_uasset(room_json)
                    except Exception as e:
                        logging.error(f"Error when processing {file}: {e}")
                        continue
    else:
        App().mainloop()
        logging.info("Editor GUI started with a blank file.")
    
