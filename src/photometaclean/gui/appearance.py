"""Native Qt controls with a blue accent shared with the app icon."""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6 import QtWidgets as W


class VerticalScrollArea(W.QScrollArea):
    """Keep the form within the viewport when native scrollbars appear."""

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.Resize and self.widget() is not None:
            self.widget().setFixedWidth(event.size().width())
        return super().viewportEvent(event)


def card():
    frame = W.QFrame()
    frame.setObjectName("card")
    layout = W.QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(9)
    return frame, layout


def heading(text, parent_layout):
    label = W.QLabel(text)
    label.setObjectName("heading")
    parent_layout.addWidget(label)
    return label


def apply_theme(window):
    preference = window.settings.value("theme", "system")
    scheme = QGuiApplication.styleHints().colorScheme()
    dark = preference == "dark" or (preference == "system" and (scheme == Qt.ColorScheme.Dark or
            (scheme == Qt.ColorScheme.Unknown and W.QApplication.style().standardPalette().window().color().lightness() < 128)))
    if dark:
        bg, panel, field, alt = "#14202c", "#1c2b39", "#233444", "#223241"
        fg, muted, border = "#eef5fa", "#b2c6d6", "#465d70"
        accent, on_accent, hover = "#a2d4f5", "#15354c", "#30465a"
    else:
        bg, panel, field, alt = "#eef3f7", "#ffffff", "#f7f9fb", "#f3f7fa"
        fg, muted, border = "#18354b", "#435e73", "#c3d2dd"
        accent, on_accent, hover = "#185a87", "#ffffff", "#e3eff7"
    pal = QPalette()
    for role, value in {"Window":bg,"WindowText":fg,"Base":panel,"AlternateBase":alt,"Text":fg,
                        "Button":field,"ButtonText":fg,"Highlight":accent,"HighlightedText":on_accent,
                        "ToolTipBase":panel,"ToolTipText":fg,"PlaceholderText":muted}.items():
        pal.setColor(getattr(QPalette.ColorRole,role), QColor(value))
    W.QApplication.instance().setPalette(pal)
    window.setPalette(pal)
    window.setStyleSheet(f"""
        QWidget#surface, QMainWindow {{background:{bg};}}
        QFrame#card {{background:{panel}; border:1px solid {border};border-radius:12px;}}
        QLabel {{color:{fg};background:transparent;}}
        QLabel#heading {{font-size:17px;font-weight:600;}}
        QLabel#brand {{font-size:22px;font-weight:700;}}
        QLabel#secondary {{color:{muted};}}
        QPushButton, QComboBox, QSpinBox {{background:{field};color:{fg};border:1px solid {border};
            border-radius:6px;padding:5px 9px;min-height:18px;}}
        QPushButton:hover:enabled {{background:{hover};}}
        QPushButton:focus, QComboBox:focus, QRadioButton:focus, QCheckBox:focus {{border:2px solid {accent};}}
        QPushButton:disabled {{color:{muted};background:{alt};border-color:{border};}}
        QPushButton#primary:enabled {{background:{accent};border-color:{accent};color:{on_accent};font-weight:700;}}
        QPushButton#primary:hover:enabled {{border-color:{fg};}}
        QRadioButton, QCheckBox {{color:{fg};spacing:8px;padding:2px 0px;}}
        QTableView {{background:{panel};alternate-background-color:{alt};color:{fg};border:1px solid {border};
            selection-background-color:{accent};selection-color:{on_accent};}}
        QHeaderView::section {{background:{field};color:{fg};padding:6px;border:0;border-right:1px solid {border};}}
        QProgressBar {{border:1px solid {border};border-radius:5px;background:{field};text-align:center;min-height:16px;}}
        QProgressBar::chunk {{background:{accent};border-radius:4px;}}
    """)
