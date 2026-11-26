# PhotoMetaClean – Abschlussbericht der ersten lokalen Entwicklungsphase

## Version 0.7.0

Die neue lokale Abnahme umfasste 71 Forschungsdateien. Zwölf HDR-JPEG-Kopien enthielten nach dem Export keine der geprüften KI-Angaben mehr. Bei allen zwölf passten komprimierte Bilddaten, dekodierte Pixel, Farbprofil und vollständige Gain Map. Eine separate, gezielt markierte Kopie einer herkömmlichen SDR-Aufnahme prüfte den Fall ohne Gain Map. Die ursprünglichen JPEGs konnten mit den privaten Wiederherstellungsdaten bytegenau rekonstruiert werden. Die Einzelergebnisse bleiben lokal. Eine automatische Kennzeichnung beim Hochladen ist eine separate Plattformentscheidung.

The 0.7.0 local acceptance run produced twelve verified HDR JPEG exports and tested a deliberately marked SDR control separately. Image scans, decoded samples, color and gain-map data were preserved. File-level checks do not predict upload labels. [JPEG export verification](jpeg-export.md)

## Version 0.6.0

Ein Ordnerpatch kann erkannte, unsignierte Werkzeugeinstellungen aus der Ausgabekopie entfernen. Nach jeder Änderung liest die App die gespeicherte Datei erneut. Ein Forumsbericht zeigt die bekannten technischen Angaben, verbleibende Hinweise und das Ergebnis der Bearbeitung. Wer nach dem Hochladen weiterhin eine KI-Kennzeichnung sieht, kann diesen Kurzbericht freiwillig in GitHub Discussions teilen. [Erkennungsregeln und Meldeweg](marker.md)

Bei der neuen Prüfung bestätigten sich die Hashes aller 71 lokalen Forschungsoriginale. Fünf der acht zusätzlichen JPEGs enthielten eine dokumentierte Firefly-Retusche. Die übrigen drei enthielten keinen passenden Eintrag. Bei einer gezielt fehlerhaft beschrifteten separaten Kontrollkopie ließ sich die Quellenangabe entfernen. Eine Plattformkennzeichnung wurde dabei nicht gemessen. [Leistungsmessung mit 100 Megapixeln und 2.000 Bildern](../research/12_ENTWICKLUNGSPLAN.md)

