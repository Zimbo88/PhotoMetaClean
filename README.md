# PhotoMetaClean

**Deutsch** · [English](README_EN.md)

PhotoMetaClean zeigt, welche Bearbeitung in einem Foto vermerkt ist. Mit **Kopien bereinigen** lassen sich bekannte KI-Angaben aus unterstützten JPEG-Dateien entfernen. Das funktioniert bei gewöhnlichen JPEGs und getesteten HDR-JPEGs mit Gain Map. Die App liest die geschriebene Kopie und vergleicht die Bilddaten mit dem Original.

## So geht’s

1. Lade die App für dein Betriebssystem herunter, entpacke das Paket und öffne **PhotoMetaClean**. [Downloads](https://github.com/Zimbo88/PhotoMetaClean/releases) · [Starthilfe](docs/START.md)
2. Ziehe einen Fotoordner ins Fenster und klicke auf **Kopien bereinigen**.
3. Klicke auf **Kopien anzeigen**. Im Ordner **Patch** findest du den kompletten Kundenordner. Unterordner, Begleitdateien und leere Ordner bleiben erhalten.

**Für die Weitergabe an Kunden** kannst du zusätzlich **Auch den Bearbeitungsverlauf aus Kopien entfernen** wählen. Dann entfernt die App beispielsweise gespeicherte Lightroom-Regler, Retuscheschritte oder den Namen des Bildbearbeitungsprogramms. Das Häkchen ist beim ersten Start aus. Das fertige Foto sieht bei einem geprüften Export genauso aus. [Welche Angaben die Option erfasst](docs/editing-history.md)

Der JPEG-Export kann einen eingebetteten signierten Nachweis aus der Kopie lösen. Das Original und das private Protokoll enthalten weiterhin die früheren Angaben. Verwende die Funktion nur bei entsprechender Berechtigung. Adobe untersagt das Entfernen seiner Content Credentials bei der Verwendung generativer Funktionen. [Was der JPEG-Export ändert](docs/jpeg-export.md) · [Adobe-Bedingungen](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html)

**Sorglos · kompletter Kundenordner** ist voreingestellt. Bei 100 Dateien und 42 Korrekturen liegen am Ende alle 100 Dateien in **Patch**, davon 58 als bytegenaue Kopien. Deine Originale bleiben erhalten. Steht bei einer Datei **Bitte prüfen**, schau dir das Ergebnis vor der Weitergabe an. Die privaten Prüfberichte liegen daneben in **Patch-Protokolle**. Bei einem weiteren Durchlauf entsteht **Patch-2**.

Für einen Plattformtest wähle **Nur geänderte Dateien**. Der Ausgabeordner bleibt leer, wenn keine Datei geändert wurde. Standort, Seriennummern und Kommentare bleiben standardmäßig erhalten. Unter **Weitere Werkzeuge und Bilddetails** kannst du Bilder untersuchen oder zwei Exporte vergleichen.

## Wird dein Bild weiterhin als KI markiert?

Wähle das Bild aus und klicke auf **KI-Hinweis melden**. Prüfe den kurzen Bericht, kopiere ihn und füge ihn im Projektforum ein. Hilfreich sind der Name der Plattform und der genaue Wortlaut des Hinweises. Wer eine weitere Kennzeichnung kennt oder selbst mitentwickeln möchte, ist willkommen. Du darfst PhotoMetaClean unter der Projektlizenz ändern und kostenlos weitergeben. [So erkennt die App KI-Marker](docs/marker.md) · [Zum Forum](https://github.com/Zimbo88/PhotoMetaClean/discussions) · [Mitwirken](CONTRIBUTING.md)

## Warum ich PhotoMetaClean veröffentliche

Wer nachts fotografiert, kennt den Wert einer guten Rauschreduzierung. Wenn unter so einer Aufnahme später „KI“ steht, können Kunden oder Redaktionen den Eindruck bekommen, die Szene sei am Computer erfunden worden. So ein Missverständnis kann Vertrauen und Aufträge kosten. Für Menschen, die von ihrer Fotografie leben, kann das die Existenz gefährden.

Kunden sehen am fertigen Bild selten, wie viel Arbeit in Aufnahme, Licht und Nachbearbeitung steckt. Ein pauschales Label kann gerade diese Leistung unsichtbar machen. Wer eine Nachtaufnahme entrauscht oder eine Brillenspiegelung retuschiert hat, soll nachvollziehbar erklären können, was am eigenen Foto bearbeitet wurde.

Ich möchte einige Fotografen aus meinem Umfeld dabei unterstützen, solche Fälle aufzuklären. Deshalb teile ich PhotoMetaClean. Die App soll helfen, am eigenen Foto nachzusehen, was gespeichert wurde, und eine nachweislich falsche Angabe zu korrigieren.

Adobe und die sozialen Netzwerke entwickeln ihre Verfahren weiter. Wie lange ich neue Kennzeichnungen untersuchen und die Erkennung pflegen kann, wird sich zeigen. Auch die Erkennung künftiger KI-Wasserzeichen kann ich nicht versprechen. Bitte prüfe die Ergebnisse selbst. Für die Gewährleistung gilt die [Projektlizenz](LICENSE).

## Was bedeutet ein KI-Hinweis?

Entrauschen kann eine Nachtaufnahme retten. Eine generativ aufgefüllte Spiegelung kann neue Bilddetails hinzufügen. Beides kann von einer Kameraaufnahme ausgehen. Bei den getesteten Adobe-Exporten ließ sich unter anderem eine signierte Firefly-Objektentfernung nachweisen. Die Korrektur einer falschen Quellenangabe wurde mit einer gezielt markierten Vergleichsdatei getestet.

PhotoMetaClean erkennt nur KI-Hinweise, die im Projekt bekannt sind und für die eine Erkennung eingebaut wurde. Soziale Netzwerke beschreiben einige ihrer Verfahren öffentlich. Welche Signale sie im Einzelnen prüfen und wie sie diese gewichten, ist nicht vollständig öffentlich dokumentiert. Deshalb kann ein Foto nach dem Hochladen weiterhin einen KI-Hinweis bekommen. Bitte prüfe die Kopien vor der Weitergabe. [Adobe-Versuche](research/15_ADOBE_BEARBEITUNGSSIGNALE.md) · [Plattformen und Quellen](research/14_PLATTFORMKENNZEICHNUNG.md)

## Funktioniert das auch mit HDR-Fotos?

Ja, bei unterstützten HDR-JPEGs. Diese Bilder enthalten ein zweites Bild mit Helligkeitsinformationen, die sogenannte Gain Map. Bei einer Korrektur prüft die App, dass Hauptbild, Gain Map und Farbprofile erhalten bleiben. Bei unbekanntem HDR-Aufbau wird das Foto unverändert kopiert. [Geprüfte HDR-Formate](docs/edit.md)

## Nutzung

Kostenlos für private und berufliche Fotoarbeit. Du darfst deine Bilder verkaufen. Der Verkauf der Software ist untersagt. © 2026 Mathias Zimmermann. [Lizenz und Gewährleistung](LICENSE) · [Datenschutz](PRIVACY.md)

[Unterstützte Änderungen und Bildqualität](docs/edit.md) · [Untersuchung der Adobe-Exporte](docs/ABSCHLUSSBERICHT.md) · [Kommandozeile, Build und Tests](docs/build.md)
