"""A user reviews and copies the report locally before opening the public forum."""
from PySide6 import QtWidgets as W
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication

from photometaclean.metadata.feedback import DISCUSSIONS, PLATFORMS, feedback_text


def show_feedback(parent, record, german):
    def t(en, de):
        return de if german else en

    dialog = W.QDialog(parent)
    dialog.setWindowTitle(t("Report an AI label", "KI-Hinweis melden"))
    dialog.resize(690, 520)
    layout = W.QVBoxLayout(dialog)
    hint = W.QLabel(t(
        "Still seeing an AI label after upload? Pick the platform, check the text and copy it into a new public GitHub discussion. Please add the wording of the label and which file you uploaded. You can keep your photo private.",
        "Wird dein Bild nach dem Hochladen weiterhin als KI markiert? Wähle die Plattform und prüfe den Text. Kopiere ihn in einen neuen Beitrag im öffentlichen GitHub-Forum. Ergänze dort den Wortlaut des Hinweises und ob du das Original oder die Kopie hochgeladen hast. Dein Foto brauchst du dafür nicht zu teilen."))
    hint.setWordWrap(True)
    layout.addWidget(hint)
    platform = W.QComboBox()
    platform.addItem(t("Choose platform (optional)", "Plattform wählen (freiwillig)"), "")
    for name in PLATFORMS:
        platform.addItem(name, name)
    layout.addWidget(platform)
    extra = W.QCheckBox(t("Include potentially relevant unknown field names", "Auch möglicherweise relevante unbekannte Feldnamen zeigen"))
    layout.addWidget(extra)
    preview = W.QPlainTextEdit()
    preview.setReadOnly(True)
    layout.addWidget(preview)
    status = W.QLabel()
    layout.addWidget(status)

    def refresh():
        preview.setPlainText(feedback_text(record, "de" if german else "en", platform.currentData(), extra.isChecked()))
        status.clear()

    platform.currentIndexChanged.connect(refresh)
    extra.toggled.connect(refresh)
    refresh()
    actions = W.QHBoxLayout()
    layout.addLayout(actions)
    copy = W.QPushButton(t("Copy report", "Bericht kopieren"))
    def copy_text():
        QGuiApplication.clipboard().setText(preview.toPlainText())
        status.setText(t("Copied. Paste the text into your forum post.", "Kopiert. Du kannst den Text jetzt in deinen Forumsbeitrag einfügen."))
    copy.clicked.connect(copy_text)
    forum = W.QPushButton(t("Open forum", "Forum öffnen"))
    forum.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DISCUSSIONS)))
    close = W.QPushButton(t("Close", "Schließen"))
    close.clicked.connect(dialog.accept)
    for button in (copy, forum, close):
        actions.addWidget(button)
    dialog.exec()
