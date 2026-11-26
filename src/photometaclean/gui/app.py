"""Bilingual local desktop client for PhotoMetaClean."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
import time

from PySide6 import QtWidgets as W
from PySide6.QtCore import Qt, QSettings, QTimer, QLocale, QUrl, QStandardPaths
from PySide6.QtGui import QGuiApplication, QDesktopServices, QIcon

from photometaclean import __version__
from photometaclean.core.publish import publish_new
from photometaclean.core.options import edit_options, has_generated_label
from photometaclean.core.review import FIELDS, destination_path
from photometaclean.metadata.findings import explain
from photometaclean.metadata.editing import LABELS
from photometaclean.metadata.generators import has_generator_record
from photometaclean.formats.recipes import RECIPE_FIELDS
from photometaclean.core.delivery import new_delivery, private_folder
from photometaclean.formats.history import HISTORY
from photometaclean.formats.share import EXPORT
from .appearance import VerticalScrollArea, apply_theme, card, heading
from .feedback import show_feedback
from .jobs import Batch


FIELD_LABELS = dict([
    ('JPEG:Comment', ('JPEG comment', 'JPEG-Kommentar')),
    ('PNG:Comment', ('PNG comment', 'PNG-Kommentar')),
    ('GIF:Comment', ('GIF comment', 'GIF-Kommentar')),
    ('TIFF:ImageDescription', ('TIFF image description', 'TIFF-Bildbeschreibung')),
    ('XMP-exif:GPSLatitude', ('Latitude in XMP', 'Breitengrad im XMP')),
    ('XMP-exif:GPSLongitude', ('Longitude in XMP', 'Längengrad im XMP')),
    ('XMP-aux:SerialNumber', ('Camera serial number in XMP', 'Kamera-Seriennummer im XMP')),
    ('XMP-aux:LensSerialNumber', ('Lens serial number in XMP', 'Objektiv-Seriennummer im XMP')),
    ('XMP-iptcExt:DigitalSourceType', ('Wrong label about how the picture was made', 'Falsche Angabe zur Bildherkunft')),
])


FIELD_LABELS.update({
    HISTORY: ("Editing history", "Bearbeitungsverlauf"),
    EXPORT: ("AI metadata in JPEG", "KI-Metadaten im JPEG"),
    "PNG:Software": ("Generator software in PNG", "Generatorname im PNG"),
    "PNG:Parameters": LABELS["sd_parameters"], "PNG:Prompt": LABELS["comfy_prompt"],
    "PNG:Workflow": LABELS["comfy_workflow"], "PNG:Invokeai_metadata": LABELS["invoke_metadata"],
    "PNG:Invokeai_workflow": LABELS["invoke_workflow"],
    "XMP-aux:EnhanceDenoiseVersion": ("Denoise settings version", "Versionsangabe zum Entrauschen"),
    "XMP-aux:EnhanceDenoiseLumaAmount": ("Denoise strength", "Stärke der Rauschreduzierung"),
    "XMP-aux:EnhanceDetailsVersion": ("Raw Details settings version", "Versionsangabe für Raw-Details"),
    "XMP-aux:EnhanceSuperResolutionVersion": ("Super Resolution settings version", "Versionsangabe für Super-Auflösung"),
    "XMP-aux:EnhanceSuperResolutionScale": ("Super Resolution scale", "Vergrößerungsfaktor für Super-Auflösung"),
    "XMP-iptcExt:AIPromptInformation": LABELS["prompt"],
})

PROJECT_URL = "https://github.com/Zimbo88/PhotoMetaClean"
ICON = Path(__file__).with_name("photometaclean.svg")
REASONS = {
    "Existing provenance protects this history / Herkunftsnachweis schützt diesen Verlauf":
        ("A provenance record protects this editing history", "Ein Herkunftsnachweis schützt diesen Bearbeitungsverlauf"),
    "provenance": ("Origin record found · double-click to inspect", "Herkunftseintrag gefunden · Doppelklick zeigt den Inhalt"),
    "format": ("This file type can only be copied", "Diesen Dateityp kann die App nur kopieren"),
    "unverified": ("Could not verify this picture", "Dieses Bild ließ sich nicht sicher prüfen"),
    "no_rule": ("Only optional fields found", "Nur freiwillig änderbare Fotodaten gefunden"),
    "other_source": ("A different source label was found", "Andere Angabe zur Bildherkunft gefunden"),
    "unconfirmed": ("Camera origin needs confirmation", "Bitte zuerst die Kameraaufnahme bestätigen"),
    "generator_review": ("Image tool also recorded · check original", "Auch ein Bildwerkzeug ist eingetragen · Original prüfen"),
    "approval_changed": ("File changed since approval", "Datei seit der Freigabe geändert"),
    "absent": ("No editable label found", "Keinen korrigierbaren Eintrag gefunden"),
}

POSTCHECK = {
    "clear": ("Copy checked · no supported indicators found", "Kopie geprüft · keine bekannten Hinweise mehr gefunden"),
    "remaining": ("Copy checked · other records remain", "Kopie geprüft · weitere Hinweise vorhanden"),
    "incomplete": ("Saved copy needs checking", "Gespeicherte Kopie bitte prüfen"),
}


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class Window(W.QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("PhotoMetaClean", "Desktop")
        self.de = self.settings.value("language", QLocale.system().name()[:2]) == "de"
        self.inputs = []
        self.output = None
        self.chosen_output = None
        self.cache = TemporaryDirectory()
        self.job = None
        self.review_rows = []
        self.candidates = {}
        self.scan_complete = False
        self.edit_after_scan = False
        self.patch_report = None
        self.setWindowIcon(QIcon(str(ICON)))
        self.setAcceptDrops(True)
        self.setWindowTitle("PhotoMetaClean")
        self.resize(1250, 780)
        self.build()

    def t(self, en, de):
        return de if self.de else en

    def build(self):
        scroll = VerticalScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(W.QFrame.Shape.NoFrame)
        panel = W.QWidget()
        panel.setObjectName("surface")
        scroll.setWidget(panel)
        self.setCentralWidget(scroll)
        outer = W.QVBoxLayout(panel)
        outer.setContentsMargins(16, 12, 16, 16)
        outer.setSpacing(12)
        header = W.QHBoxLayout()
        emblem = W.QLabel()
        emblem.setPixmap(self.windowIcon().pixmap(36, 36))
        header.addWidget(emblem)
        title = W.QLabel("PhotoMetaClean")
        title.setObjectName("brand")
        header.addWidget(title)
        header.addStretch()
        outer.addLayout(header)
        self.columns = W.QBoxLayout(W.QBoxLayout.Direction.LeftToRight)
        self.columns.setSpacing(12)
        outer.addLayout(self.columns, 1)
        self.setup_card, layout = card()
        results_card, results = card()
        self.columns.addWidget(self.setup_card)
        self.columns.addWidget(results_card, 1)
        heading(self.t("Source folder", "Quellordner"), layout)
        top = W.QGridLayout()
        layout.addLayout(top)

        def button(row, en, de, slot):
            widget = W.QPushButton(self.t(en, de))
            widget.clicked.connect(slot)
            row.addWidget(widget)
            return widget

        self.controls = []
        for en, de, slot, r, c in [
            ("Add files", "Dateien hinzufügen", self.files, 0, 1),
            ("Choose folder", "Ordner wählen", self.folder, 0, 0),
            ("Clear selection", "Auswahl leeren", self.clear_inputs, 1, 1),
            ("Choose output", "Ausgabeort wählen", self.pick_output, 1, 0),
        ]:
            widget = W.QPushButton(self.t(en, de))
            widget.clicked.connect(slot)
            top.addWidget(widget, r, c)
            self.controls.append(widget)
        self.controls.append(button(header, "Settings", "Einstellungen", self.preferences))
        self.about_button = button(header, "About", "Info", self.about)
        self.sources = W.QLabel()
        self.sources.setWordWrap(True)
        layout.addWidget(self.sources)
        self.show_inputs()
        heading(self.t("Delivery", "Kundenordner"), layout)
        tools_panel = W.QWidget()
        row = W.QGridLayout(tools_panel)
        row.setDefaultPositioning(2, Qt.Orientation.Horizontal)
        row.setContentsMargins(0, 0, 0, 0)
        self.mode = W.QComboBox()
        for key, en, de in [
            ("analyze","Analysis","Analyse"), ("compare","Compare","Vergleich"),
            ("photo","Photographer","Fotografenmodus"), ("privacy","Privacy","Datenschutz"),
            ("custom","Custom","Benutzerdefiniert"),
        ]:
            self.mode.addItem(self.t(en,de), key)
        row.addWidget(self.mode)
        self.recursive = W.QCheckBox(self.t("Include subfolders","Unterordner einbeziehen"))
        self.recursive.setChecked(True)
        row.addWidget(self.recursive)
        self.controls += [self.mode, self.recursive]
        self.start_button = button(row, "Start", "Starten", self.start)
        self.controls.append(self.start_button)
        self.edit_button = button(row, "Edit images…", "Bilder bearbeiten…", self.edit_images)
        self.controls.append(self.edit_button)
        modes = W.QVBoxLayout()
        self.full_folder = W.QRadioButton(self.t("Complete customer folder", "Sorglos · kompletter Kundenordner"))
        self.only_changed = W.QRadioButton(self.t("Only changed files", "Nur geänderte Dateien"))
        group = W.QButtonGroup(self)
        for option in (self.full_folder, self.only_changed):
            group.addButton(option)
            modes.addWidget(option)
        self.full_folder.setChecked(True)
        layout.addLayout(modes)
        explanation = W.QLabel(self.t(
            "Patch contains corrected copies and all other source files in their original folders. Logs are kept separately.",
            "In Patch liegen korrigierte Kopien und alle übrigen Quelldateien in ihren ursprünglichen Unterordnern. Die Protokolle liegen daneben."))
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.full_folder.toggled.connect(explanation.setVisible)
        patch_options = W.QGridLayout()
        patch_options.setDefaultPositioning(2, Qt.Orientation.Horizontal)
        layout.addLayout(patch_options)
        heading(self.t("Remove from copies", "Aus Kopien entfernen"), layout)
        self.camera_patch = W.QCheckBox(self.t(
            "AI records and credentials in JPEGs",
            "KI-Angaben und Nachweise in JPEGs"))
        self.camera_patch.setChecked(self.settings.value("camera_patch", True, type=bool))
        layout.addWidget(self.camera_patch)
        self.history = W.QCheckBox(self.t("Also remove editing history from copies",
                                           "Auch den Bearbeitungsverlauf aus Kopien entfernen"))
        self.history.setToolTip(self.t(
            "Clears supported editing steps, Camera Raw adjustments and editor names.",
            "Entfernt bekannte Bearbeitungsschritte, Camera-Raw-Einstellungen und Namen von Bildbearbeitungsprogrammen."))
        self.history.setChecked(self.settings.value("editing_history", False, type=bool))
        self.history.toggled.connect(lambda value: self.settings.setValue("editing_history", value))
        layout.addWidget(self.history)
        self.controls.append(self.history)
        self.recipes = W.QCheckBox(self.t("Also clear supported unsigned tool settings", "Weitere unsignierte Werkzeugeinstellungen entfernen"))
        self.recipes.setChecked(self.settings.value("recipes", True, type=bool))
        self.recipes.toggled.connect(lambda value: self.settings.setValue("recipes", value))
        layout.addWidget(self.recipes)
        self.controls.append(self.recipes)
        self.patch_description = W.QLabel()
        self.patch_description.setWordWrap(True)
        layout.addWidget(self.patch_description)
        self.patch_button = button(patch_options, "Patch folder", "Ordner patchen", self.patch_folder)
        font = self.patch_button.font()
        font.setBold(True)
        self.patch_button.setFont(font)
        self.controls.append(self.patch_button)
        self.rules_button = button(layout, "Optional personal details…", "Private Angaben auswählen…", self.patch_rules)
        self.controls.append(self.rules_button)
        self.patch_button.setObjectName("primary")
        self.controls += [self.full_folder, self.only_changed, self.camera_patch]
        self.camera_patch.toggled.connect(self.show_patch_options)
        self.history.toggled.connect(lambda _: self.show_patch_options())
        self.show_patch_options()
        self.more_tools = W.QCheckBox(self.t("More tools and picture details", "Weitere Werkzeuge und Bilddetails"))
        layout.addStretch()
        heading(self.t("Results", "Ergebnisse"), results)
        results.addWidget(self.more_tools)
        results.addWidget(tools_panel)
        tools_panel.hide()
        self.more_tools.toggled.connect(tools_panel.setVisible)
        self.only_changed.toggled.connect(self.invalidate_scan)
        self.recursive.toggled.connect(self.invalidate_scan)
        self.cancel = button(patch_options, "Cancel", "Abbrechen", self.cancel_job)
        self.cancel.setEnabled(False)
        self.export_button = button(row, "Export report", "Bericht exportieren", self.export)
        self.controls.append(self.export_button)
        self.hint = W.QLabel()
        self.hint.setWordWrap(True)
        results.addWidget(self.hint)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.bar = W.QProgressBar()
        self.bar.setTextVisible(False)
        self.percent = W.QLabel()
        progress_row = W.QHBoxLayout()
        progress_row.addWidget(self.bar, 1)
        progress_row.addWidget(self.percent)
        results.addLayout(progress_row)
        self.stats = W.QLabel()
        self.stats.setWordWrap(True)
        results.addWidget(self.stats)
        self.current = W.QLabel()
        self.current.setWordWrap(True)
        self.current.setTextFormat(Qt.TextFormat.PlainText)
        results.addWidget(self.current)
        for item in (self.bar, self.percent, self.stats, self.current):
            item.hide()
        self.table = W.QTableWidget(0,9)
        self.table.setHorizontalHeaderLabels([self.t(*pair) for pair in [
            ("File","Datei"),("Format","Format"),("Size","Größe"),("Metadata","Metadaten"),
            ("Provenance","Herkunft"),("Signature","Signatur"),("Action","Aktion"),
            ("Result","Ergebnis"),("Picture checked","Bild geprüft")]])
        self.table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 155)
        self.table.setColumnWidth(6, 195)
        self.table.setColumnWidth(7, 175)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(180)
        self.table.cellDoubleClicked.connect(self.detail)
        results.addWidget(self.table, 1)
        actions = W.QGridLayout()
        actions.setDefaultPositioning(2, Qt.Orientation.Horizontal)
        results.addLayout(actions)
        self.select_button = button(actions, "Select all reviewed files", "Alle geprüften auswählen", self.select_reviewed)
        self.apply_button = button(actions, "Save selected copies…", "Ausgewählte Kopien speichern…", self.apply)
        self.feedback_button = button(actions, "Report an AI label…", "KI-Hinweis melden…", self.feedback)
        self.open_button = button(actions, "Show copies", "Kopien anzeigen", self.open_copies)
        self.open_button.setEnabled(False)
        self.logs_button = button(actions, "Open private logs", "Private Protokolle öffnen", self.open_logs)
        self.logs_button.setEnabled(False)
        self.footer = actions
        self.footer_buttons = (self.select_button, self.apply_button, self.feedback_button, self.open_button, self.logs_button)
        self.footer_columns = None

        def advanced(show):
            self.select_button.setVisible(show)
            self.apply_button.setVisible(show)
            for column in (1, 2, 3, 5, 8):
                self.table.setColumnHidden(column, not show)
        advanced(False)
        self.more_tools.toggled.connect(advanced)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.mode_changed()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.progress)
        for label in (self.sources, explanation, self.patch_description, self.current, self.stats):
            label.setObjectName("secondary")
        self.hint.setTextFormat(Qt.TextFormat.PlainText)
        self.hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.resize_layout()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.theme)
        self.theme()

    def resize_layout(self):
        compact = self.width() < 1020
        direction = W.QBoxLayout.Direction.TopToBottom if compact else W.QBoxLayout.Direction.LeftToRight
        self.columns.setDirection(direction)
        self.setup_card.setMaximumWidth(16777215 if compact else max(410, self.setup_card.minimumSizeHint().width()))
        columns = 1 if self.width() < 820 else 2
        if self.footer_columns != columns:
            for index, widget in enumerate(self.footer_buttons):
                self.footer.removeWidget(widget)
                self.footer.addWidget(widget, index // columns, index % columns)
            self.footer_columns = columns

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "columns"):
            self.resize_layout()

    def mode_changed(self):
        self.patch_report = None
        messages = {
            "compare": ("Add two files or two folders in order. Folder comparisons use relative paths.",
                        "Zwei Dateien oder Ordner in Reihenfolge hinzufügen. Ordner werden anhand relativer Pfade verglichen."),
            "analyze": ("Drop files or folders here. Double-click a result for metadata and provenance.",
                        "Dateien oder Ordner hier ablegen. Doppelklick öffnet Metadaten und Herkunftsangaben."),
        }
        self.hint.setText(self.t(*messages.get(self.mode.currentData(), (
            "Preview changes, inspect details, then select the rows to approve.",
            "Änderungen vorab prüfen und anschließend die freizugebenden Zeilen auswählen."))))
        label = {"analyze": ("Analyze images", "Bilder analysieren"),
                 "compare": ("Compare images", "Bilder vergleichen")}.get(self.mode.currentData(),
                                                                           ("Preview changes…", "Vorschau anzeigen…"))
        self.start_button.setText(self.t(*label))
        self.edit_button.setVisible(self.mode.currentData() == "analyze")
        self.review_rows.clear()
        self.selection_changed()

    def invalidate_scan(self):
        self.patch_report = None
        self.scan_complete = False
        self.review_rows.clear()
        self.selection_changed()

    def about(self):
        dialog = W.QDialog(self)
        dialog.setWindowTitle(self.t("About PhotoMetaClean", "Über PhotoMetaClean"))
        layout = W.QVBoxLayout(dialog)
        logo = W.QLabel()
        logo.setPixmap(self.windowIcon().pixmap(96, 96))
        layout.addWidget(logo)
        layout.addWidget(W.QLabel(f"<h2>PhotoMetaClean {__version__}</h2>"))
        for text in (self.t("Inspect photo metadata locally and save verified, edited copies.",
                            "Bildmetadaten lokal untersuchen und geprüfte Kopien speichern."),
                     self.t("Free for private and commercial use. The license prohibits selling the software.",
                            "Kostenlos für private und gewerbliche Nutzung. Die Lizenz untersagt den Verkauf der Software."),
                     "© 2026 Mathias Zimmermann"):
            label = W.QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)
        link = W.QLabel(f'<a href="{PROJECT_URL}">GitHub · Zimbo88/PhotoMetaClean</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)
        close = W.QPushButton(self.t("Close", "Schließen"))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def patch_folder(self):
        folder = self.inputs[0] if len(self.inputs) == 1 and self.inputs[0].is_dir() else None
        if folder is None:
            choice = W.QFileDialog.getExistingDirectory(self, self.t("Choose the source folder", "Quellordner auswählen"))
            if not choice:
                return
            folder = Path(choice)
        if folder.is_symlink():
            self.message(self.t("Choose a regular source folder.", "Einen regulären Quellordner wählen."))
            return
        folder = folder.resolve()
        parent = self.chosen_output or folder
        try:
            if any(private_folder(p) for p in (folder, *folder.parents)):
                raise ValueError(self.t("Choose your photos folder.", "Bitte den Fotoordner wählen."))
            if self.chosen_output is None:
                try:
                    destination_path(parent / "Patch" / ".photometaclean-output-check")
                except ValueError:
                    pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
                    parent = Path(pictures) / "PhotoMetaClean" / folder.name
            logs = new_delivery(parent)
            report = logs.directory / "Durchlauf.jsonl"
            report.touch(mode=0o600, exist_ok=False)
        except (OSError, ValueError) as exc:
            self.message(str(exc))
            return
        approved = {}
        was_review = self.job is not None and self.job.task == "review"
        if was_review:
            for index in self.table.selectionModel().selectedRows():
                if index.row() in self.review_rows:
                    rec = self.read_row(index.row())
                    approved[Path(rec["path"]).resolve()] = rec["data"]
        self.inputs = [folder]
        self.output = logs.output
        self.mode.setCurrentIndex(self.mode.findData("analyze"))
        self.recursive.setChecked(True)
        self.patch_report = report
        self.show_inputs()
        self.hint.setText(self.t("Checking files and writing copies to ", "Dateien werden geprüft und Kopien geschrieben nach ") + str(logs.output))
        confirmation = ""
        if (self.camera_patch.isChecked() or self.history.isChecked()) and not was_review:
            confirmation = self.t(
                "The user selected the disclosed metadata export for these copies.",
                "Der Nutzer hat den angezeigten Metadatenexport für diese Kopien gewählt.")
        changes = self.saved_rules()
        if confirmation and self.camera_patch.isChecked():
            changes[EXPORT] = None
        if confirmation and self.history.isChecked():
            changes[HISTORY] = None
        if self.recipes.isChecked() and not was_review:
            changes.update(dict.fromkeys(RECIPE_FIELDS))
        self.launch("patch", changes, confirmation, approved=approved,
                    exclude=logs.output, logs=logs)

    def saved_rules(self):
        configured = self.settings.value("patch_fields", [], type=list)
        return {tag: None for tag in FIELDS[:-1] if tag in configured}

    def show_patch_options(self, checked=None):
        if checked is not None:
            self.settings.setValue("camera_patch", checked)
        if self.camera_patch.isChecked():
            self.patch_button.setText(self.t("Clean copies", "Kopien bereinigen"))
            message = self.t(
                "JPEG export removes supported AI records and embedded credentials from the copy. The original and a private recovery record preserve them. Use only where you have the rights. Adobe prohibits removing Content Credentials under its generative AI terms.",
                "Der JPEG-Export entfernt unterstützte KI-Angaben und eingebettete Nachweise aus der Kopie. Original und privates Sicherungsprotokoll bewahren sie auf. Nur bei entsprechender Berechtigung nutzen. Adobe untersagt das Entfernen von Content Credentials in seinen Bedingungen für generative KI.")
        else:
            self.patch_button.setText(self.t("Patch folder", "Ordner patchen"))
            message = self.t("Source labels are kept.", "Angaben zur Bildherkunft bleiben erhalten.")
        if self.history.isChecked():
            self.patch_button.setText(self.t("Clean copies", "Kopien bereinigen"))
            message += " " + self.t("Editing history and recognized editor names will also be removed where supported.",
                                    "Die App entfernt auch den Verlauf und bekannte Programmnamen, wenn der Dateiaufbau das erlaubt.")
        rules = self.saved_rules()
        details = (self.t("Also remove ", "Zusätzlich entfernen: ")
                   + ", ".join(self.t(*FIELD_LABELS[key]) for key in rules)) if rules else self.t(
                       "Location, serial numbers and comments are kept.",
                       "Standort, Seriennummern und Kommentare bleiben erhalten.")
        self.patch_description.setText(message + " " + details)

    def patch_rules(self):
        changes, _ = self.fields("rules")
        if changes is not None:
            self.settings.setValue("patch_fields", list(changes))
            self.show_patch_options()

    def edit_images(self):
        self.patch_report = None
        self.guided_edit()

    def guided_edit(self):
        if not self.inputs:
            self.files()
        if not self.inputs:
            return
        if not self.scan_complete:
            self.edit_after_scan = True
            self.launch("analyze", {}, "")
            return
        selected = sorted(index.row() for index in self.table.selectionModel().selectedRows())
        rows = selected or self.candidates.keys()
        candidates = {self.candidates[n][0]: self.candidates[n][1:] for n in rows}
        options = {key for _, fields, _, _ in candidates.values() for key in fields}
        if not options:
            self.hint.setText(self.t("No editable fields in these images. The Action column explains why.",
                                     "Keine bearbeitbaren Felder in diesen Bildern. Den Grund zeigt die Spalte Aktion."))
            return
        changes, evidence = self.fields("guided", options)
        if changes:
            self.launch("review", changes, evidence, candidates=candidates)

    def select_reviewed(self):
        from PySide6.QtCore import QItemSelection, QItemSelectionModel
        selection = QItemSelection()
        for row in self.review_rows:
            selection.select(self.table.model().index(row, 0), self.table.model().index(row, 8))
        self.table.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def feedback(self):
        selected = self.table.selectionModel().selectedRows()
        if len(selected) == 1:
            show_feedback(self, self.read_row(selected[0].row()), self.de)

    def selection_changed(self):
        available = bool(self.review_rows) and bool(self.job) and not self.job.isRunning()
        self.select_button.setEnabled(available)
        selected = {index.row() for index in self.table.selectionModel().selectedRows()}
        self.feedback_button.setEnabled(len(selected) == 1 and bool(self.job) and self.job.task in ("analyze", "patch", "apply"))
        self.apply_button.setEnabled(available and not selected.isdisjoint(self.review_rows))

    def open_copies(self):
        if self.output and self.output.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output)))

    def open_logs(self):
        if self.job and self.job.logs:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.job.logs.directory)))

    def show_inputs(self):
        if len(self.inputs) > 1:
            inputs = self.t(f"{len(self.inputs)} selected", f"{len(self.inputs)} ausgewählt")
        else:
            inputs = str(self.inputs[0]) if self.inputs else self.t("Drop a photo folder here", "Ziehe deinen Fotoordner hierher")
        self.sources.setToolTip("\n".join(map(str, self.inputs[:10])))
        self.sources.setText(inputs + "\n" + self.t("Output location", "Ausgabeort") + " · " + str(
            self.chosen_output or self.t("Inside the photo folder", "Im Fotoordner")))
        self.sources.setTextFormat(Qt.TextFormat.PlainText)

    def add(self, paths):
        if self.job and self.job.isRunning():
            return
        self.invalidate_scan()
        self.inputs = list(dict.fromkeys([*self.inputs, *(Path(p).absolute() for p in paths if p)]))
        self.show_inputs()
        self.review_rows.clear()
        self.selection_changed()

    def clear_inputs(self):
        self.inputs.clear()
        self.add([])

    def files(self):
        self.add(W.QFileDialog.getOpenFileNames(self)[0])

    def folder(self):
        self.add([W.QFileDialog.getExistingDirectory(self)])

    def pick_output(self):
        value = W.QFileDialog.getExistingDirectory(self)
        if value:
            try:
                destination_path(Path(value) / ".photometaclean-output-check")
            except (ValueError, OSError) as exc:
                self.message(str(exc))
                return
            if self.patch_report:
                self.invalidate_scan()
            self.output = Path(value).resolve()
            self.chosen_output = self.output
            self.show_inputs()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.add([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])

    def theme(self, *_):
        apply_theme(self)

    def preferences(self):
        dialog = W.QDialog(self)
        dialog.setWindowTitle(self.t("Settings","Einstellungen"))
        form = W.QFormLayout(dialog)
        language = W.QComboBox()
        language.addItems(["English","Deutsch"])
        language.setCurrentIndex(int(self.de))
        form.addRow(self.t("Language (after restart)","Sprache (nach Neustart)"),language)
        theme = W.QComboBox()
        themes = ["system","light","dark"]
        theme.addItems(["System",self.t("Light","Hell"),self.t("Dark","Dunkel")])
        theme.setCurrentIndex(themes.index(self.settings.value("theme","system")))
        form.addRow(self.t("Appearance","Darstellung"),theme)
        workers = W.QSpinBox()
        workers.setRange(1,32)
        workers.setValue(self.workers())
        form.addRow(self.t("Parallel files","Parallele Dateien"),workers)
        self.buttons(dialog,form)
        if dialog.exec():
            self.settings.setValue("language",["en","de"][language.currentIndex()])
            self.settings.setValue("workers",workers.value())
            self.settings.setValue("theme",themes[theme.currentIndex()])
            self.theme()

    def workers(self):
        return max(1,min(32,int(self.settings.value("workers",2))))

    def buttons(self, dialog, layout):
        box = W.QDialogButtonBox(W.QDialogButtonBox.StandardButton.Ok | W.QDialogButtonBox.StandardButton.Cancel)
        box.button(W.QDialogButtonBox.StandardButton.Cancel).setText(self.t("Cancel","Abbrechen"))
        box.accepted.connect(dialog.accept)
        box.rejected.connect(dialog.reject)
        layout.addWidget(box)

    def message(self, text):
        W.QMessageBox.information(self, "PhotoMetaClean", text)

    def fields(self, mode, options=None):
        dialog = W.QDialog(self)
        rules = mode == "rules"
        dialog.setWindowTitle(self.t("Patch rules", "Patch-Regeln") if rules else self.t("Preview correction","Korrektur vorschauen"))
        form = W.QVBoxLayout(dialog)
        form.addWidget(W.QLabel(self.t("Clear the selected fields at the specified storage locations.",
                                       "Ausgewählte Felder an den angegebenen Speicherorten leeren.")))
        if rules:
            form.addWidget(W.QLabel(self.t("Clear the checked fields on future folder runs. Leave all unchecked to keep personal details.",
                                           "Diese Felder bei künftigen Ordnerläufen leeren. Ohne Auswahl bleiben persönliche Angaben erhalten.")))
        tags = FIELDS[-1:] if mode == "photo" else FIELDS[:-1] if mode in ("privacy", "rules") else (*FIELDS, *sorted(RECIPE_FIELDS))
        if options is not None:
            tags = [tag for tag in tags if tag in options]
        boxes = {}
        for tag in tags:
            box = W.QCheckBox(self.t(*FIELD_LABELS[tag]))
            box.setToolTip(tag)
            box.setObjectName(tag)
            if rules:
                box.setChecked(tag in self.saved_rules())
            boxes[tag] = box
            form.addWidget(box)
        if mode == "photo" or (options is not None and len(tags) == 1 and tags[0] != FIELDS[-1]):
            boxes[tags[0]].setChecked(True)
        if any(tag.startswith(("XMP-exif:", "XMP-aux:")) for tag in tags):
            note = W.QLabel(self.t("GPS and serial number options cover XMP only. EXIF and camera MakerNotes are preserved.",
                                   "GPS- und Seriennummernoptionen betreffen nur XMP. EXIF und Kamera-MakerNotes bleiben erhalten."))
            note.setWordWrap(True)
            form.addWidget(note)
        evidence = W.QPlainTextEdit()
        if FIELDS[-1] in tags:
            form.addWidget(W.QLabel(self.t("For a source correction, enter how you verified the original.",
                                           "Bei einer Herkunftskorrektur kurz angeben, wie du das Original geprüft hast.")))
            evidence.setPlaceholderText(self.t("For DigitalSourceType, document ownership and evidence of the incorrect declaration.",
                "Für DigitalSourceType Eigentum und Nachweis der falschen Angabe dokumentieren."))
            form.addWidget(evidence)
        self.buttons(dialog, form)
        approve = dialog.findChild(W.QDialogButtonBox).button(W.QDialogButtonBox.StandardButton.Ok)
        approve.setText(self.t("Show preview", "Vorschau anzeigen"))

        def ready():
            selected = {tag for tag, box in boxes.items() if box.isChecked()}
            approve.setEnabled((rules or bool(selected)) and
                               (FIELDS[-1] not in selected or bool(evidence.toPlainText().strip())))
            if rules:
                approve.setText(self.t("Save rules", "Regeln speichern"))

        for box in boxes.values():
            box.toggled.connect(ready)
        evidence.textChanged.connect(ready)
        ready()
        if dialog.exec():
            return {tag: None for tag, box in boxes.items() if box.isChecked()}, evidence.toPlainText()
        return None, ""

    def start(self):
        self.patch_report = None
        mode = self.mode.currentData()
        if not self.inputs or (mode == "compare" and len(self.inputs) != 2):
            self.message(self.hint.text())
            return
        changes, evidence = {}, ""
        if mode not in ("analyze","compare"):
            changes, evidence = self.fields(mode)
            if not changes:
                return
            mode = "review"
        self.launch(mode, changes, evidence)

    def apply(self):
        selected = {}
        for index in self.table.selectionModel().selectedRows():
            rec = self.read_row(index.row())
            if rec.get("task") == "review" and "data" in rec:
                selected[Path(rec["path"])] = rec["data"], Path(rec["relative"])
        if not selected:
            self.message(self.t("Select reviewed rows first.","Zuerst geprüfte Zeilen auswählen."))
            return
        if self.output is None:
            self.pick_output()
        if self.output is None:
            return
        targets = [self.output / rel for _, rel in selected.values()]
        try:
            for target in targets:
                destination_path(target)
            if len(set(targets)) != len(targets):
                raise ValueError(self.t("Duplicate output paths","Doppelte Ausgabepfade"))
        except (OSError, ValueError) as exc:
            self.message(str(exc))
            return
        answer = W.QMessageBox.question(self,"PhotoMetaClean", self.t("Apply reviewed changes to new files?",
            "Geprüfte Änderungen auf neue Dateien anwenden?") + f"\n{len(selected)} → {self.output}")
        if answer == W.QMessageBox.StandardButton.Yes:
            self.launch("apply", {}, "", selected)

    def launch(self, task, changes, evidence, approved=None, candidates=None, exclude=None, logs=None):
        self.scan_complete = False
        self.candidates.clear()
        self.review_rows.clear()
        self.select_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.logs_button.setEnabled(False)
        self.table.setRowCount(0)
        for item in (self.bar, self.percent, self.stats, self.current):
            item.show()
        self.cache.cleanup()
        self.cache = TemporaryDirectory()
        self.counts = dict(found=0, done=0, flagged=0, unchanged=0, corrected=0, skipped=0, errors=0, size=0)
        self.started = time.monotonic()
        self.job = Batch(task, self.inputs.copy(), self.recursive.isChecked(), logs.work if logs else self.output,
                         self.workers(), changes, evidence, approved, candidates,
                         mirror=task == "patch" and not self.only_changed.isChecked(), exclude=exclude, logs=logs)
        self.job.total.connect(lambda n: self.counts.update(found=n))
        self.job.current.connect(self.show_current)
        self.job.result.connect(self.add_row)
        self.batch_error = ""
        self.job.failed.connect(self.batch_failed)
        self.job.finished.connect(self.finished)
        for widget in self.controls + [self.apply_button]:
            widget.setEnabled(False)
        self.cancel.setEnabled(True)
        self.job.start()
        self.timer.start(250)
        self.progress()

    def cancel_job(self):
        self.job.stop.set()
        self.current.setText(self.t("Finishing active files…","Laufende Dateien werden abgeschlossen…"))
        self.cancel.setEnabled(False)

    def batch_failed(self, error):
        self.batch_error = error
        self.message(error)

    def finished(self):
        self.timer.stop()
        self.current.setText(self.t("Cancelled","Abgebrochen") if self.job.stop.is_set() else self.t("Finished","Abgeschlossen"))
        for widget in self.controls:
            widget.setEnabled(True)
        self.cancel.setEnabled(False)
        self.scan_complete = self.job.task == "analyze" and not self.job.stop.is_set() and self.counts["done"] == self.counts["found"]
        if self.scan_complete:
            number = sum(bool(fields) for _, _, fields, _, _ in self.candidates.values())
            self.hint.setText(self.t(f"{number} files with editable fields. Click Edit images to choose changes.",
                                     f"{number} Bilder mit bearbeitbaren Feldern. Mit „Bilder bearbeiten“ Änderungen wählen.")
                              if number else self.t("No editable fields found. See the Action column.",
                                                    "Keine bearbeitbaren Felder gefunden. Gründe stehen in der Spalte Aktion."))
        if self.job.task == "review" and not self.review_rows:
            self.hint.setText(self.t("No copies ready. Check the reason in the Result column.",
                                     "Keine Kopie freigegeben. Den Grund zeigt die Spalte Ergebnis."))
        if self.job.task == "review" and self.review_rows:
            if self.job.candidates is not None:
                self.select_reviewed()
            elif len(self.review_rows) == 1:
                self.table.selectRow(self.review_rows[0])
            self.hint.setText(self.t("Double-click to inspect a change. Select reviewed files, then save your copies.",
                                     "Doppelklick zeigt die Änderung. Geprüfte Bilder auswählen und Kopien speichern."))
        if self.job.task == "patch":
            c = self.counts
            summary = self.t(f"{c['corrected']} corrected, {c['unchanged']} copied unchanged, {c['skipped']} without a copy, {c['errors']} errors.",
                             f"{c['corrected']} korrigiert, {c['unchanged']} unverändert kopiert, {c['skipped']} ohne Kopie, {c['errors']} Fehler.")
            complete = (not self.job.stop.is_set() and not self.batch_error and not c["errors"]
                        and c["found"] == c["done"] and (not self.job.mirror or c["found"] == c["unchanged"] + c["corrected"]))
            if complete:
                try:
                    self.job.logs.finish()
                except OSError as exc:
                    self.batch_error = str(exc)
                    complete = False
            if complete:
                detail = self.t(f"Customer folder {self.output.name} is complete.", f"Kundenordner {self.output.name} ist vollständig.")
                self.open_button.setToolTip(str(self.output))
                if c["flagged"]:
                    detail += self.t(f" Review {c['flagged']} files before delivery.",
                                     f" Vor der Übergabe {c['flagged']} Dateien prüfen.")
            else:
                self.output = None
                self.current.setText(self.t("Incomplete export", "Ausgabe unvollständig"))
                detail = self.t("Incomplete export. Open private logs to see the partial copies.",
                                "Ausgabe unvollständig. Die bisherigen Kopien findest du unter „Private Protokolle öffnen“.")
                if self.batch_error:
                    detail += " · " + self.batch_error
            self.hint.setText(summary + "\n" + detail)
            self.logs_button.setToolTip(str(self.job.logs.directory))
        self.selection_changed()
        self.logs_button.setEnabled(self.job.logs is not None)
        self.open_button.setEnabled((self.job.task == "patch" and self.output is not None) or (self.job.task == "apply" and self.counts["corrected"] > 0))
        self.progress()
        follow_up = self.edit_after_scan and self.scan_complete
        self.edit_after_scan = False
        if follow_up:
            self.guided_edit()

    def show_current(self, value):
        self.current.setToolTip(value)
        self.current.setText(self.current.fontMetrics().elidedText(value, Qt.TextElideMode.ElideMiddle,
                                                                  max(240, self.table.width() - 12)))

    def progress(self):
        c = self.counts
        elapsed = max(.001,time.monotonic()-self.started)
        rate = c["done"]/elapsed
        percent = round(100*c["done"]/max(1,c["found"]))
        self.bar.setValue(percent)
        self.percent.setText(f"{percent} %")
        labels = [("found","Found","Gefunden"),("done","Processed","Untersucht"),
                  ("flagged","For review","Bitte prüfen"),("unchanged","Unchanged","Unverändert"),
                  ("corrected","Corrected","Korrigiert"),("skipped","Without a copy","Ohne Kopie"),
                  ("errors","Errors","Fehler")]
        eta = f'{max(0,c["found"]-c["done"])/rate:.0f} s' if rate else "—"
        locale = QLocale("de_DE" if self.de else "en_GB")
        self.stats.setText("   ·   ".join(f"{self.t(en,de)} {c[k]}" for k,en,de in labels)
                           + f'\n{self.t("Elapsed","Verstrichen")} {elapsed:.0f} s   ·   {self.t("Time left","Restzeit")} {eta}   ·   '
                           + f'{locale.toString(rate, "f", 2)} {self.t("files/s","Dateien/s")}   ·   {locale.toString(c["size"]/1048576, "f", 1)} MiB')

    def read_row(self,n):
        return json.loads((Path(self.cache.name)/str(n)).read_text(encoding="utf8"))

    def add_row(self,rec):
        n = self.table.rowCount()
        (Path(self.cache.name)/str(n)).write_text(pretty(rec),encoding="utf8")
        self.table.insertRow(n)
        d = rec.get("data",{})
        task = rec["task"]
        skipped = rec.get("skipped") or d.get("unmatched") or d.get("omitted")
        error = rec.get("error") or d.get("error")
        analysis = d.get("analysis", d)
        refs = analysis.get("provenance_references") or {}
        flagged = bool(analysis.get("error") or analysis.get("validation_error") or analysis.get("editing_signals") or analysis.get("warnings") or analysis.get("manifest") or refs.get("sidecars") or refs.get("xmp")
                       or any(d.get("differences",{}).values()) or analysis.get("classification",{}).get("declarations")
                       or task == "review" and not error)
        c = self.counts
        c["done"] += 1
        c["size"] += rec.get("size",0)
        c["skipped"] += int(bool(skipped))
        c["errors"] += int(bool(error and not skipped))
        postcheck = d.get("postcheck")
        c["flagged"] += int(postcheck["state"] != "clear" if postcheck else flagged)
        success = not error and not skipped
        if task == "review" and success:
            self.review_rows.append(n)
        writing = task in ("apply", "patch")
        c["corrected"] += int(success and writing and not d.get("copy_only"))
        c["unchanged"] += int(success and (not writing or bool(d.get("copy_only"))))
        provenance = "—"
        signature = d.get("preview",{}).get("signature_status","—")
        if task in ("analyze", "patch"):
            finding = explain(analysis or rec, self.t("en", "de"))
            provenance, signature = finding.headline, finding.verification
        elif self.de and signature == "no embedded manifest detected; external status unknown":
            signature = "Kein eingebettetes Manifest erkannt, externer Status offen"
        action = {"patch":self.t("Patch","Patch"),"analyze":self.t("Inspect","Prüfen"),"review":self.t("Review","Freigabe prüfen"),
                  "apply":self.t("Apply","Anwenden"),"compare":self.t("Compare","Vergleichen")}[task]
        status = self.t("Skipped","Übersprungen") if skipped else self.t("Error","Fehler") if error else self.t("OK","OK")
        if task == "analyze":
            fields, reason = edit_options(rec["path"], d or rec)
            self.candidates[n] = (Path(rec["path"]), Path(rec["relative"]), fields, reason, d.get("sha256"))
            if FIELDS[-1] in fields and has_generated_label(d):
                action = (self.t(*REASONS["generator_review"]) if has_generator_record(d)
                          else self.t("Can remove a false AI label", "Falsche KI-Angabe kann entfernt werden"))
            else:
                action = ", ".join(self.t(*FIELD_LABELS[key]) for key in fields) if fields else self.t(*REASONS[reason])
        if task == "patch" and d.get("omitted"):
            action = self.t("Checked · no copy requested for unchanged files", "Geprüft · nur geänderte Bilder zur Ausgabe gewählt")
            reason = d.get("reason")
            status = self.copy_reason(reason)
        if task == "patch" and error:
            status = str(error)
        if d.get("copy_only"):
            action = self.t("Copied unchanged", "Unverändert kopiert")
            reason = d.get("reason")
            if reason:
                status = self.copy_reason(reason)
        if writing and d.get("audit"):
            removed = list(dict.fromkeys(change["before"] if change["field"] in {EXPORT, HISTORY} else self.t(*FIELD_LABELS[change["field"]])
                                          for change in d["audit"]["changes"]))
            action = self.t("Removed ", "Entfernt: ") + ", ".join(removed)
            status = self.t(*POSTCHECK[postcheck["state"]]) if postcheck else self.t("Corrected copy saved", "Korrigierte Kopie gespeichert")
            if d.get("retained_fields"):
                kept = ", ".join(self.t(*FIELD_LABELS[key]) for key in d["retained_fields"])
                status += self.t(" · Kept for review: ", " · Zur Prüfung erhalten: ") + kept
            if postcheck:
                provenance = self.t("See original in details", "Originalangaben im Doppelklick")
        if (task in ("patch", "analyze") and analysis.get("manifest") and
                any(item["operation"] == "firefly_fill" for item in analysis.get("editing_signals", []))):
            if task == "analyze":
                action = self.t("Firefly records found · JPEG export available for review", "Firefly-Einträge gefunden · JPEG-Export prüfen")
            elif d.get("reason") == "provenance":
                status = self.t("An Adobe record documents Firefly retouching", "Adobe dokumentiert eine Firefly-Retusche")
        elif task == "review" and success:
            action = ", ".join(self.t(*FIELD_LABELS[entry["field"]]) for entry in d["preview"]["changes"])
        if skipped and error:
            if error in REASONS:
                status = self.t(*REASONS[error])
            elif any(term in error.lower() for term in ("manifest", "provenance")):
                status = self.t(*REASONS["provenance"])
            elif "missing or already blank" in error:
                status = self.t(*REASONS["absent"])
            else:
                status = self.t("Manual review", "Manuell prüfen") + " · " + str(error)
        values = [rec["relative"],analysis.get("format",Path(rec["path"]).suffix.lstrip(".").upper()),
                  str(rec.get("size",0)),str(len(analysis["metadata"])) if "metadata" in analysis else "—",
                  provenance or "—",signature,
                  action,status,self.t("Check needed", "Prüfung offen") if postcheck and postcheck["state"] == "incomplete" else self.t("Verified","Bestätigt") if writing and success else "—"]
        if self.patch_report:
            event = dict(file=rec["relative"], stage=task, result=status, action=action)
            if error:
                event["error"] = str(error)
            if "destination" in d:
                event["destination"] = d["destination"]
            if d.get("audit"):
                event["output_sha256"] = d["audit"]["output_sha256"]
            if d.get("retained_fields"):
                event["retained_fields"] = d["retained_fields"]
            if postcheck:
                event["postcheck"] = postcheck
            try:
                if writing and d.get("copy_only"):
                    event.update(source_sha256=d["source_sha256"], output_sha256=d["output_sha256"])
                with self.patch_report.open("a", encoding="utf8") as log:
                    log.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError as exc:
                self.patch_report = None
                self.cancel_job()
                self.message(str(exc))
        for i,value in enumerate(values):
            item = W.QTableWidgetItem(str(value))
            item.setToolTip(str(rec["path"] if i == 0 else value))
            self.table.setItem(n,i,item)

    def copy_reason(self, reason):
        return self.t(*REASONS.get(reason, ("Open details to see why the file was kept",
                                             "Der Grund steht im vollständigen Bericht per Doppelklick")))

    def detail(self,row,column=0):
        rec = self.read_row(row)
        dialog = W.QDialog(self)
        dialog.setWindowTitle(rec["relative"])
        dialog.resize(900,650)
        layout = W.QVBoxLayout(dialog)
        if rec.get("skipped") and ("provenance" in rec.get("error", "").lower() or "manifest" in rec.get("error", "").lower()):
            label = W.QLabel(self.t("Review the original edit history and re-export with accurate credentials.",
                                    "Bearbeitungshistorie prüfen und aus der Quelle mit zutreffenden Herkunftsangaben exportieren."))
            layout.addWidget(label)
        tabs = W.QTabWidget()
        layout.addWidget(tabs)
        data = rec.get("data",{})
        preview = data.get("preview") or data.get("audit")
        if preview:
            table = W.QTableWidget(0, 3)
            table.setHorizontalHeaderLabels([self.t("Field", "Feld"), self.t("Before", "Vorher"), self.t("After", "Nachher")])
            table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
            for entry in preview["changes"]:
                row_index = table.rowCount()
                table.insertRow(row_index)
                old = str(entry["before"])
                if entry["field"] in FIELDS[:4]:
                    old = bytes.fromhex(old).decode("utf8", errors="replace")
                for column, value in enumerate((self.t(*FIELD_LABELS[entry["field"]]), old, self.t("Cleared", "Geleert"))):
                    table.setItem(row_index, column, W.QTableWidgetItem(value))
            table.resizeColumnsToContents()
            tabs.addTab(table, self.t("Preview", "Vorschau"))
        if rec.get("task") in ("patch", "analyze"):
            finding = explain(data.get("analysis", data) or rec, self.t("en", "de"))
            view = W.QPlainTextEdit(finding.text)
            view.setReadOnly(True)
            label = self.t("Original findings", "Befund im Original") if rec["task"] == "patch" else self.t("Provenance findings", "Herkunftsbefund")
            tabs.addTab(view, label)
        if check := data.get("postcheck"):
            lines = [self.t(*POSTCHECK[check["state"]])]
            lines.extend(self.t(*LABELS[s["operation"]]) + " · " + s["field"] for s in check["signals"])
            lines.extend(str(entry["value"]) for entry in check["source_types"])
            if check["provenance"]:
                lines.append(self.t(*REASONS["provenance"]))
            if check["issue"]:
                lines.append(str(check["issue"]))
            view = W.QPlainTextEdit("\n".join(lines))
            view.setReadOnly(True)
            tabs.addTab(view, self.t("Saved copy", "Gespeicherte Kopie"))
            tabs.setCurrentWidget(view)
        for name,value in [(self.t("Changes","Änderungen"),data.get("differences",data.get("preview",data.get("audit",{})).get("changes"))),
                           (self.t("Before","Vorher"),data.get("before")), (self.t("After","Nachher"),data.get("after")),
                           (self.t("Full record","Vollständiger Bericht"),rec)]:
            if value is not None:
                view = W.QPlainTextEdit(pretty(value))
                view.setReadOnly(True)
                tabs.addTab(view,name)
        if rec.get("task") in ("analyze", "patch", "apply"):
            feedback = W.QPushButton(self.t("Still labeled as AI? Prepare a forum report…", "Weiterhin als KI markiert? Bericht fürs Forum vorbereiten…"))
            feedback.clicked.connect(lambda: show_feedback(dialog, rec, self.de))
            layout.addWidget(feedback)
        dialog.exec()

    def export(self):
        directory = self.job.logs.directory if self.job and self.job.logs else Path.cwd()
        name = W.QFileDialog.getSaveFileName(self,self.t("Export report","Bericht exportieren"),str(directory / "report.json"),"JSON (*.json)")[0]
        if not name:
            return
        tmp = None
        try:
            target = destination_path(name)
            if self.job and self.job.logs and target.resolve().is_relative_to(self.job.logs.output):
                raise ValueError(self.t("Save reports outside the customer folder.", "Berichte außerhalb des Kundenordners speichern."))
            with NamedTemporaryFile("w",dir=target.parent,delete=False,encoding="utf8") as out:
                tmp = Path(out.name)
                out.write("[")
                for n in range(self.table.rowCount()):
                    if n:
                        out.write(",\n")
                    out.write(pretty(self.read_row(n)))
                out.write("]\n")
            publish_new(tmp, target)
        except (OSError,ValueError) as exc:
            self.message(str(exc))
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)

    def closeEvent(self,event):
        if self.job and self.job.isRunning():
            self.cancel_job()
            self.job.finished.connect(self.close)
            event.ignore()
            return
        self.cache.cleanup()
        super().closeEvent(event)


def main():
    import sys
    from multiprocessing import freeze_support
    freeze_support()
    app = W.QApplication.instance() or W.QApplication(sys.argv)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(ICON)))
    if "--smoke-test" in sys.argv:
        from .smoke import exercise_patch
        return exercise_patch(app)
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
