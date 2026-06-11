import os
import shutil
from datetime import datetime

import yaml
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QFrame, QScrollArea, QStatusBar, QMessageBox,
    QInputDialog, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QFont

from konsave.consts import PROFILES_DIR, CONFIG_FILE
from konsave.funcs import save_profile, apply_profile, remove_profile, export, import_profile


class _Worker(QThread):
    """Runs a blocking konsave operation off the main thread."""
    finished = Signal(bool, str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self._fn(*self._args, **self._kwargs)
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Konsave GUI")
        self.resize(960, 620)
        self._worker = None
        self._build_ui()
        self._build_menu()
        self.refresh_profiles()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        root.addWidget(self._build_left_panel())
        root.addWidget(self._build_detail_panel(), 1)

        self.setStatusBar(QStatusBar())

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QLabel("Profiles")
        heading.setStyleSheet("font-weight: 700; font-size: 14px; color: #94a3b8;")
        layout.addWidget(heading)

        self._profile_list = QListWidget()
        self._profile_list.currentRowChanged.connect(self._on_profile_selected)
        layout.addWidget(self._profile_list)

        self._save_btn = QPushButton("Save Current")
        self._save_btn.setObjectName("success")
        self._save_btn.setToolTip("Snapshot current desktop config as a new profile")
        self._save_btn.clicked.connect(self._on_save)
        layout.addWidget(self._save_btn)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setToolTip("Restore selected profile to disk")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self._apply_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("danger")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self._delete_btn)

        return panel

    def _build_detail_panel(self) -> QFrame:
        self._detail_frame = QFrame()
        layout = QVBoxLayout(self._detail_frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self._detail_name = QLabel("Select a profile")
        self._detail_name.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #f8fafc; background: transparent; border: none;"
        )
        layout.addWidget(self._detail_name)

        self._detail_date = QLabel("")
        self._detail_date.setStyleSheet(
            "color: #64748b; font-size: 12px; background: transparent; border: none;"
        )
        layout.addWidget(self._detail_date)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #334155; border: none; max-height: 1px;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self._sections_container = QWidget()
        self._sections_container.setStyleSheet("background: transparent;")
        self._sections_layout = QVBoxLayout(self._sections_container)
        self._sections_layout.setContentsMargins(0, 4, 0, 4)
        self._sections_layout.setSpacing(8)
        self._sections_layout.addStretch()

        scroll.setWidget(self._sections_container)
        layout.addWidget(scroll, 1)

        # bottom row: export / import
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._export_btn = QPushButton("Export .knsv")
        self._export_btn.setObjectName("secondary")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        btn_row.addWidget(self._export_btn)

        import_btn = QPushButton("Import .knsv")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(import_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return self._detail_frame

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("File")

        edit_cfg = QAction("Edit Config File…", self)
        edit_cfg.setShortcut("Ctrl+,")
        edit_cfg.triggered.connect(self._on_edit_config)
        file_menu.addAction(edit_cfg)

        file_menu.addSeparator()

        wipe_act = QAction("Wipe All Profiles…", self)
        wipe_act.triggered.connect(self._on_wipe)
        file_menu.addAction(wipe_act)

    # ------------------------------------------------------------------ profiles

    def _get_profiles(self) -> list[str]:
        if not os.path.exists(PROFILES_DIR):
            return []
        return sorted(os.listdir(PROFILES_DIR))

    def refresh_profiles(self):
        selected_name = self._selected_name()

        self._profile_list.blockSignals(True)
        self._profile_list.clear()
        for name in self._get_profiles():
            self._profile_list.addItem(name)
        self._profile_list.blockSignals(False)

        if selected_name:
            hits = self._profile_list.findItems(selected_name, Qt.MatchFlag.MatchExactly)
            if hits:
                self._profile_list.setCurrentItem(hits[0])
                return

        if self._profile_list.count():
            self._profile_list.setCurrentRow(0)
        else:
            self._clear_detail()

    def _selected_name(self) -> str | None:
        item = self._profile_list.currentItem()
        return item.text() if item else None

    # ------------------------------------------------------------------ detail view

    def _clear_detail(self):
        self._detail_name.setText("No profiles saved yet")
        self._detail_date.setText('Use "Save Current" to snapshot your desktop config.')
        self._apply_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._clear_sections()

    def _clear_sections(self):
        while self._sections_layout.count() > 1:
            item = self._sections_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_profile_selected(self, row: int):
        if row < 0:
            self._clear_detail()
            return

        name = self._profile_list.item(row).text()
        profile_dir = os.path.join(PROFILES_DIR, name)

        self._detail_name.setText(name)
        mtime = os.path.getmtime(profile_dir)
        dt = datetime.fromtimestamp(mtime).strftime("%B %d, %Y  %H:%M")
        self._detail_date.setText(f"Saved {dt}")

        self._apply_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._export_btn.setEnabled(True)

        self._clear_sections()
        self._populate_sections(profile_dir)

    def _populate_sections(self, profile_dir: str):
        conf_path = os.path.join(profile_dir, "conf.yaml")
        if not os.path.exists(conf_path):
            return
        try:
            with open(conf_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            return

        save_cfg = config.get("save") or {}
        export_cfg = config.get("export") or {}

        if save_cfg:
            self._add_group_heading("Saved sections")
            for sec_name, sec_data in save_cfg.items():
                self._add_section_card(sec_name, sec_data or {})

        if export_cfg:
            self._add_group_heading("Export-only sections")
            for sec_name, sec_data in export_cfg.items():
                self._add_section_card(sec_name, sec_data or {})

    def _add_group_heading(self, text: str):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1px; "
            "color: #475569; background: transparent; border: none;"
        )
        self._sections_layout.insertWidget(self._sections_layout.count() - 1, lbl)

    def _add_section_card(self, name: str, data: dict):
        location = data.get("location", "")
        entries = data.get("entries") or []

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(3)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "font-weight: 600; color: #cbd5e1; background: transparent; border: none;"
        )
        cl.addWidget(name_lbl)

        if location:
            loc_lbl = QLabel(location)
            loc_lbl.setStyleSheet(
                "font-size: 11px; color: #475569; background: transparent; border: none;"
            )
            cl.addWidget(loc_lbl)

        if entries:
            shown = [str(e) for e in entries[:10]]
            suffix = f"  +{len(entries) - 10} more" if len(entries) > 10 else ""
            entry_lbl = QLabel(", ".join(shown) + suffix)
            entry_lbl.setStyleSheet(
                "font-size: 11px; color: #334155; background: transparent; border: none;"
            )
            entry_lbl.setWordWrap(True)
            cl.addWidget(entry_lbl)

        self._sections_layout.insertWidget(self._sections_layout.count() - 1, card)

    # ------------------------------------------------------------------ actions

    def _set_busy(self, busy: bool):
        self._save_btn.setEnabled(not busy)
        self._apply_btn.setEnabled(not busy and bool(self._selected_name()))
        self._delete_btn.setEnabled(not busy and bool(self._selected_name()))
        self._export_btn.setEnabled(not busy and bool(self._selected_name()))

    def _on_save(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        profiles = self._get_profiles()
        force = False
        if name in profiles:
            reply = QMessageBox.question(
                self, "Profile exists",
                f'Profile "{name}" already exists. Overwrite it?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            force = True

        self.statusBar().showMessage("Saving profile…")
        self._set_busy(True)
        self._worker = _Worker(save_profile, name, profiles, force=force)
        self._worker.finished.connect(lambda ok, err: self._after_save(ok, err, name))
        self._worker.start()

    def _after_save(self, ok: bool, err: str, name: str):
        self._set_busy(False)
        if ok:
            self.refresh_profiles()
            hits = self._profile_list.findItems(name, Qt.MatchFlag.MatchExactly)
            if hits:
                self._profile_list.setCurrentItem(hits[0])
            self.statusBar().showMessage(f'Profile "{name}" saved.', 5000)
        else:
            self.statusBar().showMessage(f"Save failed: {err}", 5000)

    def _on_apply(self):
        name = self._selected_name()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Apply Profile",
            f'Apply profile "{name}"?\n\nConfig files will be overwritten. '
            "You may need to log out and back in to see all changes.",
            QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Apply:
            return

        profiles = self._get_profiles()
        self.statusBar().showMessage("Applying profile…")
        self._set_busy(True)
        self._worker = _Worker(apply_profile, name, profiles, len(profiles))
        self._worker.finished.connect(lambda ok, err: self._after_apply(ok, err, name))
        self._worker.start()

    def _after_apply(self, ok: bool, err: str, name: str):
        self._set_busy(False)
        if ok:
            self.statusBar().showMessage(
                f'"{name}" applied. Log out and back in to see all changes.', 7000
            )
        else:
            self.statusBar().showMessage(f"Apply failed: {err}", 5000)

    def _on_delete(self):
        name = self._selected_name()
        if not name:
            return
        reply = QMessageBox.warning(
            self, "Delete Profile",
            f'Delete profile "{name}"?\n\nThis cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        profiles = self._get_profiles()
        remove_profile(name, profiles, len(profiles))
        self.refresh_profiles()
        self.statusBar().showMessage(f'Profile "{name}" deleted.', 5000)

    def _on_export(self):
        name = self._selected_name()
        if not name:
            return
        directory = QFileDialog.getExistingDirectory(
            self, "Choose export directory", os.path.expanduser("~")
        )
        if not directory:
            return
        profiles = self._get_profiles()
        self.statusBar().showMessage("Exporting…")
        self._set_busy(True)
        self._worker = _Worker(
            export, name, profiles, len(profiles), directory, None, False
        )
        self._worker.finished.connect(lambda ok, err: self._after_export(ok, err, name, directory))
        self._worker.start()

    def _after_export(self, ok: bool, err: str, name: str, directory: str):
        self._set_busy(False)
        if ok:
            self.statusBar().showMessage(f'"{name}" exported to {directory}', 6000)
        else:
            self.statusBar().showMessage(f"Export failed: {err}", 5000)

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile",
            os.path.expanduser("~"),
            "Konsave archives (*.knsv)",
        )
        if not path:
            return
        self.statusBar().showMessage("Importing…")
        self._set_busy(True)
        self._worker = _Worker(import_profile, path)
        self._worker.finished.connect(lambda ok, err: self._after_import(ok, err, path))
        self._worker.start()

    def _after_import(self, ok: bool, err: str, path: str):
        self._set_busy(False)
        if ok:
            self.refresh_profiles()
            self.statusBar().showMessage(
                f'Imported "{os.path.basename(path)}".', 5000
            )
        else:
            self.statusBar().showMessage(f"Import failed: {err}", 5000)

    def _on_wipe(self):
        reply = QMessageBox.warning(
            self, "Wipe All Profiles",
            "This will permanently delete ALL saved profiles.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if os.path.exists(PROFILES_DIR):
            shutil.rmtree(PROFILES_DIR)
            os.makedirs(PROFILES_DIR)
        self.refresh_profiles()
        self.statusBar().showMessage("All profiles wiped.", 5000)

    def _on_edit_config(self):
        from gui.dialogs import ConfigEditorDialog
        dlg = ConfigEditorDialog(CONFIG_FILE, self)
        dlg.exec()
