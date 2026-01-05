import tkinter as tk
from tkinter import ttk
import json
from room_parser import validate_room

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from jsonschema import ValidationError
from room_viewer import room_plotter_3d
from json_builder import build_json_and_uasset


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("DRG Custom Room Editor")
        self.geometry("950x600")

        self.update_job = None

        # ================= MAIN LEFT / RIGHT SPLIT =================
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # ================= LEFT COLUMN =================
        left_column = ttk.Frame(main)
        left_column.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        left_column.rowconfigure(1, weight=1)  # editor expands
        left_column.rowconfigure(2, weight=0)  # status fixed-ish

        # ---- Top-left control panel ----
        controls = ttk.Frame(left_column, padding=(5, 5))
        controls.grid(row=0, column=0, sticky="ew")

        ttk.Button(controls, text="Reset Plot View", command=self.reset_ax_view).grid(
            row=0, column=0, padx=10
        )

        self.save_button = ttk.Button(
            controls, text="Save UAsset", command=self.try_saving_uasset
        )
        self.save_button.grid(row=0, column=1, padx=10)

        self.var_entrances = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Show Entrances",
            variable=self.var_entrances,
            command=self.try_update_from_json,
        ).grid(row=0, column=3, padx=10)

        self.var_ffill = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Show FloodFillLines",
            variable=self.var_ffill,
            command=self.try_update_from_json,
        ).grid(row=0, column=4, padx=10)
        # ---- Vertical split: editor / status ----
        left_pane = ttk.Panedwindow(left_column, orient=tk.VERTICAL)
        left_pane.grid(row=1, column=0, sticky="nsew")

        # JSON editor
        editor_frame = ttk.Frame(left_pane)
        self.editor = tk.Text(editor_frame, wrap=tk.NONE)
        self.editor.pack(fill=tk.BOTH, expand=True)

        self.editor.insert(tk.END, """{}""")

        left_pane.add(editor_frame, weight=4)

        # Status box
        status_frame = ttk.Frame(left_pane, height=80)
        self.status = tk.Text(
            status_frame,
            height=4,
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#f4f4f4",
        )
        self.status.pack(fill=tk.BOTH, expand=True)

        left_pane.add(status_frame, weight=1)

        # ================= RIGHT COLUMN (PLOT) =================
        fig = Figure(dpi=100)
        self.ax = fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(fig, master=main)
        self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # ---- Bindings ----
        self.editor.bind("<<Modified>>", self.on_text_change)
        self.editor.edit_modified(False)

        # TODO: add default plot state here if needed
        self.set_status("Ready")

    # ---------- Text handling ----------
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
    App().mainloop()
