# Forschungsstand / Research status

62 lokale JPEG-Exporte wurden vollständig inventarisiert. Für jede Datei stimmten die SHA-256-Prüfsummen vor und nach der Untersuchung überein. Es gab keine Analysefehler. Die privaten Ergebnisdateien liegen unter `research/private/`. Sie enthalten unter anderem identifizierende Metadaten und Pfade.

All 62 local JPEG exports completed analysis. Before/after SHA-256 checks agreed for every original. Public reports contain aggregate findings. Individual metadata, image fingerprints, paths and manifest details belong in the ignored private directory.

Der ergänzende Versuch umfasst acht JPEG-Exporte und eine Sony-RAW-Datei. Bei der erneuten Prüfung für Version 0.6.0 stimmten alle 71 untersuchten Originale mit den archivierten SHA-256-Werten überein. Bei fünf der acht zusätzlichen Exportbilder war eine Firefly-Retusche mit Herkunftsnachweis dokumentiert. Weitere lokale Tests umfassten öffentlich verfügbare Vergleichsdateien und eine ausdrücklich als solche angelegte Positivkontrolle.

The follow-up series contains eight JPEG exports and one Sony RAW file. The 0.6.0 recheck matched all 71 original SHA-256 digests. Five of the eight additional exports carried a documented Firefly edit with provenance. [Adobe-Befunde / Adobe findings](15_ADOBE_BEARBEITUNGSSIGNALE.md) · [Marker / indicators](../docs/marker.md)

## Reproduktion / Reproduction

Aus dem Projektverzeichnis unter Linux mit ExifTool auf dem PATH / From the repository root on Linux with ExifTool on PATH:

```bash
python3 -m venv .venv-research
.venv-research/bin/python -m pip install Pillow==12.1.1 c2pa-python==0.39.0 pytest
.venv-research/bin/python scripts/research.py --workers 8
.venv-research/bin/python -m pytest -q tests/test_research.py
```

Gemessene Umgebung / Measured environment: Python 3.14.4, Pillow 12.1.1, ExifTool 13.50, c2pa-python 0.39.0. Paketinstallation benötigt einen lokalen Paketbestand oder Internetzugang. Der Untersuchungslauf arbeitet lokal. ExifTool läuft ohne Benutzerkonfiguration. Der Manifestleser verwendet eine leere Netzwerkfreigabeliste und deaktiviert Online-Manifest- und OCSP-Abrufe.

The run replaces earlier private reports. Archive previous reports locally before repeating if needed. Filesystem access timestamps and SDK trust decisions can vary across environments.

Version 0.2.0 ergänzt sieben öffentliche, separat gelagerte Kontrollen und den Abnahmetest mit temporären Kopien der privaten Exporte. Reproduce the local edit checks with `python scripts/check_research_edits.py --workers 3`. The script prints aggregate results and saves measurements under `research/private/`. [Öffentliche Kontrollen / Public controls](13_OEFFENTLICHE_VERGLEICHSBILDER.md)
