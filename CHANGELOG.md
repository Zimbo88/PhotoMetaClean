# Changelog / Änderungsprotokoll

## 0.9.1 · 2026-11-26

- Die JPEG-Bereinigung unterstützt zusätzlich getestete Android- und Apple-Gain-Maps. Bei diesen Dateien bleiben Bildpositionen, Mehrbildindex und Helligkeitsbild bytegenau erhalten. Die Ergebnisliste erklärt, wenn sich der Aufbau nicht sicher prüfen lässt.
- Eine bereits vorhandene Warnung zu alten IPTC-Daten darf bei der gezielten Korrektur einer einzelnen, unsignierten XMP-Quellenangabe bestehen bleiben. Die App zeigt die Warnung auch nach der Korrektur an.
- The JPEG export now supports tested Android and Apple gain-map layouts. An existing IPTC digest warning can remain visible after a verified edit of a single unsigned XMP source label. The results explain unsupported HDR layouts and outstanding metadata warnings.

## 0.9.0 · 2026-11-26

- Der Sorglos-Modus erstellt einen vollständigen Kundenordner mit geprüften Korrekturen, unveränderten Dateien und der ursprünglichen Ordnerstruktur. Private Protokolle haben einen eigenen Ordner. Nach einem Abbruch bleibt der unvollständige Stand dort zur Prüfung.
- Das Hauptfenster passt sich an schmale und breite Bildschirme an. Deutsch und Englisch, heller und dunkler Modus sowie ein neues blau-weißes Symbol stehen in allen Desktop-Paketen bereit.
- The default export creates a complete customer folder. Verified edits, unchanged files and empty folders keep their original layout. Logs and interrupted exports stay in a separate folder. The desktop layout adapts to the window, with German and English labels, light and dark themes and a new blue-and-white icon.

## 0.8.0 · 2026-11-26

