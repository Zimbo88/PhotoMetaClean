# Weiterarbeit und Benchmark / Next experiments and benchmark

| Worker | Dateien / files | Sekunden / seconds | Dateien/s | MiB/s |
|---:|---:|---:|---:|---:|
| 1 | 62 | 21.749 | 2.851 | 11.875 |
| 8 | 62 | 4.431 | 13.992 | 58.286 |

Gemessen wurde die gesamte parallele Inventur einschließlich Vorher-/Nachher-Hash, ExifTool, JPEG-Struktur, Pixeldekodierung und Offline-C2PA-Prüfung. Paarzuordnung und Berichtsausgabe liegen außerhalb des Zeitfensters. Der Acht-Worker-Lauf war hier rund 4,9-mal schneller. Beide Messungen liefen auf demselben Linux-Rechner mit bereits gelesenen Daten. Einzelmessungen ohne erzwungenen Cache-Reset erlauben keine allgemeine Hochrechnung.

Next, export an explicitly licensed reference image with identical settings in each available Lightroom version. Vary one edit or credential setting per export. Preserve catalog history, RAW references and the offline trust configuration. Repeat measurements across worker counts and memory budgets before setting production concurrency for thousands of files. The exhaustive pair search used here scales with the product of the two inventory sizes.

Ein zusätzlicher lokaler Lasttest durchlief mit 16 Prozessen 2.000 synthetische JPEGs in 20,04 Sekunden (99,78 Dateien/s). Die Bilder waren 320 × 240 Pixel groß. Dieser Lauf misst vor allem Verzeichniserfassung und Metadatenverarbeitung. Für hochauflösende HDR-Fotos gilt die gesonderte Messung oben. Reproduction: `python scripts/benchmark.py --files 2000 --workers 16`.

For a controlled Adobe comparison, keep the export preset, optional credentials setting, camera source and application version fixed. Use separate virtual copies from the same known baseline for an unedited control, a re-export of earlier Generative Remove, a new manual clone, Denoise and a new Generative Remove stroke. Record the exact Remove mode and Firefly checkbox, software build, catalog history and output hash. Examine the resulting JPEGs offline. A platform label is a separate observation requiring the exact uploaded export and the label text.

Der abschließende Acht-Worker-Kontrolllauf nach der Integration von Klassifikations- und Speichergrenzen dauerte 3,554 Sekunden bei 62 erfolgreich untersuchten Dateien. Die damaligen Analysegrenzen waren 128 MiB Eingabedaten, 64 Millionen Pixel pro JPEG-Bild und 128 Millionen Pixel über die aufeinanderfolgenden JPEG-Bildströme. Der Schreibpfad verwendet engere Formatgrenzen.

## Messung mit Version 0.6.0 / Version 0.6.0 benchmark

Am 26. November 2026 wurden auf dem lokalen Ubuntu-Rechner ein synthetisches 100-Megapixel-JPEG (410.781.429 Bytes) und ein Ordner mit 2.000 kleinen synthetischen JPEGs geprüft. Die Korrektur des großen Bildes einschließlich erneutem Einlesen dauerte 38,35 Sekunden. Der Stapel schrieb und prüfte 2.000 Kopien in 203,10 Sekunden. Beide Läufe wurden teilweise gleichzeitig ausgeführt. Die Zahl der Dateien, die Bildgröße und die Kosten für das Rücklesen beeinflussen die Laufzeit. Die Originale und die Bilddaten wurden mit den Ausgaben verglichen.

The same tests used the CLI with full read-back enabled. On this Ubuntu system the 410.8 MB edit took 38.35 seconds and the 2,000-image batch took 203.10 seconds. The workloads partly overlapped. The current per-file ceilings are 1 GiB of input and 128 million pixels per frame. Format-specific and cumulative frame limits also apply. [Reproduction commands](../docs/build.md)
