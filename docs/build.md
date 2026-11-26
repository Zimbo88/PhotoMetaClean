# Entwicklung und Tests / Development and testing

## Deutsch

Die Pakete enthalten die grafische Anwendung, die Kommandozeile und ExifTool. Auf Ubuntu x86_64 lässt sich die tar.gz im Dateimanager entpacken. Ein Doppelklick auf **PhotoMetaClean** im entpackten Ordner öffnet die Anwendung. [Alle Downloads und Startanleitungen](START.md)

Wer aus dem Quellcode arbeiten möchte, benötigt Python ab 3.11 und ExifTool. Für reproduzierbare native Pakete verwendet der CI-Build Python 3.12. Unter Ubuntu im Projektordner ausführen.

```bash
sudo apt install python3-venv squashfs-tools libimage-exiftool-perl libegl1 libxcb-cursor0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[gui,test,build]'
photometaclean-gui
```

Die folgenden Befehle zeigen die Analyse, den Dateivergleich und die zweistufige Korrektur an einem Beispiel. Protokolle können persönliche Daten enthalten. Wähle dafür ein privates Ziel außerhalb der Eingabeordner.

```bash
photometaclean patch Bilder --output Auslieferung
photometaclean analyze Bilder --workers 4 --report analyse.jsonl
photometaclean explain Bilder --lang de
photometaclean compare vorher.jpg nachher.jpg
photometaclean edit Bilder --changes '{"JPEG:Comment":null}'
photometaclean edit Bilder --changes '{"JPEG:Comment":null}' --apply --output Kopien --report korrekturen.jsonl
```

Der Befehl `patch` legt im gewählten Ausgabeort den Kundenordner `Patch` und den getrennten Ordner `Patch-Protokolle` an. Mit `--only-changed` erhältst du nur bearbeitete Dateien, mit `--history` entfernst du zusätzlich unterstützte Bearbeitungsschritte.

## English

The `patch` command creates the complete customer folder and its separate logs under the selected output location. Add `--only-changed` to save corrections alone or `--history` to remove supported editing records as well.

The release packages include the desktop app, CLI and ExifTool. For a source installation, install Python 3.11 or later and put ExifTool on PATH. The Ubuntu commands above create a virtual environment and install the GUI, test and build dependencies. The native workflow uses Python 3.12. In the CLI examples, substitute your input and output directories and use `--lang en` for the English report. Analysis includes subfolders by default. Use `--flat` to scan the top level alone. [Desktop packages and startup instructions](START.md#english)

## Prüfungen und Pakete / Tests and packages

```bash
python -m pytest
python scripts/privacy_guard.py
python packaging/build.py
```

Der Workflow erstellt Pakete auf Ubuntu 22.04 x86_64, Windows Server 2022 x64 und macOS 15 für Intel und macOS 26 für Apple Silicon. Der Pakettest startet das gebündelte Qt-Fenster, klickt auf den Patch-Button und prüft die geschriebenen Dateien. Automatisierte Pakettests und Prüfungen auf Desktopgeräten werden getrennt dokumentiert. Die manuelle Bedienprüfung auf Windows 11 und macOS steht aus. [Prüfläufe](https://github.com/Zimbo88/PhotoMetaClean/actions/workflows/native.yml)

Each build runs on its target architecture and exercises the packaged GUI and CLI. Hands-on testing on Windows 10/11 and macOS desktops is pending. The Windows package ships without a publisher signature. The Mac packages are not notarized. Linux builds use a pinned x86_64 AppImage runtime and require squashfs-tools. Uncached build dependencies need network access. The packaged app processes photos offline. [Native workflow](../.github/workflows/native.yml) · [Third-party notices](../THIRD_PARTY_NOTICES.md)

## Abnahme von 0.6.0 / Release verification

Je 252 Tests bestanden auf Ubuntu 22.04 x86_64, Windows Server 2022 x64, macOS 15 Intel und macOS 26 Apple Silicon. Der Test der gepackten Anwendung prüfte per Klick eine JPEG-Korrektur mit Unicode-Dateinamen, ein PNG mit komprimierten Werkzeugeinstellungen und die unveränderte Kopie einer Begleitdatei. Die Linux-Ausgabe lief außerdem offline unter Debian 13.8 und schrieb erfolgreich auf ein temporäres exFAT-Dateisystem. [Prüflauf für den veröffentlichten Programmstand](https://github.com/Zimbo88/PhotoMetaClean/actions/workflows/native.yml)

All 252 tests passed on each native runner. The packaged GUI test clicked through a folder patch and checked the files it wrote. The Linux package was additionally exercised on offline Debian 13.8 and an exFAT test volume. Manual testing of Windows 10/11 and end-user Mac desktops remains open. [Release packages and SHA-256 checksums](https://github.com/Zimbo88/PhotoMetaClean/releases)

## Frühere Leistungsmessung / Earlier benchmark

Ein synthetisches JPEG mit 100 Megapixeln und 410.781.421 Bytes benötigte auf dem lokalen Ubuntu-Rechner 14 Sekunden für die Analyse und 28 Sekunden für eine geprüfte Korrektur. Die Spitzenwerte für den Arbeitsspeicher lagen bei rund 1,16 und 0,79 GiB. Ein separater Lauf mit 2.000 kleinen JPEGs schrieb die Kopien und Protokolle in rund neun Sekunden. Die Werte hängen von Bildgröße, Speicher und Laufwerk ab.

On the local Ubuntu machine, a synthetic 410.8 MB JPEG took 14 seconds to analyze and 28 seconds to edit and verify. A separate batch of 2,000 small JPEGs took about nine seconds. Use the following commands to repeat the measurements on your hardware.

```bash
python scripts/check_large_batch.py large
python scripts/check_large_batch.py batch --files 2000
```
