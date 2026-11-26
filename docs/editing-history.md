# Bearbeitungsverlauf aus einer Kopie entfernen

[English](#english)

Wenn du ein fertiges Foto weitergibst, kannst du die gespeicherten Arbeitsschritte für dich behalten. Ziehe den Fotoordner ins Fenster, setze **Auch den Bearbeitungsverlauf aus Kopien entfernen** und klicke auf **Kopien bereinigen**. Beim ersten Start ist das Häkchen aus. Die Ergebnisliste zeigt, was mit jeder Datei passiert ist. Im Standardmodus kommen auch unveränderte Bilder in den Ausgabeordner.

| Was in der Datei steht | Was die Option damit macht |
|---|---|
| XMP-Verlauf und Versionsliste | Entfernt unterstützte Einträge in `xmpMM:History`, `xmpMM:Versions` und `photoshop:History`. Adobe beschreibt den XMP-Verlauf als Liste von Aktionen, die zur aktuellen Fassung geführt haben. [Adobe XMP](https://developer.adobe.com/xmp/docs/xmp-namespaces/xmp-mm/) |
| Gespeicherte Entwicklungs- und Retuschierschritte | Entfernt bekannte Camera-Raw-Regler für Belichtung, Farbe, Schärfung und Beschnitt sowie unterstützte Retusche- und Maskeneinträge im Hauptpaket und bei JPEG auch im erweiterten XMP. |
| Bearbeitungsprogramm | Entfernt bekannte Editornamen in unterstützten EXIF-, TIFF-, PNG- und XMP-Feldern. Kamera-Firmware, Fotografenname, Bildrechte, Aufnahmedatum und Bildbeschreibung bleiben erhalten. |
| Herkunftsnachweis | Das Häkchen für den Verlauf allein erhält den eingebetteten Nachweis. Würde die Änderung eine Signatur verletzen, bleibt die Datei im Standardmodus eine exakte Kopie. Sind auch die JPEG-Herkunftsnachweise zum Entfernen ausgewählt, kann die App bei erkannten Bearbeitungsaktionen das vollständige Manifest aus der Kopie lösen. Das frühere Manifest ist im Original und im privaten Protokoll erhalten. |
| HDR und unbekannte Angaben | Farbprofile, HDR-Parameter, Gain Maps und Kameraprofile bleiben erhalten. Unbekannte Formate, nicht unterstützte Strukturen und externe Herkunftsnachweise können den Export verhindern. |

Die Option verarbeitet unterstützte gewöhnliche und HDR-JPEGs sowie passende XMP-Pakete in PNG/APNG, WebP, TIFF und unterstützten HEIF-Containern einschließlich AVIF. Die App überprüft die Bilddaten und die entfernten Felder nach dem Speichern. RAW-Dateien bleiben im Analyse- und Kopiermodus. Ein erhaltener Titel, ein frei geschriebener Kommentar, ein Wasserzeichen in den Pixeln oder eine separat mitgelieferte Datei können weiterhin Hinweise auf die Bearbeitung enthalten. Die tatsächlichen Retuschen sind Teil des Bildes. Die Plattform entscheidet beim Upload über ihr Label. [Bekannte KI-Felder](marker.md) · [HDR-Prüfung](jpeg-export.md)

Bei Aufnahmen mit generativer Adobe-Bearbeitung gelten die Nutzungsbedingungen der eingesetzten Funktion. Adobe untersagt das Entfernen, Verändern oder Deaktivieren von Content Credentials. [Adobe, Abschnitt 6](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html)

## English

Drop a folder into the window, select **Also remove editing history from copies** and click **Clean copies**. The option starts off. It covers recognized XMP history and version lists, Camera Raw exposure, colour, crop, retouch and mask records, and recognized editor names in supported software fields. It applies to supported SDR and HDR JPEGs and supported XMP layouts in PNG/APNG, WebP, TIFF and HEIF containers including AVIF. RAW files can be analyzed and copied.

With the JPEG credentials option off, an edit that would invalidate a provenance record is skipped. Selecting both options can detach an embedded manifest describing recognized edits. The copy then loses that embedded signature. The original and the private recovery journal retain the prior record. Keep full journals private. The app preserves camera and credit fields, checked pixels, colour profiles and HDR gain maps. Free text, separate files, unknown records or an embedded pixel watermark can still describe or reveal the edit. Social platforms decide how they label uploads. Adobe prohibits removing, altering or disabling Content Credentials under its generative AI guidelines. [XMP history](https://developer.adobe.com/xmp/docs/xmp-namespaces/xmp-mm/) · [Recognition rules](marker.md) · [Adobe terms](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html)

For the CLI, pass `--changes '{"XMP:EditingHistory":null}'` to `edit`, together with `--evidence` describing the requested export. The default is a preview. Add `--apply --output <new-directory>` to create the checked copies.

## Öffentlicher Bildvergleich vom 26. November 2026

Die Prüfung umfasste **100 unterschiedliche Internetbilder**. 86 Aufnahmen kamen aus der NASA Image and Video Library. 14 Beispiele kamen von der Content Authenticity Initiative, aus den C2PA-Testdateien und aus den ComfyUI-Beispielen. Identische Datei-Hashes und nahe Bildfingerabdrücke wurden bei der Auswahl ausgefiltert. Alle Quelldateien wurden lokal geprüft. [NASA](https://images.nasa.gov/) · [CAI-Bilder](https://github.com/contentauth/example-assets) · [C2PA-Beispiele](https://github.com/c2pa-org/public-testfiles) · [ComfyUI-Bilder](https://github.com/comfyanonymous/ComfyUI_examples)

| Ergebnis beim ersten Durchlauf mit eingeschaltetem Verlauf | Dateien |
|---|---:|
| Bearbeitet und erneut eingelesen, ohne verbliebene erkannte KI- oder Verlaufsangaben | 42 |
| Bytegleich kopiert, weil keine passende Änderung ausgewählt oder gefunden wurde | 50 |
| Bytegleich kopiert wegen Herkunftsnachweisen, Metadatenwarnungen oder einer offenen Nachprüfung | 8 |

Unter den 42 geänderten Originalmotiven hatten zehn erkennbare KI-Einträge, 31 gewöhnliche Verlaufseinträge und eines einen signierten Bearbeitungsschritt. Bei allen 42 stimmten die komprimierten Bilddaten und die dekodierten Pixel mit der jeweiligen Eingabe überein.

Für einen zweiten Versuch wurden aus denselben 100 Motiven verkleinerte, **absichtlich markierte Testkopien** erstellt. 50 JPEGs und 50 PNGs erhielten bekannte Verlaufsfelder und eine künstliche KI-Quellenangabe. Die PNGs enthielten zusätzlich Generator-Einstellungen. Die App entfernte die vorbereiteten Einträge bei allen 100. Eine Kontroll-Seriennummer blieb erhalten. Aus jeder Ausgabe und ihrem privaten Protokoll ließ sich die jeweilige markierte Eingabe bytegenau rekonstruieren. Die Fotos wurden für diesen Versuch auf keiner sozialen Plattform hochgeladen.

### English test results

The batch processed 100 distinct online originals from NASA, CAI, C2PA and ComfyUI. It edited and verified 42 files, copied 50 files without a matching change, and preserved eight because of provenance, metadata warnings or an inconclusive read-back. Ten edited files contained recognized AI fields, 31 contained ordinary editing records and one contained a signed editing action. In a separate controlled trial, 50 JPEG and 50 PNG derivatives of these subjects received known test records. All 100 derivatives passed removal, pixel checks, retention of a control serial number and byte-exact reconstruction of their marked inputs. This was a local file test. No photos were uploaded to social platforms.
