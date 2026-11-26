# PhotoMetaClean

**Deutsch** · [English](README_EN.md)

PhotoMetaClean prüft Fotos auf bekannte KI-Metadaten, etwa nach einer Bearbeitung in Adobe Lightroom. Du siehst, welche Angaben zur Aufnahme und Bearbeitung in der Bilddatei stehen, und kannst unterstützte Einträge aus einer Kopie entfernen. Die kostenlose App läuft auf deinem Rechner unter Windows, macOS oder Linux, ohne Konto und ohne Foto-Upload. [App herunterladen](https://github.com/Zimbo88/PhotoMetaClean/releases/latest) · [Hilfe beim Start](docs/START.md)

Eine Nachtaufnahme bleibt eine Fotografie, auch wenn beim Entrauschen KI geholfen hat. Wer später nur das Wort „KI“ unter dem Bild sieht, kann leicht den Eindruck bekommen, das ganze Motiv sei künstlich erzeugt. Ich veröffentliche PhotoMetaClean, weil ich Fotografen in meinem Umfeld dabei helfen möchte, ihren Kunden solche Unterschiede zu erklären.

## Einen Kundenordner vorbereiten

1. Ziehe deinen Fotoordner ins Fenster. **Sorglos · kompletter Kundenordner** ist bereits ausgewählt.
2. Prüfe unter **Aus Kopien entfernen**, welche Angaben du entfernen möchtest. Klicke auf **Kopien bereinigen**.
3. Öffne **Kopien anzeigen**. In **Patch** liegen die geprüften Kopien zusammen mit allen unveränderten Dateien in der gewohnten Ordnerstruktur. In der Spalte **Ergebnis** siehst du, welche Einträge entfernt wurden oder weshalb ein Bild unverändert blieb.

Deine Originale bleiben erhalten. Die privaten Prüfberichte liegen separat in **Patch-Protokolle**. Für einen Test mit wenigen Bildern kannst du **Nur geänderte Dateien** wählen. Möchtest du auch gespeicherte Lightroom-Regler oder Retuscheschritte entfernen, aktiviere **Auch den Bearbeitungsverlauf aus Kopien entfernen**. Sichtbare Retuschen bleiben Teil des Bildes. [Unterstützte Bearbeitungsschritte](docs/editing-history.md)

## Welche Hinweise lassen sich entfernen?

Die App kennt unter anderem KI-Quellenangaben in JPEGs und gespeicherte Generator-Einstellungen in PNGs. Ein solcher Eintrag kann die Erstellung eines ganzen Bildes oder einen einzelnen Bearbeitungsschritt betreffen. Ob eine Angabe für dein Foto zutrifft, lässt sich am besten mit der Originalaufnahme und deiner Kenntnis der Bearbeitung beurteilen. [So erkennt PhotoMetaClean die Einträge](docs/marker.md)

Auch bei HDR-Fotos kommt es auf den Aufbau der Datei an. Bei unterstützten JPEGs prüft die App die komprimierten Bilddaten, die dekodierten Pixel und das Farbprofil. Bei unterstützten HDR-JPEGs prüft sie zusätzlich das eingebettete Helligkeitsbild, die **Gain Map**. Ist der Aufbau unbekannt, enthält das Foto etwa zusätzlich ein Video oder lässt sich eine Änderung nicht sicher prüfen, kann der Eintrag erhalten bleiben. Im Sorglos-Modus bekommst du dann eine bytegleiche Kopie. RAW-Dateien werden analysiert und unverändert kopiert. [JPEG und HDR im Detail](docs/jpeg-export.md)

## Was gilt bei Herkunftsnachweisen?

Der JPEG-Export kann bei unterstützten Dateien auch einen signierten Herkunftsnachweis aus der Kopie entfernen. Damit verliert die Kopie diesen eingebetteten Nachweis. Soll er erhalten bleiben, schalte **KI-Angaben und Nachweise in JPEGs** aus. Prüfe vor der Weitergabe, welche Rechte, Kennzeichnungspflichten und Nutzungsbedingungen für dein Bild gelten. Adobe untersagt für seine generativen KI-Funktionen das Entfernen, Verändern oder Deaktivieren von Content Credentials. [Adobe-Richtlinien, Abschnitt 6](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html) · [Fotopraxis und Nutzungsrechte](docs/nutzung.md)

## Wenn nach dem Hochladen weiterhin „KI“ am Foto steht

PhotoMetaClean erkennt die im Projekt bekannten Einträge. Wasserzeichen, die in den Bildpunkten selbst stecken, liegen außerhalb dieser Prüfung. Plattformen veröffentlichen ihre Erkennungsverfahren nur teilweise. Auch nach einer erfolgreichen Dateiprüfung kann ein KI-Hinweis erscheinen. Mit **KI-Hinweis melden** kannst du einen kurzen technischen Bericht ansehen, kopieren und im Projektforum teilen. Hilfreich sind der Name der Plattform und der genaue Wortlaut des Hinweises. Behalte das Foto und die vollständigen Prüfprotokolle bei dir. [Zum Forum](https://github.com/Zimbo88/PhotoMetaClean/discussions) · [Was über Plattformkennzeichnungen bekannt ist](research/14_PLATTFORMKENNZEICHNUNG.md)

## Nutzung und Mitarbeit

Du darfst PhotoMetaClean privat und für bezahlte Fotoaufträge nutzen und deine Bilder verkaufen. Du darfst die Software unter der Projektlizenz weiterentwickeln und kostenlos weitergeben. Der Verkauf der Software ist ausgeschlossen. © 2026 Mathias Zimmermann. [Lizenz und Gewährleistung](LICENSE) · [Mitwirken](CONTRIBUTING.md) · [Datenschutz](PRIVACY.md)
