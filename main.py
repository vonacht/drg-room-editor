import sys
import json
import argparse
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QCheckBox, QPlainTextEdit
)
from PySide6.QtCore import Qt, QTimer, QRect, QSize, QRegularExpression
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter
)

import pyqtgraph.opengl as gl

from jsonschema import ValidationError
from room_parser import validate_room
from room_viewer import room_plotter_3d
from json_builder import build_json_and_uasset


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


class JsonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON."""

    def __init__(self, parent=None, dark_mode=True):
        super().__init__(parent)
        self.highlighting_rules = []

        if dark_mode:
            # Dark mode colors
            key_format = QTextCharFormat()
            key_format.setForeground(QColor("#9cdcfe"))  # Light blue

            string_format = QTextCharFormat()
            string_format.setForeground(QColor("#ce9178"))  # Orange

            number_format = QTextCharFormat()
            number_format.setForeground(QColor("#b5cea8"))  # Light green

            keyword_format = QTextCharFormat()
            keyword_format.setForeground(QColor("#569cd6"))  # Blue

            brace_format = QTextCharFormat()
            brace_format.setForeground(QColor("#ffd700"))  # Gold
        else:
            # Light mode colors
            key_format = QTextCharFormat()
            key_format.setForeground(QColor("#0451a5"))

            string_format = QTextCharFormat()
            string_format.setForeground(QColor("#a31515"))

            number_format = QTextCharFormat()
            number_format.setForeground(QColor("#098658"))

            keyword_format = QTextCharFormat()
            keyword_format.setForeground(QColor("#0000ff"))

            brace_format = QTextCharFormat()
            brace_format.setForeground(QColor("#000000"))

        # Rules: (pattern, format)
        # Keys (before colon)
        self.highlighting_rules.append(
            (QRegularExpression(r'"[^"]*"\s*(?=:)'), key_format)
        )
        # Strings (values)
        self.highlighting_rules.append(
            (QRegularExpression(r':\s*"[^"]*"'), string_format)
        )
        # Numbers
        self.highlighting_rules.append(
            (QRegularExpression(r'\b-?\d+\.?\d*([eE][+-]?\d+)?\b'), number_format)
        )
        # Keywords: true, false, null
        self.highlighting_rules.append(
            (QRegularExpression(r'\b(true|false|null)\b'), keyword_format)
        )
        # Braces and brackets
        self.highlighting_rules.append(
            (QRegularExpression(r'[\[\]{}]'), brace_format)
        )

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class LineNumberArea(QWidget):
    """Line number area for CodeEditor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit with line numbers."""

    def __init__(self, parent=None, dark_mode=True):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        self.update_line_number_area_width(0)

        # Use monospace font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        bg_color = QColor("#1e1e1e") if self.dark_mode else QColor("#f0f0f0")
        text_color = QColor("#858585") if self.dark_mode else QColor("#666666")
        painter.fillRect(event.rect(), bg_color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(text_color)
                painter.drawText(
                    0, top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class App(QMainWindow):
    def __init__(self, light_mode, text="{}"):
        super().__init__()

        self.setWindowTitle("DRG Custom Room Editor")
        self.resize(950, 600)
        self.light_mode = light_mode
        self.room_json = None

        # Debounce timer for text updates
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.try_update_from_json)

        # Apply theme
        if not self.light_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #121212; }
                QWidget { background-color: #121212; color: #ffffff; }
                QPushButton {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444444;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover { background-color: #3d3d3d; }
                QPushButton:disabled { background-color: #1a1a1a; color: #666666; }
                QCheckBox { color: #ffffff; }
                QPlainTextEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #444444;
                }
                QSplitter::handle { background-color: #444444; }
            """)

        # ================= Main layout with QSplitter =================
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(main_splitter)

        # Left side container
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # ---- Top-left control panel ----
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(5, 5, 5, 5)

        reset_btn = QPushButton("Reset Plot View")
        reset_btn.clicked.connect(self.reset_view)
        controls_layout.addWidget(reset_btn)

        self.save_button = QPushButton("Save UAsset")
        self.save_button.clicked.connect(self.try_saving_uasset)
        controls_layout.addWidget(self.save_button)

        self.check_entrances = QCheckBox("Show Entrances")
        self.check_entrances.setChecked(True)
        self.check_entrances.stateChanged.connect(self.try_update_from_json)
        controls_layout.addWidget(self.check_entrances)

        self.check_ffill = QCheckBox("Show FloodFillLines")
        self.check_ffill.setChecked(True)
        self.check_ffill.stateChanged.connect(self.try_update_from_json)
        controls_layout.addWidget(self.check_ffill)

        self.check_pillars = QCheckBox("Show FloodFillPillars")
        self.check_pillars.setChecked(True)
        self.check_pillars.stateChanged.connect(self.try_update_from_json)
        controls_layout.addWidget(self.check_pillars)

        controls_layout.addStretch()
        left_layout.addWidget(controls)

        # ---- Vertical split: editor / status ----
        nested_splitter = QSplitter(Qt.Orientation.Vertical)

        # JSON editor with syntax highlighting and line numbers
        self.editor = CodeEditor(dark_mode=not self.light_mode)
        self.editor.setPlainText(text)
        self.editor.textChanged.connect(self.on_text_change)
        self.highlighter = JsonHighlighter(self.editor.document(), dark_mode=not self.light_mode)
        nested_splitter.addWidget(self.editor)

        # Status box
        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        if self.light_mode:
            self.status.setStyleSheet("background-color: #f4f4f4;")
        nested_splitter.addWidget(self.status)

        nested_splitter.setSizes([400, 200])
        left_layout.addWidget(nested_splitter)

        main_splitter.addWidget(left_widget)

        # ================= Right side (3D View) =================
        self.gl_view = gl.GLViewWidget()
        self.gl_view.setBackgroundColor('black')

        # Set initial camera position
        self.gl_view.setCameraPosition(distance=3000, elevation=30, azimuth=45)

        main_splitter.addWidget(self.gl_view)
        main_splitter.setSizes([300, 650])

        self.set_status("Ready")
        if text != "{}":
            self.try_update_from_json()

    # ---------- View control ----------
    def reset_view(self):
        self.gl_view.setCameraPosition(distance=3000, elevation=30, azimuth=45)

    # ---------- Text handling ----------
    def on_text_change(self):
        self.update_timer.start(300)  # 300ms debounce

    def try_update_from_json(self):
        raw = self.editor.toPlainText()

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

        self.plot_context = {
            "room": self.room_json,
            "show_ffill": self.check_ffill.isChecked(),
            "show_entrances": self.check_entrances.isChecked(),
            "show_pillars": self.check_pillars.isChecked(),
        }
        room_plotter_3d(self.gl_view, self.plot_context)

    # ---------- Status + feedback ----------
    def set_status(self, message):
        self.status.setPlainText(message)

    def set_invalid_state(self, message):
        if self.light_mode:
            self.editor.setStyleSheet("background-color: #ffe6e6;")
        else:
            self.editor.setStyleSheet(
                "background-color: #cf6679; color: #ffffff; border: 1px solid #444444;"
            )
        self.disable_save_button()
        self.set_status(message)

    def set_valid_state(self):
        if self.light_mode:
            self.editor.setStyleSheet("background-color: white;")
        else:
            self.editor.setStyleSheet(
                "background-color: #1e1e1e; color: #ffffff; border: 1px solid #444444;"
            )
        self.enable_save_button()
        self.set_status("JSON valid")

    def enable_save_button(self):
        self.save_button.setEnabled(True)

    def disable_save_button(self):
        self.save_button.setEnabled(False)

    def try_saving_uasset(self):
        build_json_and_uasset(self.room_json)

    def closeEvent(self, _event):
        import os
        os._exit(0)


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

    if args.batch:
        logging.info("Running batch mode.")
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
        qt_app = QApplication(sys.argv)

        if args.filename is not None:
            try:
                with open(args.filename, 'r') as f:
                    logging.info(f"Editor GUI started with file {args.filename}")
                    json_from_file = json.load(f)
                    app = App(args.light, text=json.dumps(json_from_file, indent=4))
            except Exception as e:
                logging.error(e)
                sys.exit(1)
        else:
            logging.info("Editor GUI started with a blank file.")
            app = App(args.light)

        app.show()
        sys.exit(qt_app.exec())
