import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui.main_window import MainWindow

STYLESHEET = """
* {
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
}
QDialog {
    background-color: #0f172a;
    color: #e2e8f0;
}
QListWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
    margin: 1px 0;
    color: #e2e8f0;
}
QListWidget::item:selected {
    background-color: #1d4ed8;
    color: #f8fafc;
}
QListWidget::item:hover:!selected {
    background-color: #334155;
}
QPushButton {
    background-color: #1e40af;
    color: #e2e8f0;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #1e293b;
    color: #475569;
}
QPushButton#danger {
    background-color: #7f1d1d;
    color: #fca5a5;
}
QPushButton#danger:hover {
    background-color: #991b1b;
}
QPushButton#success {
    background-color: #14532d;
    color: #86efac;
}
QPushButton#success:hover {
    background-color: #166534;
}
QPushButton#secondary {
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
}
QPushButton#secondary:hover {
    background-color: #334155;
    color: #e2e8f0;
}
QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 10px;
    color: #e2e8f0;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QLabel {
    background: transparent;
    border: none;
}
QFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}
QTextEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
}
QScrollBar:vertical {
    background-color: #0f172a;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #475569;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    background-color: #0f172a;
    height: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #475569;
    border-radius: 4px;
    min-width: 20px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QMenuBar {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
    color: #e2e8f0;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background-color: #1e293b;
    border-radius: 4px;
}
QMenu {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
    color: #e2e8f0;
}
QMenu::item {
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #1d4ed8;
}
QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 8px;
}
QStatusBar {
    background-color: #0f172a;
    color: #64748b;
    border-top: 1px solid #1e293b;
    font-size: 12px;
}
QMessageBox {
    background-color: #0f172a;
}
QInputDialog {
    background-color: #0f172a;
}
QToolTip {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 8px;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Konsave GUI")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
