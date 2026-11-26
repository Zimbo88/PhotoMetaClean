# Adobe-Bearbeitungen und KI-Angaben / Adobe edits and AI declarations

26. November 2026 · PhotoMetaClean 0.4.0

## Deutsch

Adobe führt im KI-Bearbeitungsstatus unter anderem Entrauschen, Raw-Details, Super-Auflösung, Reflexionsentfernung, Personenentfernung und generatives Erweitern auf. Maskierung und Objektivunschärfe können ebenfalls einen Bearbeitungsstatus haben. Diese Liste beschreibt die Funktionen der Programme. Welche davon ein bestimmter Export offenlegt, hängt von Datei, Programmversion und Exportweg ab. [Adobe zu Lightroom und Camera Raw](https://helpx.adobe.com/lightroom/web/edit-photos/manage-ai-edits.html) · [Content Credentials im Lightroom-Export](https://helpx.adobe.com/lightroom/desktop/edit-photos/content-credentials-lightroom.html)

| Fundort | Was die App daraus liest |
|---|---|
| C2PA-Aktion | Aktionsname, Beschreibung, Software-Agent, digitaler Quelltyp und der Adobe-Parameter für die Camera-Raw-Aktion. Ein Hersteller kann die Beschreibung frei formulieren. |
| XMP-aux | Entrauschen, Raw-Details und Super-Auflösung. Ein ausdrücklich gesetztes Anwendungsflag, ein deaktiviertes Flag und ein gespeicherter Einstellwert erhalten verschiedene Befunde. |
| XMP-crs | Vorhandene Retuschierbereiche, Maskengruppen, Objektivunschärfe und Tiefenkarten. Diese Felder können auch bei gewöhnlicher Bearbeitung vorkommen. |
| IPTC Extension in XMP | Digitaler Quelltyp sowie die vier KI-Felder für Prompt, Promptautor, System und Systemversion. Die Übersicht meldet das Vorhandensein der Promptfelder. Die vollständigen Metadaten sind lokal einsehbar. |

Ein Beispiel aus den Forschungsbildern ist Adobes Eintrag für die generative Objektentfernung. Bei einem Nachtfoto kann dagegen ein aktiviertes Entrauschungsflag genau diesen Arbeitsschritt dokumentieren. Für generatives Füllen, Erweitern, Reflexions- oder Personenentfernung geben wir die tatsächlich gespeicherte Aktionsbeschreibung wieder, sofern sie vorhanden ist. Eine eigenständige Zuordnung eines bestimmten Byte-Musters zu jeder Adobe-Funktion oder zu einer Entscheidung von Instagram oder X ist anhand dieser Stichprobe offen. [Lokale Vergleichsergebnisse](08_ADOBE_AENDERUNGEN.md) · [C2PA-Aktionen](https://spec.c2pa.org/specifications/specifications/2.5/specs/ContentCredentials.html) · [IPTC-Felder](https://iptc.org/std/photometadata/specification/IPTC-PhotoMetadata-2025.1.html)

## English

Adobe's edit-status interface includes denoise, raw detail enhancement, super resolution, reflection and people removal, generative expansion, masking and lens blur. Individual exports can expose different records. PhotoMetaClean displays the C2PA action and its description, agent, source type and Adobe Camera Raw operation where present. In XMP it distinguishes an explicit enhancement flag from a disabled flag or a stored adjustment. Masking, depth and retouching settings alone leave the creation history open. [Adobe edit status](https://helpx.adobe.com/lightroom/web/edit-photos/manage-ai-edits.html) · [Lightroom export](https://helpx.adobe.com/lightroom/desktop/edit-photos/content-credentials-lightroom.html)

The report also identifies populated IPTC fields for the AI system, version, prompt and prompt writer. A photographer can compare these declarations with the camera original and edit history. The local set demonstrates Adobe's generative object-removal action. Other Adobe features need controlled exports to establish their precise encoding. The platform decision for a specific upload remains unknown. [IPTC standard](https://iptc.org/std/photometadata/specification/IPTC-PhotoMetadata-2025.1.html) · [IPTC source types](https://cv.iptc.org/newscodes/digitalsourcetype) · [Platform evidence](14_PLATTFORMKENNZEICHNUNG.md)

### Zusätzlicher Retuscheversuch / Additional retouch experiment

Die neue lokale Serie enthält eine Sony-RAW-Aufnahme und acht JPEGs. Fünf JPEGs enthalten in den strukturierten XMP-Retuschierbereichen die Methode `Fill_method=firefly`. In einem dieser Exporte sind sieben solcher Bereiche gespeichert, in vier Exporten jeweils acht. In allen fünf meldet das eingebettete Manifest außerdem den Agenten `Adobe Remove Object` und den Parameter `Healing changed, Uses GenAI`. Die lokale SDK-Prüfung ergab jeweils `Valid` mit unbekannter Zertifikatsvertrauenskette. Die drei übrigen JPEGs enthalten kein eingebettetes JPEG-JUMBF-Manifest. Aus der Anzahl der gespeicherten Bereiche lässt sich keine Zahl unabhängiger Bearbeitungsvorgänge ableiten.

The new local series contains one Sony RAW and eight JPEG exports. Five JPEGs declare Firefly in structured XMP retouch areas and also contain a signed generative object-removal action. The other three JPEGs have no detected embedded JUMBF manifest. The findings view counts explicit Firefly area records. The default folder workflow retains the unmodified signed image and any sidecars byte for byte. A controlled upload would be needed to observe a platform label.

Ein zusätzliches öffentliches SDK-Kontrollbild meldete in der C2PA-Aktion `c2pa.edited` den Software-Agenten Adobe Firefly und den Quelltyp für generative Bearbeitung. Die App zeigte beides an. Die konkrete Photoshop-Funktion blieb in dieser Aktion offen. Bei generativem Füllen kann Photoshop auch ein Partnermodell verwenden. [SDK-Kontrollbild](https://github.com/contentauth/c2pa-rs/blob/bf30cc5ed8785165a42e17845ffe9eb2be4d4f4e/sdk/tests/fixtures/ocsp.jpg) · [Adobe zu generativem Füllen](https://helpx.adobe.com/photoshop/desktop/create-open-import-images/create-images/edit-images-with-generative-fill.html)

An additional public SDK fixture reports Adobe Firefly as the agent of a generative edit. PhotoMetaClean shows the recorded action and source type. Identifying the specific Photoshop tool would require additional evidence. Adobe also supports partner models for Generative Fill. [Adobe documentation](https://helpx.adobe.com/photoshop/desktop/create-open-import-images/create-images/edit-images-with-generative-fill.html)
