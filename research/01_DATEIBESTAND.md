# Dateibestand / Inventory

| Gruppe / Group | JPEG | Bytes | Sidecars |
|---|---:|---:|---:|
| Vorher / Before | 32 | 187279839 | 0 |
| Nachher / After | 30 | 83531723 | 0 |

Die Inventur durchsucht beide Ordner rekursiv einschließlich versteckter regulärer Dateien. Symbolische Links werden ausgelassen. Alle 62 JPEGs wurden dekodiert. Zusätzlich wurden 51 eingebettete sekundäre JPEG-Bildströme dekodiert.

The recursive inventory includes regular hidden files and skips symbolic links. Private inventory.json contains dimensions, hashes, format, decoded frame details, JPEG structure, ExifTool metadata grouped by location and instance, and embedded manifest validation. Binary metadata values returned by ExifTool are represented by size and SHA-256. inventory.csv provides a compact per-file index.

`research/private/signed_exports.csv` listet die sieben Dateien mit Manifest, Validierungsstatus und deklariertem Quellentyp. `research/private/metadata_changes.csv` enthält die tagweisen Differenzen der untersuchten Kandidaten mit ihrer jeweiligen Zuordnungssicherheit. Both tables contain private research data.
