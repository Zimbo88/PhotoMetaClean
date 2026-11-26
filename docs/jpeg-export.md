# JPEG-Kopien mit und ohne HDR

[English](#jpeg-copies-with-and-without-hdr) · 26. November 2026

**Kopien bereinigen** liest bekannte KI-Einträge in JPEG, gewöhnlichem XMP, Extended XMP und einfachen EXIF-Werkzeugfeldern. Der Export kann auch ein eingebettetes C2PA-Manifest aus der Ausgabedatei lösen. Dadurch hat die neue Datei den bisherigen eingebetteten Signaturnachweis nicht mehr. Die App stellt keinen neuen Herkunftsnachweis aus. Das Original und das private Prüfprotokoll bewahren die ursprünglichen Angaben.

- **Gewöhnliches JPEG (SDR).** Die App bearbeitet erkannte Metadatenbereiche, liest die gespeicherte Datei und vergleicht komprimierte Bilddaten, dekodierte Pixel und das ICC-Profil.
- **HDR-JPEG mit unterstützter ISO-Gain-Map.** Die App prüft zusätzlich den MPF-Index, die HDR-Beschreibungen und den zweiten JPEG-Bildstrom. Beim Entfernen von Metadaten können sich Bildpositionen verschieben. Die App berücksichtigt diese Verschiebung. Die gesamte Gain Map muss bytegenau erhalten bleiben.
- **Extended XMP.** Die App ordnet die Teile anhand von Kennung, Gesamtlänge und Position. Sie prüft die Prüfsumme, entfernt erkannte Firefly-Retuscheneinträge, berechnet die Kennung neu und aktualisiert den Verweis im Hauptpaket. Gewöhnliche Retuschen im selben Arbeitsablauf können damit erhalten bleiben.
- **Privates Prüfprotokoll.** Die JSONL-Datei enthält Eingabe- und Ausgabehashes und die früheren Metadatenbytes. Die Einträge unter `recovery` enthalten die Position in der Ausgabedatei, die Länge der dort geschriebenen Daten und die ursprünglichen Bytes in Base64. In umgekehrter Reihenfolge eingesetzt, ergeben sie zusammen mit der Ausgabedatei das ursprüngliche JPEG. Im Forum bitte nur den Kurzbericht aus der App teilen.
- **Grenzen.** Der vollständig geprüfte Export gilt für unterstützte JPEG-Strukturen. RAW bleibt im Lese- und Kopiermodus. Separat vorliegende C2PA-Dateien, unbekannte Mehrbildstrukturen oder ein verbliebener erkannter KI-Eintrag können den Export verhindern. Ein Plattform-Upload kann weiterhin eine Kennzeichnung auslösen. Das Programm untersucht keine Wasserzeichen in den Pixeln.

Die technische Grundlage bilden Adobes XMP-Dateispezifikation, die C2PA-Spezifikation für JPEG und die Dokumentation zu HDR-Bildern mit Gain Map. Android dokumentiert auch Kombinationen von Ultra HDR und ISO 21496-1. Die aktuelle App prüft ihren unterstützten ISO-Aufbau. [Adobe XMP, Teil 3](https://developer.adobe.com/xmp/docs/xmp-specifications/) · [C2PA für JPEG](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html) · [Android HDR-Bildformat](https://developer.android.com/media/platform/hdr-image-format)

Verwende den Export nur, wenn du die erforderlichen Rechte hast. Adobe untersagt für seine generativen Funktionen das Entfernen, Verändern oder Deaktivieren von Content Credentials. Eine Sicherung des Originals erteilt keine vertragliche Freigabe. [Adobe, Abschnitt 6](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html)

## JPEG copies with and without HDR

**Clean copies** checks recognized AI fields in JPEG, ordinary and extended XMP, and simple EXIF tool fields. The export can detach an embedded C2PA manifest from the output image. The original and the local recovery journal keep the previous record. The exported copy carries no new signed statement.

For ordinary JPEGs the app verifies compressed scans, decoded samples and ICC data. For supported HDR JPEGs it also validates the MPF index and the ISO gain-map descriptors and checks that the complete secondary image is byte-identical. Extended XMP fragments are reassembled, checked and referenced using their updated digest. Recovery records can be applied in reverse order using each output offset, replacement length and original bytes.

An unknown multi-image layout, an external manifest, or a supported AI record still present on read-back can prevent a clean export. Social networks may evaluate other signals. Pixel watermarks are outside this metadata check. Keep the full journal private. Use the short in-app report for GitHub Discussions.

Use the export only where you have the necessary rights. Adobe's terms for its generative features prohibit removing, altering or disabling Content Credentials. [Adobe terms](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html) · [JPEG/XMP](https://developer.adobe.com/xmp/docs/xmp-specifications/) · [C2PA](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html) · [Gain maps](https://developer.android.com/media/platform/hdr-image-format)
