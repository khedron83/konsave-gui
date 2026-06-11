import os
import yaml
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QMessageBox,
)
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter
from PySide6.QtCore import Qt, QRegularExpression


class _YamlHighlighter(QSyntaxHighlighter):
    """Minimal YAML syntax highlighting."""

    def __init__(self, document):
        super().__init__(document)

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(700)
            return f

        self._rules = [
            # Comments
            (QRegularExpression(r"#[^\n]*"), fmt("#475569")),
            # Keys (word before colon)
            (QRegularExpression(r"^\s*[\w\-]+(?=\s*:)"), fmt("#93c5fd")),
            # Strings in quotes
            (QRegularExpression(r'"[^"]*"'), fmt("#86efac")),
            (QRegularExpression(r"'[^']*'"), fmt("#86efac")),
            # Values after colon (unquoted)
            (QRegularExpression(r"(?<=:\s)[^\n#]+"), fmt("#d1fae5")),
            # List item dashes
            (QRegularExpression(r"^\s*-\s"), fmt("#94a3b8", bold=True)),
            # YAML document markers
            (QRegularExpression(r"^---$|^\.\.\.$"), fmt("#7c3aed", bold=True)),
            # Placeholders like $HOME, $CONFIG_DIR
            (QRegularExpression(r"\$[\w{=\"}]+"), fmt("#fbbf24")),
        ]

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


class ConfigEditorDialog(QDialog):
    def __init__(self, config_path: str, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self.setWindowTitle("Edit Config File")
        self.resize(760, 640)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        path_lbl = QLabel(self._config_path)
        path_lbl.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(path_lbl)

        self._editor = QTextEdit()
        mono = QFont("Monospace", 11)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(mono)
        self._editor.setTabStopDistance(16.0)
        _YamlHighlighter(self._editor.document())
        layout.addWidget(self._editor)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _load(self):
        try:
            with open(self._config_path, encoding="utf-8") as f:
                self._editor.setPlainText(f.read())
        except FileNotFoundError:
            self._editor.setPlainText("")

    def _save(self):
        text = self._editor.toPlainText()
        try:
            yaml.safe_load(text)
        except yaml.YAMLError as exc:
            QMessageBox.critical(self, "Invalid YAML", str(exc))
            return
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.accept()
        except OSError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
