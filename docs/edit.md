# Verified image copies / Geprüfte Bildkopien

Version 0.6 supports removing recognized PNG processing records and selected simple XMP tool settings in the verified folder patch. For CLI edits, use the keys in `formats.recipes.RECIPE_FIELDS` with null values. PNG workflow chunks are removed as a unit. Other edits retain their existing lengths. Each edited copy is read back. [Detection and fields](marker.md#how-does-photometaclean-recognize-ai-indicators)

Der Ordnerpatch entfernt auf geeigneten Kopien erkannte PNG-Arbeitsabläufe und unterstützte einfache XMP-Werkzeugeinstellungen. Die passenden CLI-Feldnamen stehen in `formats.recipes.RECIPE_FIELDS`. Ein PNG-Arbeitsablauf wird als vollständiger Textblock entfernt. Die fertige Kopie wird erneut eingelesen. [Erkennung und Felder](marker.md)


Der separate JPEG-Export ist in [JPEG-Kopien mit und ohne HDR](jpeg-export.md) beschrieben. Die folgenden Einzelregeln gelten für den manuellen Feldeditor. Über die CLI wählt `--changes '{"JPEG:AIRecords":null}'` den JPEG-Export. Mit `--evidence` dokumentierst du die Grundlage, mit `--apply --output Kopien` erzeugst du eine neue Datei.

The JPEG export uses the same CLI with `JPEG:AIRecords` and a documented basis. The individual-field editor below retains its separate safeguards. [JPEG export](jpeg-export.md#jpeg-copies-with-and-without-hdr)

Import `plan` and `apply` from `photometaclean.core.edit`. Pass a Path and a dictionary using the keys below. Both functions return a JSON-compatible audit dictionary. The preview includes the original SHA-256. Apply independently checks the source and writes to a new destination with exclusive publication. Persist the returned audit locally if needed. Unsupported or ambiguous requests raise ValueError. Existing destinations raise FileExistsError.

Beide Funktionen liefern ein JSON-kompatibles Protokoll. Die Vorschau enthält den ursprünglichen SHA-256. Änderungen erfolgen ausschließlich in einer neuen Zieldatei. Das Protokoll kann personenbezogene Daten enthalten.

| Key / Schlüssel | Value / Wert | Scope / Umfang |
|---|---|---|
| JPEG:Comment | null | Blank every JPEG COM payload / Inhalt aller JPEG-Kommentare mit Leerzeichen überschreiben |
| PNG:Comment | null | Blank the value of a plain PNG tEXt Comment and update its CRC / einfachen PNG-Kommentar leeren und seine CRC-Prüfsumme aktualisieren |
| GIF:Comment | null | Blank comment sub-blocks, keeping animation frames and timing / Kommentarinhalte leeren, Animationsbilder und Anzeigedauer erhalten |
| TIFF:ImageDescription | null | Blank a plain description in the supported classic single-directory TIFF / einfachen Beschreibungstext im unterstützten klassischen TIFF leeren |
| XMP-exif:GPSLatitude, XMP-exif:GPSLongitude | null | Remove matching simple XMP attributes / einfache XMP-Attribute löschen |
| XMP-aux:SerialNumber, XMP-aux:LensSerialNumber | null | Remove matching simple XMP attributes / einfache XMP-Attribute löschen |
| XMP-iptcExt:DigitalSourceType | null | Remove one verified incorrect declaration in a simple attribute, text element or rdf:resource / belegbar falsche Angabe als einfaches Attribut, Textelement oder rdf:resource entfernen |

EXIF GPS and MakerNotes are preserved. A privacy edit covers only the named storage location. Confirm ownership and independently verify the editing history before correcting DigitalSourceType. Supply that evidence in the evidence argument. The software cannot establish whether a declaration is false. Signed, ambiguous and unsupported layouts require review and re-export from the original with accurate credentials. Retain the original and the audit.

EXIF-GPS und MakerNotes bleiben erhalten. Datenschutzänderungen betreffen ausschließlich den benannten Speicherort. Vor der Korrektur des DigitalSourceType Eigentum und Bearbeitungshistorie prüfen und den Beleg als evidence übergeben. Bei signierten oder unklaren Dateien die Ausgangsdatei mit zutreffenden Herkunftsangaben neu exportieren und das Original aufbewahren.

### Reviewed batch API / Freigegebene Stapelverarbeitung

`photometaclean.core.review.review(path, changes, evidence="")` returns
`source, source_sha256, changes, evidence, preview`. Keep this local record
intact for approval. Pass the approved record to
`apply_reviewed(record, destination)`. It checks the source bytes and proposed audit against the reviewed plan and returns
`source, source_sha256, destination, audit`. The field keys above are also
available as `core.review.FIELDS`.

Die GUI und CLI können denselben Prüfdatensatz übernehmen. Die Anwendung
prüft den Hash der eingelesenen Quelldaten vor der Bearbeitung und sperrt bestehende
Ziele sowie beide Forschungsordner im Projekt.

JPEG writes use fixed-size byte substitutions. Every byte outside the reported ranges is preserved. SHA-256 checks cover the persisted output, entropy-coded scans, decoded samples and ICC data. Publication uses an exclusive rename on Windows and on supported Linux/macOS filesystems without hard links, including exFAT. Limits are 1 GiB and 128 megapixels per image. APP11, extended XMP, unrecognized MP indexes, unindexed trailing images, unrecognized APP containers and adjacent .c2pa manifests block editing. This edit gate does not authenticate signatures. JPEG comments in the audit use hex encoding.

Die geänderten Bytebereiche stehen im Protokoll. Die Prüfung umfasst Ausgabedatei, komprimierte Scans, dekodierte Pixel und ICC-Profil. Unter Windows und auf unterstützten Linux-/macOS-Dateisystemen ohne Hardlinks, einschließlich exFAT, wird die geprüfte Datei ohne Überschreiben an ihren Zielnamen verschoben. Grenzen pro Bild sind 1 GiB und 128 Megapixel. APP11, Extended XMP, unbekannte MP-Indizes, nicht indizierte Zusatzbilder, unbekannte APP-Container und benachbarte .c2pa-Manifeste sperren den Schreibvorgang. Der Schreibschutz führt keine kryptografische Signaturprüfung aus. JPEG-Kommentare werden im Protokoll hexadezimal dargestellt.

The GUI and CLI create a private `.photometaclean.jsonl` audit for each edit in a separate sibling logs folder. It records the approval before writing the image and the verified output hash afterward. A failed attempt keeps its audit. Select a fresh destination when retrying.

GUI und CLI legen für jede Korrektur im separaten Protokollordner ein privates Prüfprotokoll mit der Endung `.photometaclean.jsonl` an. Es enthält die Freigabe und nach Erfolg den geprüften Ausgabehash. Bei einem Fehler bleibt der Versuch dokumentiert. Für einen erneuten Versuch ein neues Ziel wählen.

The preview audit contains `source`, `source_sha256`, `output_sha256`,
`evidence`, `signature_status`, `changes` and `integrity_before`.
Each change identifies `field`, `before`, `after`, `offset` and `length`.
The output audit adds `destination` and `integrity_after`.
A .c2pa sidecar beside the original (stem or full filename, case-insensitive)
blocks processing at apply time and immediately before publishing the copy.

Das Prüfprotokoll enthält Ein- und Ausgabehash, Beleg, Signaturstatus und
Integritätsmerkmale. Für jede Änderung sind Feld, alter und neuer Wert,
Byteposition und Länge dokumentiert. C2PA-Sidecars werden nochmals am
Originalpfad geprüft. Unterstützte APP13-Ressourcen sind IPTC-IIM,
IPTC-Digest, ResolutionInfo und Vorschaubilder im geprüften JPEG-Layout. Ihr vollständiger Block bleibt byteidentisch.
[Photoshop resource IDs / Ressourcenkennungen](https://exiftool.org/TagNames/Photoshop.html)


### HDR-JPEGs mit Gain Map / HDR JPEGs with a gain map

Eine Änderung ist im Hauptbild möglich, wenn der MPF-0100-Index die beiden unmittelbar aufeinanderfolgenden JPEGs mit korrekten Typen, Längen und Offsets beschreibt. Beide Bilder müssen die unterstützten ISO-21496-1-Deskriptoren enthalten. Der Prüflauf vergleicht die komprimierten Scans, dekodierten Pixel und ICC-Profile beider Bilder, die MPF- und ISO-Segmente sowie den SHA-256 des gesamten zweiten Bildstroms. Der feste Platzbedarf der Ersetzung bewahrt die Offsets. Änderungen an der Gain Map benötigen einen separaten Export aus der Bildbearbeitung.

Supported dual-stream files carry a classic two-entry MP index and version-zero ISO gain-map descriptors in each stream. Edits target the primary JPEG. The primary rendering data, secondary JPEG bytes, decoded samples, color profiles and descriptor hashes are checked before publication. Other layouts can be inspected offline. [Ultra HDR format and ISO compatibility](https://developer.android.com/media/platform/hdr-image-format)

The single named top-level RDF subject `DJI Meta Data` is supported for the listed privacy attributes. For DigitalSourceType the writable subject must identify the image itself. A detected external provenance pointer, structured source-type value or ambiguous subject requires manual review and a documented re-export.

## Bildformate / Image formats

| Dateiformat / Format | Geprüfter Schreibumfang / Verified edits |
|---|---|
| JPEG, JPG, JPE, JFIF | JPEG-Kommentar und unterstütztes XMP, einschließlich bestimmter HDR-JPEGs mit Gain Map. / JPEG comments and supported XMP, including selected HDR gain-map layouts. |
| PNG, APNG | Einfacher tEXt-Kommentar und unkomprimiertes Adobe-XMP in iTXt. CRC, komprimierte Bilddaten und dekodierte Einzelbilder werden geprüft. / Plain tEXt Comment and uncompressed Adobe XMP in iTXt, with CRC, compressed data and frame checks. |
| WebP | Unterstütztes XMP in einem RIFF-Chunk. Bei Animationen werden die komprimierten Frames, Pixel, Dauer und Schleifeneinstellung kontrolliert. / One supported RIFF XMP chunk, with compressed frames, pixels, duration and loop checks. |
| GIF | Kommentare, auch bei Animationen. Unbekannte Anwendungserweiterungen sperren die Änderung. / Comments, including animations. An unknown application extension blocks editing. |
| TIFF | Beschreibung oder unterstütztes XMP in einem klassischen TIFF mit einem Bildverzeichnis und geprüften, getrennten Bildstreifen. / Description or supported XMP in a classic single-directory TIFF with verified, disjoint image strips. |
| HEIC, HEIF, HIF, AVIF | Unterstütztes XMP, wenn genau ein Bildobjekt und ein zugeordnetes XMP-Objekt in getrennten Datenbereichen liegen. Weitere Objekte, EXIF-Items, Hilfsbilder oder Herkunftscontainer benötigen eine manuelle Prüfung. / Supported XMP on a single still with a separate, unambiguously linked XMP item. Extra items, auxiliary images and provenance containers require review. |
| BMP, JPEG 2000, RAW, SVG und weitere von ExifTool lesbare Bildtypen | Metadatenanalyse. Ein verfügbarer Bilddecoder liefert zusätzliche Pixelbefunde. SVG wird nicht gerendert und RAW bleibt lesend. / Metadata analysis. An available decoder provides additional pixel evidence. SVG stays unrendered and RAW is read-only. |

Größenlimits gelten pro Datei. Bei Animationen gelten zusätzlich höchstens 512 Frames und insgesamt 512 Millionen dekodierte Pixel. Ab 64 MiB Dateigröße bearbeitet die Stapelverarbeitung eine Datei gleichzeitig. Auf Geräten mit knappem RAM einen Worker wählen. Die Originaldatei und die verifizierte Kopie benötigen jeweils Platz auf dem Datenträger.

The size limits apply per file. Animated formats allow up to 512 frames and 512 million decoded pixels in total. Within a batch, files of 64 MiB or more run individually. Choose one worker on machines with limited memory. Allow disk space for both the source and the verified copy.

Die Anwendung liest Dateiangaben lokal. Selbstangaben auf Plattformen, deren interne Erkennungsmodelle und anbieterspezifische unsichtbare Wasserzeichen liegen außerhalb ihres Prüfbereichs. / The app reads local file evidence. Platform disclosures, internal detection models and vendor-specific invisible watermarks are outside its scope. [Plattformbericht / Platform findings](../research/14_PLATTFORMKENNZEICHNUNG.md)
