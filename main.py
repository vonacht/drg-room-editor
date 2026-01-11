import tkinter as tk
from tkinter import HORIZONTAL, ttk
import json
from room_parser import validate_room

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from jsonschema import ValidationError
from room_viewer import room_plotter_3d
from json_builder import build_json_and_uasset
import argparse


class App(tk.Tk):
    def __init__(self, text="{}"):
        super().__init__()

        self.title("DRG Custom Room Editor")
        self.geometry("950x600")

        self.update_job = None

        # ================= Main geometry with a Windowed Pane =================
        paned = ttk.PanedWindow(self, orient=HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(paned, width=100, height=100, relief="sunken")
        middle = ttk.Frame(paned, width=100, height=100, relief="sunken")
        right = ttk.Frame(paned, width=200, height=100, relief="sunken")

        paned.add(left, weight=1)
        paned.add(middle, weight=3)
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
        fig = Figure(dpi=100)
        self.ax = fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(fig, master=right)
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

        self.set_valid_state()
        # TODO: Add default plot state here
        self.plot_context = {
            "room": self.room_json,
            "show_ffill": self.var_ffill.get(),
            "show_entrances": self.var_entrances.get(),
            "show_pillars": self.var_pillars.get(),
        }
        room_plotter_3d(self.ax, self.canvas, self.plot_context)

    # ---------- Status + feedback ----------
    def set_status(self, message):
        self.status.config(state=tk.NORMAL)
        self.status.delete("1.0", tk.END)
        self.status.insert(tk.END, message)
        self.status.config(state=tk.DISABLED)

    def set_invalid_state(self, message):
        self.editor.configure(background="#ffe6e6")
        self.disable_save_button()
        self.set_status(message)

    def set_valid_state(self):
        self.editor.configure(background="white")
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
    parser.add_argument(
        "filename",
        nargs="?",            # makes it optional
        default=None,          # value if not provided
        help="Optional input filename"
    )

    args = parser.parse_args()

    if args.filename is not None:
        with open(args.filename, 'r') as f:
            json_from_file = json.load(f)
            app = App(text=json.dumps(json_from_file, indent=4))
            app.mainloop()
    else:
        App().mainloop()

