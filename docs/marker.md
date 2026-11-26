# Woran erkennt PhotoMetaClean KI-Hinweise?

[English](#how-does-photometaclean-recognize-ai-indicators) · Stand 26. November 2026

Die App liest die Angaben im Bild. Ein einzelner Arbeitsschritt kann generativ sein, auch wenn die Szene mit einer Kamera aufgenommen wurde. Deshalb schaut die App nach, **welches Feld** die Angabe enthält und **ob sie das ganze Bild oder eine einzelne Bearbeitung beschreibt**.

| Fund | Was die App prüft | Was beim Patchen passiert |
|---|---|---|
| IPTC-Angabe zur Bildherkunft | Im XMP-Feld `DigitalSourceType` erkennt sie bekannte IPTC-Adressen und die Kurzform wie `trainedAlgorithmicMedia`. Angaben wie `digitalCapture` und `compositeWithTrainedAlgorithmicMedia` haben jeweils eine eigene Bedeutung. | Der JPEG-Export kann erkannte KI-Quelltypen auf der Ausgabekopie entfernen. |
| Adobe Camera Raw / Lightroom | Sie unterscheidet zwischen gespeicherten Einstellungen, als angewendet gemeldeten Verbesserungen und gewöhnlicher Retusche. Bei `RetouchAreas` sucht sie nach der ausdrücklich genannten Füllmethode `firefly`. | Auf geeigneten unsignierten Kopien entfernt sie gespeicherte Werte für Entrauschungsstärke, Vergrößerungsfaktor und die Versionen von Entrauschen, Raw-Details und Super-Auflösung. In JPEG-Kopien lassen sich auch dokumentierte Firefly-Retuscheneinträge aus XMP lösen. |
| KI-Prompts in IPTC | Sie liest die Felder für Prompt, Promptautor, KI-System und Systemversion. | Einen einfachen, unsignierten Prompttext kann sie aus der Kopie entfernen. |
| PNG-Werkzeugeinstellungen | ComfyUI hinterlegt Arbeitsgraphen mit Knoten und Verbindungen. InvokeAI speichert strukturierte Bild- und Workflow-Einstellungen. Bei Einträgen im Stable-Diffusion-WebUI-Format prüft die App gemeinsam Schritte, Sampler, CFG-Skala und Seed. | Sie entfernt den vollständigen erkannten Textblock aus der Kopie, auch wenn der Text komprimiert ist. Die komprimierten Bilddaten, das Farbprofil und die dekodierten Pixel werden geprüft. |
| Software-Eintrag oder EXIF-Kommentar | Sie erkennt hinterlegte Produktnamen wie Adobe Firefly, ComfyUI oder InvokeAI im Softwarefeld und das genannte WebUI-Muster auch im EXIF-Benutzerkommentar. | Solche Angaben erscheinen im Befund. Dateinamen, Bildtitel und freie Kommentare mit dem Wort „KI“ lösen keine Generator-Erkennung aus. |
| Content Credentials / C2PA | Sie sucht nach eingebetteten Manifesten, externen Verweisen und lokalen Begleitdateien. Sie zeigt dokumentierte Aktionen und die lokal verfügbare Signaturprüfung. | Der JPEG-Export kann einen unterstützten eingebetteten Nachweis aus der Kopie lösen. Die ursprünglichen Bytes stehen im privaten Prüfprotokoll. |

Enthält ein Bild mehrere Felder, kann der Ordnerpatch die einzeln prüfbaren Angaben entfernen und ein zu komplex aufgebautes Feld erhalten. Die Ergebniszeile nennt dieses Feld. Für externe Nachweise bleibt die Datei im Prüfmodus.

Die Regeln für PNG sind an den dokumentierten Speicherformaten der Werkzeuge orientiert. Die Erkennung wird mit synthetischen Beispielen getestet. Eine bekannte IPTC-Kurzform findet sich auch im öffentlich beschriebenen Beispiel von Meta. [ComfyUI](https://github.com/Comfy-Org/ComfyUI/blob/8b0f107157b58f9ec79a19fb3182e78cb30f0a23/nodes.py) · [InvokeAI](https://github.com/invoke-ai/InvokeAI/blob/21331d5e2e97029dde9a3e211ffa88ce1a8ad044/invokeai/app/services/image_files/image_files_disk.py) · [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/82a973c04367123ae98bd9abdf80d9eda9b910e2/modules/images.py) · [IPTC-Beispiel](https://iptc.org/news/meta-announces-support-for-iptc-metadata-in-generative-ai-images/)

**Nach dem Hochladen steht noch „KI“ am Bild?** Wähle das Bild in der Ergebnisliste und klicke auf **KI-Hinweis melden**. Wähle die Plattform, lies die Vorschau und klicke auf **Bericht kopieren**. Mit **Forum öffnen** gelangst du zu GitHub Discussions. Füge den Text in einen Beitrag ein und ergänze, was die Plattform angezeigt hat und welche Kopie du hochgeladen hast. Das hilft beim Nachstellen. Das Forum ist öffentlich. Bitte teile dort nur den vorgesehenen Kurzbericht. Der vollständige lokale Bericht kann private Daten enthalten. [Zum Forum](https://github.com/Zimbo88/PhotoMetaClean/discussions)

Ein unauffälliger Befund bedeutet, dass die App in diesem Bild keine der geprüften KI-Angaben gefunden hat. Plattformen können weitere Signale auswerten. Manche Wasserzeichen stecken in den Pixeln. PhotoMetaClean untersucht Metadaten und erhält die Pixel. [Plattformrecherche](https://github.com/Zimbo88/PhotoMetaClean/blob/main/research/14_PLATTFORMKENNZEICHNUNG.md) · [SynthID](https://deepmind.google/models/synthid/)

[JPEG und HDR im Detail](jpeg-export.md)

## How does PhotoMetaClean recognize AI indicators?

Reviewed November 26, 2026. A camera photograph can contain a generative edit. The app looks at the specific metadata field and whether it describes the whole image or just one action.

| Finding | What the app looks for and can change |
|---|---|
| IPTC source type | Recognizes known IPTC URLs and short codes in the main XMP source field. JPEG export can omit supported AI source declarations from the copy. Camera capture and generative composite declarations have distinct meanings. |
| Adobe metadata | Separates settings from applied enhancements. In retouch areas it checks specifically for the Firefly fill method. Supported unsigned copies can omit the denoise amount, enlargement factor and the settings version for Denoise, Raw Details or Super Resolution. |
| IPTC AI fields | Recognizes the prompt, prompt writer, system and version. A simple unsigned prompt text can be removed. |
| PNG workflow settings | Validates structured ComfyUI graphs, InvokeAI metadata and workflows, and WebUI-style settings that include steps, sampler, CFG scale and seed. A patch removes the complete matching text chunk, including compressed records. Compressed image data, decoded pixels and the color profile are checked. |
| Product and EXIF fields | Recognizes specific software names in software fields and structured WebUI settings in the EXIF user comment. Supported simple JPEG EXIF fields and recognized PNG software fields can be cleared. Ordinary titles and comments containing “AI” do not trigger a tool match. |
| Content Credentials | Checks embedded C2PA, references and adjacent manifest files, reports actions and local signature results, and can detach a supported embedded manifest from a JPEG export while preserving its original bytes in the private journal. |

When a photo has several eligible fields, the folder patch can clear the independently verified ones and identify a complex field that must be kept for review. External credentials require review.

The upstream file writers and IPTC's illustrated example are linked above. Platforms may also evaluate other signals, including watermarks embedded in pixels. A local inspection cannot predict what a platform will display. [Platform research](https://github.com/Zimbo88/PhotoMetaClean/blob/main/research/14_PLATTFORMKENNZEICHNUNG.md) · [SynthID](https://deepmind.google/models/synthid/)

**Still labeled as AI after upload?** Select the picture, click **Report an AI label**, choose the platform and review the preview. Click **Copy report**, then **Open forum**. Paste the text into a public discussion and add the exact label and whether you uploaded the original or a saved copy. Share the short report. Your full local analysis can contain personal information. [GitHub Discussions](https://github.com/Zimbo88/PhotoMetaClean/discussions)
