# Vergleich bestehender Projekte / Upstream project review

Stand / reviewed 2026-11-26. Statische Stichprobe aus Standardzweig, README, Quellbaum, Lizenz und ausgewählten Implementierungspfaden. Jeder Link fixiert den untersuchten Commit. Das Datum ist sein Committerdatum. Testdateien und Herstellerangaben belegen keine erfolgreiche Ausführung auf unserem System. / Static review of default-branch snapshots, documentation, license files and selected source paths. Dates refer to the pinned commits. Test presence and platform claims are upstream evidence only.

## adrozdenko/metascrub

2026-07-08 · MIT · [Quellstand / source snapshot](https://github.com/adrozdenko/metascrub/tree/e2f87d992ca82e765f3b7afbe352a5a0c9dea9b5)

**DE** Bash, ExifTool, ImageMagick, Web UI. JPEG, PNG, WebP, HEIC, TIFF, GIF. macOS/Linux/Windows laut README. Smoke-Test mit HEIC. clean.sh unterdrückt einzelne Fehler und bietet Neukodierung als Rückfall.

**EN** Shell and web front ends. HEIC smoke fixture. Blanket stripping and fallback re-encoding prevent adoption of the write path.

## TomSkywalker/Photo-Metadata-and-Filename-Tools

2026-08-31 · Keine Lizenzdatei / no license file · [Quellstand / source snapshot](https://github.com/TomSkywalker/Photo-Metadata-and-Filename-Tools/tree/5a562d9e1a9d605625682bd688049148ddecef7b)

**DE** Interaktive Python-/ExifTool-Skripte für Namen, Datumsabgleich und Übernahme von EXIF. JPEG, HEIF, PNG, WebP u.a. Windows-Doppelklick dokumentiert. Schreibpfad nutzt overwrite_original. Keine Tests im geprüften Baum gefunden.

**EN** Interactive Python utilities synchronize names, timestamps and EXIF. Windows-oriented launch. In-place writes conflict with copy-only processing. No test suite identified.

## ibrofk/ai-metadata-cleaner

2026-08-01 · MIT · [Quellstand / source snapshot](https://github.com/ibrofk/ai-metadata-cleaner/tree/2ed5fecc4d3dfd6eea426bbbd64102d89af30e70)

**DE** Python-CLI, lokale Weboberfläche, Windows-PowerShell-Bootstrap. JPEG, TIFF, WebP, PNG, AVIF, HEIF. Separate Tests für KI- und allgemeine Bereinigung. Pillow-Speicherpfad verwendet Qualität 95.

**EN** Windows-first dependency setup. Separate AI and general cleaner tests. JPEG/WebP quality-based save paths preclude a blanket losslessness claim. Useful report design.

## GitBreak/image-metadata-toolkit

2026-08-28 · MIT (Lite) · [Quellstand / source snapshot](https://github.com/GitBreak/image-metadata-toolkit/tree/3f1af5c0b27999d037ab422570c2f9fd1c156b55)

**DE** Python/ExifTool für JPEG, PNG, WebP. CLI, macOS-Installationsbeispiel. Eigene Tests. Prüft Abmessungen und komprimierte Daten nach Ausgabe in Kopie.

**EN** Local copy workflow with compressed-data verification and a test suite. Closest integrity model. Extend verification to secondary images, MakerNotes and signed claims before adopting a write policy.

## lokeshbyte/C2PA-Tool

2026-08-01 · MIT genannt / named only · [Quellstand / source snapshot](https://github.com/lokeshbyte/C2PA-Tool/tree/9b965929f11b95d6dce13de8eae0ea1a3853de97)

**DE** Python, Pillow und C2PA-Reader. JPEG-Segmentbearbeitung, alternativ erneutes Speichern mit Pillow. Keine Plattformmatrix oder Tests belegt. LICENSE enthält nur den Lizenznamen.

**EN** Python script with a JPEG segment path and a generic re-save path. Detecting removal differs from validating a signed asset. No test suite identified. Do not copy without a complete grant.

## earthwrld/aistrip

2026-11-01 · MIT · [Quellstand / source snapshot](https://github.com/earthwrld/aistrip/tree/6c98243b43d880d49b1cb57f17aaa37876ea3d7d)

**DE** Python-CLI mit Scanner, Stapelbetrieb und separatem Cleaner. JPEG, PNG, WebP, TIFF, HEIF laut README. tests/test_aistrip.py vorhanden. JPEG-Speicherpfad setzt Qualität 95.

**EN** Python CLI with scan and batch modes. Platform support depends on codecs. Explicit JPEG re-encoding and APP11 stripping disqualify its writer.

## AlinTibi/MetaClean

2026-11-10 · MIT · [Quellstand / source snapshot](https://github.com/AlinTibi/MetaClean/tree/609be09bd6d25cb1fd3b582ce94dac83eec44ad1)

**DE** Go/Wails, TypeScript und gebündeltes ExifTool. Windows x64 mit WebView2. JPEG, PNG, TIFF, WebP, HEIF, PDF, Office nur lesend. Go- und Frontendtests. Version 1.0.1 korrigierte veraltete Ergebnisanzeigen.

**EN** Windows desktop privacy utility. Go and frontend tests. Refreshing reports from the actual output is worth adopting. Review mode can replace originals, and broad deletion needs independent integrity checks.

## exiftool/exiftool

2026-11-16 · Perl Artistic oder/or GPL (README) · [Quellstand / source snapshot](https://github.com/exiftool/exiftool/tree/3d7a0538324e9b04aa8930201b007009491321d2)

**DE** Perl-Bibliothek und CLI für JPEG, HEIF, TIFF, ARW, DNG und viele weitere Formate. Windows/macOS/Linux. Formatbezogene Perl-Tests. Herstellergruppen und unbekannte Tags sind für die Analyse besonders wertvoll.

**EN** Broad format and MakerNote support, extensive format-specific tests. Use as a local subprocess for extraction. Check diagnostics even when JSON parses. Per-format write support needs separate verification.

## contentauth/c2pa-rs

2026-11-25 · MIT OR Apache-2.0 · [Quellstand / source snapshot](https://github.com/contentauth/c2pa-rs/tree/bf30cc5ed8785165a42e17845ffe9eb2be4d4f4e)

**DE** Rust-SDK, CLI und native Bindings, Format- und CI-Matrizen im Repository. JPEG, PNG und weitere Asset-Handler. Tests für Validierung, Vertrauensketten und Interoperabilität.

**EN** Native validation engine with documented target tiers and format handlers. Select for local verification. Pin versions and test offline trust settings, malformed boxes and supported architectures.

## contentauth/c2pa-python

2026-11-18 · MIT OR Apache-2.0 · [Quellstand / source snapshot](https://github.com/contentauth/c2pa-python/tree/26cad53cd48f09f9d7c0ec708f1aed2ceef48570)

**DE** Python-Bindings für native C2PA-Bibliothek, Reader und Signer. Formatumfang vom nativen SDK abhängig. Testfixtures u.a. JPEG, DNG und MOV. macOS Universal-Build dokumentiert.

**EN** Python entry point to native SDK validation. Prefer Reader for inspection. Test native library loading on each Windows, Linux and macOS architecture and distinguish missing backend from absent manifest.

## exiv2/exiv2

2026-11-22 · GPL, siehe / see COPYING · [Quellstand / source snapshot](https://github.com/exiv2/exiv2/tree/6c0f61e1289bbb7688379ed60f052459206638f8)

**DE** Zusätzlicher Vergleich: C++-Bibliothek und CLI, EXIF/IPTC/XMP, JPEG/TIFF und optionale BMFF-Unterstützung. CI für Linux/macOS/Windows, Regressionstestdaten.

**EN** Additional independent metadata implementation. Useful cross-check for disputed values. Build options affect BMFF coverage. A second native writer increases the verification and distribution burden.

## Offene Fehlerberichte / Open upstream reports

Stichprobe offener Meldungen zum Abrufdatum, ohne lokale Reproduktion. / Selected upstream reports, independently unverified.

- ExifTool: Lesefehler bei bestimmten Xiaomi-HEIC-Dateien / read failure on specific HEIC inputs. [#525](https://github.com/exiftool/exiftool/issues/525)
- C2PA Rust: Ablehnung von JUMBF-Padding / rejection of JUMBF padding. [#3138](https://github.com/contentauth/c2pa-rs/issues/3138)
- Exiv2: Verlust des UTC-Offsets bei Datumskonvertierung / offset loss during date conversion. [#9575](https://github.com/Exiv2/exiv2/issues/9575)

## Architekturentscheidung / Architecture decision

Eigener Kopier-, Freigabe- und Prüfpfad. ExifTool liest gruppierte Metadaten, der CAI-Reader validiert Manifeste. Ein unabhängiger JPEG-Parser erfasst Scans, segmentierte Metadaten und Zusatzbilder. Jede erlaubte Änderung braucht eine feldgenaue Vorschau und eine Prüfung der Ausgabedatei. Ein Fehler in einem Backend bleibt als Fehler sichtbar.

Build the approval, copy and verification workflow locally. Read grouped metadata through ExifTool and validate manifests through the CAI reader. Independently compare JPEG scans, metadata containers and auxiliary images. Require field-level previews and verify changes against the actual output. Preserve backend failures in reports.