Version 0.6.0 checks each edited output by reading it back and offers a short report for public forum feedback. The 71 research originals matched their archived hashes. Five of eight additional export variants carried Firefly edit credentials. A separate deliberately mislabeled control allowed an actual verified correction. [Recognition rules and forum](marker.md#how-does-photometaclean-recognize-ai-indicators)

## Stand der Ordnerprüfung in Version 0.5.0

Der erste Klick prüfte alle 70 JPEGs und das Sony-RAW aus den drei Forschungsordnern. Bei zwölf JPEGs schützte die App die eingebetteten Herkunftsnachweise. Keine der Dateien enthielt die unterstützte falsche, unsignierte Angabe „vollständig KI-generiert“. Der Lauf mit ausschließlich geänderten Bildern ergab deshalb null Fotokopien und null Fehler. Alle 71 Original-Prüfsummen stimmten mit der Inventur überein. Eine getrennte, gezielt beschriftete Kontrollaufnahme prüft den Fall einer tatsächlichen Korrektur. Sie zählt nicht zur Adobe-Stichprobe.

## Was Adobe in diesen Exporten aufgezeichnet hat

Die beiden Forschungsordner enthalten 32 ältere und 30 neuere JPEGs. Die Dateiprüfsummen aller 62 Originale stimmten vor und nach der Untersuchung überein. Sidecars kamen in beiden Ordnern nicht vor. Als Exportsoftware nennen die älteren Dateien Lightroom Classic 15.5.1 oder 15.6 und die neueren 16.0.1. Nach Angabe des Fotografen erfolgte für diesen Vergleich keine neue Bearbeitung.

| Beobachtung | Früher (32) | Später (30) |
|---|---:|---:|
| Eingebettetes C2PA-Manifest | 5 | 2 |
| Zweiter JPEG-Bildstrom mit Gain-Map-Kennzeichnung | 30 | 21 |
| Extended XMP | 6 | 2 |

In allen sieben aktiven Manifesten nennt Adobe das Werkzeug `Adobe Remove Object` und protokolliert `Healing changed, Uses GenAI`. Der IPTC-Wert `compositeWithTrainedAlgorithmicMedia` bezeichnet eine generative Bearbeitung bzw. Ergänzung. Das erklärt, wie ein selbst aufgenommenes Foto einen maschinenlesbaren KI-Bearbeitungshinweis tragen kann. Die Einträge enthalten keine belastbare Aussage darüber, wie groß die retuschierte Stelle war. Die sieben Signaturen und Inhaltsbindungen bestanden die Offline-Prüfung. Die lokale Vertrauensprüfung meldete für die Zertifikate `signingCredential.untrusted`. [C2PA-Befunde](../research/09_C2PA_ANALYSE.md)

Fünf Paare ließen sich anhand von Aufnahmezeit, Dateinamen und Bildinhalt eindeutig zuordnen. Alle fünf erhielten ein neues Camera-Raw-Feld `ReshapeAmount`, vier zusätzlich `Glow`. Bei allen änderten sich die Pixelhashes des Hauptbilds. Das Auslesen eines neuen Reglerfelds belegt dessen Speicherung. Welchen Regler der Fotograf betätigte, ergibt sich daraus allein nicht. Keines dieser Paare belegt einen Übergang zu einem eingebetteten Manifest. Vier weitere Kandidaten sind unsicher. Ein direkter Vergleich der beiden Manifestanzahlen wäre wegen der unterschiedlichen Bildauswahl irreführend. [Metadatenvergleich](../research/06_METADATEN_VERGLEICH.md)

## Muss das Foto neu bearbeitet werden?

Für den Nachweis eines vorhandenen KI-Bearbeitungshinweises reicht hier die bestehende Sammlung. Auch eine bereits im Katalog gespeicherte generative Retusche kann bei einem späteren Export wieder erscheinen. Ein Nutzer reproduzierte das in Lightroom Classic 15.5.1 mit einem bereits bearbeiteten Katalogfoto. Adobe beschreibt die automatische Einbettung bei bestimmten generativen Werkzeugen. Meta bestätigt, dass auch kleine KI-Retuschen zu sichtbaren Hinweisen geführt haben. Für vier zusätzliche Exporte meldete der Fotograf nach einem Upload eine KI-Kennzeichnung. Plattform, Wortlaut und Ursache sind für diese Beobachtung offen. [Katalogversuch](https://community.adobe.com/questions-675/p-post-15-5-1-content-credentials-may-be-added-automatically-during-export-1639701) · [Adobe-FAQ](https://helpx.adobe.com/creative-cloud/apps/generative-ai/ai-content-labeling-faq.html) · [Meta](https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/)

Für die separate Frage nach einer **frischen** Retusche in 16.0.1 ist ein kontrollierter Versuch offen. Dazu dasselbe Ausgangsfoto in separaten virtuellen Kopien ohne Retusche, mit manuellem Klonen, mit Entrauschen und mit einem ausdrücklich generativen Entfernen exportieren. Eine weitere Kopie mit einer alten generativen Retusche direkt neu exportieren. Das Exportprofil konstant halten. Dafür ist kein Upload privater Fotos erforderlich.

## Anwendung, Tests und Grenzen

Die lokale deutsche und englische Desktopanwendung und die CLI unterstützen rekursive Analyse, Vergleich, Korrekturvorschau und verifizierte JPEG-Ausgaben. Der Fotografenmodus verlangt eine begründete manuelle Entscheidung. Die Datenbereinigung bezieht sich auf die ausdrücklich ausgewählten Speicherorte. COM-Kommentare und unterstützte einfache XMP-Attribute lassen sich korrigieren. Ein GPS-Eintrag in EXIF kann weiterhin vorhanden sein. Signierte, mehrdeutige und nicht unterstützte Dateien erhalten keine korrigierte Ausgabe. Für ein signiertes Foto die dokumentierte Aktion am Kameraoriginal und im Katalog überprüfen und bei Bedarf nachvollziehbar neu exportieren. [Bearbeitungsleitfaden](edit.md)

Der Schreibpfad bewahrt die Bytes außerhalb der freigegebenen Bereiche. Er kontrolliert komprimierte JPEG-Scans, dekodierte Pixel und ICC-Daten. Bei unterstützten HDR-JPEGs prüft die Anwendung auch den zweiten Bildstrom. Unbekannte Mehrbildstrukturen und Extended XMP bleiben im Analysemodus. RAW-Dateien werden ausschließlich untersucht oder bytegenau kopiert. Die inzwischen unterstützten Schreibpfade für weitere Formate sind im [Bearbeitungsleitfaden](edit.md) aufgeführt. Die Forschungsberichte mit Dateinamen, Bildfingerabdrücken, Standort- und Herkunftsdaten liegen ausschließlich im lokal ignorierten Verzeichnis.

Die Tests verwenden synthetische Daten und prüfen unter anderem parallele Veröffentlichungsversuche, ungültige Eingaben, Änderungen zwischen Vorschau und Freigabe, MakerNote-Nutzdaten, Pixel, ICC, HDR-Schutz, Unicode-Pfade und die Qt-Bedienfolge von der Vorschau bis zur Ausgabedatei. Die Messung mit acht Prozessen untersuchte die 62 Forschungsbilder in 4,43 Sekunden. Ein separater Lauf verarbeitete 2.000 kleine synthetische JPEGs. [Messbedingungen](../research/12_ENTWICKLUNGSPLAN.md)

## Start unter Ubuntu

Unter Ubuntu x86_64 das Archiv **PhotoMetaClean-linux-x86_64.tar.gz** herunterladen, im Dateimanager entpacken und **PhotoMetaClean** doppelklicken. [Download und Start auf allen drei Plattformen](START.md)

Wer direkt aus dem eingerichteten Projektverzeichnis arbeitet, kann die Oberfläche auch so starten.

```bash
.venv/bin/photometaclean-gui
```

Für eine neue Installation, CLI-Beispiele und den Build aus dem Quelltext siehe [Entwicklungsanleitung und Plattformprüfstand](build.md).

Im lokalen Abnahmelauf wurde auf **21 temporären Kopien** jeweils das vorhandene XMP-Seriennummernfeld entfernt. Bei 19 dieser Kopien wurden beide JPEG-Bildströme dekodiert und verglichen. ExifTool bestätigte die Änderung, und der Bytevergleich erfasste alle Bereiche außerhalb des ausgewählten Attributs. Sieben signierte Exporte sperrten Vorschau und Schreiben. Bei 34 Dateien fehlte ein geeignetes Feld für diesen Datenschutztest. Die Hashwerte aller 62 Ausgangsdateien entsprachen der früheren Inventur. Der Test sagt ausschließlich etwas über die bearbeitete XMP-Eigenschaft aus. Eine Seriennummer kann beispielsweise auch in EXIF stehen.

Für die Herkunftsauswertung wurden zusätzlich sieben unveränderte, öffentlich lizenzierte Testbilder untersucht. Sie enthalten unter anderem getrennte Kontrollfälle für eine fehlerhafte Signatur und einen fehlerhaften Inhaltsnachweis. Die lokalen Dateien belegen weiterhin keine individuelle Plattformentscheidung. [Öffentliche Kontrollbilder und Prüfsummen](../research/13_OEFFENTLICHE_VERGLEICHSBILDER.md)

## Ordner-Patch und Adobe-Retuscheversuch in 0.4.0

Im zusätzlichen Versuch enthielten fünf von acht JPEGs jeweils Adobes signierte Objektentfernung und Firefly als Füllmethode im XMP-Retuschierbereich. Die drei übrigen JPEGs enthielten kein erkennbares eingebettetes JUMBF-Manifest. Die Dateibindung und die Signaturen der fünf Exporte bestanden die lokale Prüfung. Die Zertifikate hatten lokal keine bestätigte Vertrauenskette. Das zusätzliche Sony-RAW blieb im Analysemodus. [Felder und Interpretation](../research/15_ADOBE_BEARBEITUNGSSIGNALE.md)

Im normalen Ordner-Patch erzeugte die grafische Oberfläche neun bytegleiche Kopien. Im Modus für ausschließlich geänderte Bilder wurde bei diesem Versuch keine Bildkopie ausgegeben. Die SHA-256-Werte aller neun Ausgangsdateien blieben gleich. In einem getrennten Versuch enthielt ein synthetisches JPEG eine absichtlich falsche, unsignierte IPTC-Einstufung. Über den Patch-Button ließ sie sich nach Prüfung der Vorschau auf einer Kopie entfernen. Die Bilddatenprüfung bestand, und die erneute Analyse las keine Herkunftseinstufung mehr aus dieser Kopie. Aus diesen lokalen Versuchen folgt keine Zusage über die Kennzeichnung eines Uploads. [Meta zu Kennzeichnungen kleiner Retuschen](https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/)

## Nutzung und Kompatibilität

Die Desktop-App ist für Windows, macOS und Linux erhältlich. Die Startanleitung erklärt die Paketwahl nach Betriebssystem und Prozessor. [Startanleitung](START.md) · [Tests und Systemvoraussetzungen](build.md)