- Auf Wunsch lassen sich gespeicherte Bearbeitungsschritte, bekannte Camera-Raw-Einstellungen und Namen von Bildbearbeitungsprogrammen aus den Kopien entfernen. Die Option ist beim ersten Start ausgeschaltet. [Unterstützte Angaben und Grenzen](docs/editing-history.md)
- Optional editing history removal for delivery copies, with independent switches for JPEG credentials and generator settings. Each supported edit is checked after saving. [Supported records and formats](docs/editing-history.md#english)

## 0.7.0 · 2026-11-26

- JPEG-Export für gewöhnliche Bilder und unterstützte HDR-JPEGs. Erkannte KI-Angaben werden aus der Kopie entfernt. Die App prüft Bildströme und Gain Map und bewahrt frühere Metadaten im privaten Protokoll auf.
- JPEG export for ordinary and supported HDR images. The app verifies compressed scans and the gain map and archives previous metadata separately. [JPEG / HDR](docs/jpeg-export.md)

## 0.6.0 · 2026-11-26

- Der Ordnerpatch entfernt erkannte, unsignierte Werkzeugeinstellungen und prüft die gespeicherte Kopie erneut. Die Liste zeigt entfernte Felder und verbleibende Hinweise.
- Ein kopierbarer Kurzbericht hilft beim Melden einer weiterhin sichtbaren KI-Kennzeichnung im öffentlichen Projektforum. Die Vorschau enthält ausgewählte technische Angaben, auch bei einem Bild ohne bekannte Marker.
- The folder patch removes supported unsigned tool settings and reads back each edited copy. Results show the fields removed and remaining indicators.
- A previewable report for GitHub Discussions helps investigate persistent platform labels, including cases with no recognized marker. [Marker / indicators](docs/marker.md)

## 0.5.0 · 2026-11-26

- Beim ersten Klick können bestätigte Kameraaufnahmen mit einer falschen, unsignierten KI-Angabe korrigiert werden. Jede Bildzeile nennt die Änderung oder den Grund für die unveränderte Kopie. Private Fotodaten bleiben standardmäßig erhalten.
- The first click can correct a false unsigned AI label on verified camera photos. Each row shows the change or the reason for copying unchanged. Personal photo details are kept by default.

## 0.4.1 · 2026-11-26

- Ein Klick auf **Ordner patchen** liest, prüft und schreibt den Ordner. Freigegebene Regeln, gewählter Zielordner und getrennte Wiederholungsläufe werden berücksichtigt. Die Ausgabe funktioniert auch auf exFAT ohne Hardlinks.
- **Patch folder** now inspects, verifies and writes in a single run. It honors approved rules and the output folder, keeps repeated runs separate and supports exFAT publication without hard links.

## 0.4.0 · 2026-11-26

- Ganze Ordner mit geprüften 1:1-Kopien einschließlich RAW und Sidecars spiegeln oder ausschließlich geänderte Bilder ausgeben. Firefly-Füllungen in Retuschierbereichen anzeigen. / Mirror entire folders with verified byte-for-byte copies or export edits only. Identify Firefly fill methods in retouch-area records.
- Ordner direkt nach Patch verarbeiten, passende Felder pro Bild auswählen und Gründe für übersprungene Bilder sehen. Neues App-Symbol und zweisprachige Projektinfo.
- Added a guided Patch folder workflow, per-image field selection, Adobe processing and IPTC AI findings, desktop icons, and About on all platforms.
- Optionale Windows-Signierung mit Zeitstempel und Prüfung. / Optional Windows signing with timestamp and verification.

## 0.3.1 · 2026-11-26

- Die Desktop-App führt mit verständlichen Feldnamen durch Analyse, Vorschau und Speichern. Ein Klick wählt alle erfolgreich geprüften Bilder aus. „Kopien anzeigen“ öffnet den Ausgabeordner.
- The desktop app guides users through analysis, preview and saving. One click selects all eligible previews. “Show copies” opens the output folder.
- Zusätzliches Linux-Paket zum Entpacken und Starten per Doppelklick, auch ohne FUSE. / Additional portable Linux archive for double-click launch without FUSE.

## 0.3.0 — development / Entwicklung

- Große Fotos bis 1 GiB und 128 Megapixel pro Bild. Geprüfte Kopien unterstützen ausgewählte Metadaten in PNG/APNG, WebP, GIF, TIFF und einfachen HEIC/HEIF-/AVIF-Standbildern. Die Stapelverarbeitung plant große Dateien einzeln ein.
- Support for photos up to 1 GiB and 128 megapixels per image. Verified copies can clear selected fields in PNG/APNG, WebP, GIF, TIFF and supported HEIC/HEIF/AVIF stills. Large files run individually within a batch.
- Eigene Projektlizenz für private und gewerbliche Nutzung mit kostenfreier Weitergabe und Verkaufsverbot. / Project license allowing private and commercial use and free redistribution, with a prohibition on selling the software.

## 0.2.0 — development / Entwicklung

- Bilingual provenance findings in the desktop and CLI, with local sidecar analysis, declared action interpretation and separate asset-binding and trust results.
- Zweisprachiger Herkunftsbefund in GUI und CLI mit lokaler Sidecar-Prüfung und verständlichen Angaben zu Bearbeitung, Dateibindung und Zertifikatsvertrauen.
- Fixed-size edits of primary metadata in supported MPF/ISO HDR JPEGs. All auxiliary image bytes and pixel hashes are verified.
- Erweiterte Korrektur einfacher XMP-Quellentypen, einschließlich Textelementen und RDF-Ressourcenverweisen. Unsichere Zuordnungen und erkannte Herkunftsverweise sperren die Änderung.

## 0.1.0 — development / Entwicklung

- Local metadata inspection, export comparison and reviewed JPEG corrections.
- Lokale Metadatenanalyse, Exportvergleich und geprüfte JPEG-Korrekturen.
- Bilingual Qt interface and reproducible private before/after research reports.
- Zweisprachige Qt-Oberfläche und reproduzierbare private Vorher-Nachher-Berichte.
