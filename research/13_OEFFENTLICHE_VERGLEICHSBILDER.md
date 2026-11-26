# Öffentliche Vergleichsbilder / Public control images

## Befunde vom 26. November 2026

Sieben JPEGs dienen als unabhängige Kontrollen für die Herkunftsanalyse. Bei zwei Google-Beispielen lässt sich anhand der Manifestkette unterscheiden, ob ein Modell das Ausgangsbild erzeugt hat oder ob eine Kameraaufnahme später generativ bearbeitet wurde. Alle Angaben zur Entstehung stammen aus Deklarationen. Die Kontrollen sind weder ein kontrolliertes Lightroom-Update-Experiment noch ein Test der Kennzeichnung durch Instagram oder Facebook.

| Anbieter und Datei | Befund aus den lokalen Bytes | C2PA-Prüfung |
|---|---|---|
| Adobe · `adobe-20220124-A.jpg` | EXIF nennt Canon EOS REBEL T3. Der Export nennt Lightroom 5.3. Kein eingebetteter JPEG-JUMBF-Container gefunden. | Keine eingebettete Signatur geprüft. |
| Adobe · `adobe-20220124-CA.jpg` | Das aktive Manifest nennt Öffnen und Farbkorrektur. Als Generator steht dort `make_test_images`. | `Valid`. Claim-Signatur und Dateibindung bestätigt. |
| Adobe · `adobe-20220124-E-sig-CA.jpg` | Die dekodierten Hauptbildpixel stimmen mit der CA-Kontrolle überein. | `Invalid`. Claim-Signatur fehlerhaft, Dateibindung bestätigt. |
| Adobe · `adobe-20220124-E-dat-CA.jpg` | Dieselben Hauptbildpixel wie bei CA. | `Invalid`. Claim-Signatur bestätigt, Dateibindung fehlerhaft. |
| Truepic · `truepic-20230212-camera.jpg` | Aufnahmekontrolle mit Pixel 5 in EXIF und Kameraangaben im Manifest. | `Invalid`. Claim-Signatur bestätigt. Der SDK bestätigt den Datenhash und beanstandet zugleich, dass der vom Hash ausgenommene Bereich nicht zur Manifestposition passt. |
| Google LLC · `a.jpg` | Vier Manifeste. Frühere Erstellungsaktionen nennen `trainedAlgorithmicMedia`. Das aktive Manifest nennt eine Transkodierung mit `algorithmicallyEnhanced`. | `Valid`. Claim-Signatur und Dateibindung bestätigt. |
| Google LLC · `b.jpg` | Drei Manifeste dokumentieren Pixel-Kameraaufnahme (`computationalCapture`), Beschnitt (`humanEdits`) und im aktiven Manifest generative Bearbeitung (`compositeWithTrainedAlgorithmicMedia`). | `Invalid`. Dateibindung bestätigt. Das aktive Signaturzertifikat wird lokal als abgelaufen gemeldet. |

Alle sechs eingebetteten Manifestspeicher melden beim aktiven Manifest `signingCredential.untrusted`. Der SDK unterscheidet kryptografische Prüfung und Vertrauen in den Unterzeichner. Bei Google `a.jpg` enthält die kurze Klassifikationsliste von `analyze()` nur die aktive Transkodierung. Die Erzeugungsdeklaration ist im vollständigen Manifestspeicher lesbar. Bei `b.jpg` findet der JPEG-Parser zwei Bildströme. Pillow warnt beim Öffnen vor einer fehlerhaften MPO-Struktur und liest das Hauptbild als JPEG.

Für jedes Bild wurde dieselbe unverbindliche Vorschau mit `plan(path, {"JPEG:Comment": None})` berechnet. Der Herkunftsschutz sperrte alle sechs Dateien mit Manifest. Bei Adobe A fehlte ein befüllter JPEG-Kommentar. Die sieben Datei-Hashes stimmten auch nach der Prüfung. Eine zutreffende Bearbeitungsangabe zu entfernen war kein Bestandteil des Versuchs.

**Separate Manifeste.** Die Suche in den Dateibäumen und der erreichbaren Historie der 15 Branches und 26 Pull-Request-Referenzen dieses Repositorys ergab keine eigenständige Datei mit Endung `.c2pa`. Die veröffentlichten JSON-Manifestauszüge sind Berichte. Diese Stichprobe liefert daher keinen Praxistest des Validators für ein Bild mit separat ausgeliefertem Binärmanifest.

## Findings on 26 November 2026

The seven controls exercise capture, editing, declared generation and independent signature failure modes. The histories below are claims recorded in the assets. The collection establishes neither a change between Lightroom versions nor a social platform's labelling decision.

| Contributor and control | Local observation |
|---|---|
| Adobe A | Canon EOS REBEL T3 and Lightroom 5.3 metadata. No embedded JPEG JUMBF container detected. |
| Adobe CA | The test generator declares opening and colour adjustment. The active claim signature and asset binding pass. SDK state `Valid`. |
| Adobe E-sig-CA | The active claim signature fails and the asset binding passes. SDK state `Invalid`. |
| Adobe E-dat-CA | The active claim signature passes and the asset binding fails. SDK state `Invalid`. The three CA variants have identical decoded primary pixels. |
| Truepic camera | Pixel 5 EXIF and capture assertions. The active signature passes. The SDK reports a matching data hash together with an exclusion range inconsistent with the manifest location. Overall state `Invalid`. |
| Google a | Four manifests. Earlier creation actions declare model generation. The active claim covers a later transcode. Reading only the active source type misses the declaration of generation. Signature and binding pass, state `Valid`. |
| Google b | Three manifests declare computational camera capture, human cropping and a generative edit. Local validation reports a matching asset binding and an expired active signing credential, state `Invalid`. Pillow warns about malformed MPO structure. The JPEG parser finds two codestreams. |

All six active manifests report an untrusted signing credential under the local settings. The same JPEG-comment removal preview was refused on all six provenance-bearing files. Adobe A lacked a populated JPEG comment. All seven input digests matched after inspection. The upstream branch and pull-request histories inspected contained no standalone `.c2pa` file. A real detached asset/manifest pair remains outside this control set.

## Quellen und Nutzungsrechte / Sources and licence

- **Adobe und Truepic / Adobe and Truepic.** Fünf unveränderte JPEGs aus dem Hauptzweig / five unmodified JPEGs from the main branch. Commit `22beccc075707475b038d8789d0136c009e43143`, Verzeichnis / directory `legacy/1.4/image/jpeg/`. Die Bilddokumentation beschreibt die vorgesehenen Positiv- und Fehlerfälle / the image guide describes the intended positive and negative cases. [Bildkatalog / Image catalogue](https://github.com/c2pa-org/public-testfiles/blob/22beccc075707475b038d8789d0136c009e43143/legacy/1.4/image/README.md) · [Quellen / Input files](https://github.com/c2pa-org/public-testfiles/tree/22beccc075707475b038d8789d0136c009e43143/legacy/1.4/image/jpeg)
- **Google LLC.** Zwei unveränderte JPEGs aus einem vorgeschlagenen Beitrag desselben Repositorys / two unmodified JPEGs from a proposed contribution to the same repository. Commit `ae61d4c5cee15cf641cd9455916c75db81753567`, Verzeichnis / directory `2.2/image/good/jpeg/`. Die Anbieterbeschreibung lässt sich mit den lokal extrahierten Aktionen vergleichen / the contributor's description can be checked against the extracted actions. [Pull Request 29](https://github.com/c2pa-org/public-testfiles/pull/29) · [Katalog / Catalogue](https://github.com/c2pa-org/public-testfiles/blob/ae61d4c5cee15cf641cd9455916c75db81753567/samples.json) · [Quellen / Input files](https://github.com/c2pa-org/public-testfiles/tree/ae61d4c5cee15cf641cd9455916c75db81753567/2.2/image/good/jpeg)
- **CC BY-SA 4.0 International.** Beide Quellstände enthalten dieselbe Lizenz. Lizenztext und README beider Stände werden mitgesichert. Bei Weitergabe sind Namensnennung, Lizenzverweis, Kennzeichnung von Änderungen und gegebenenfalls Weitergabe unter gleichen Bedingungen zu beachten. Both revisions include the same licence. The cache retains each revision's README and licence. Redistribution requires attribution, a licence reference, identification of changes and share-alike for adaptations. [Lizenz im Hauptzweig / Main licence](https://github.com/c2pa-org/public-testfiles/blob/22beccc075707475b038d8789d0136c009e43143/LICENSE) · [Lizenz im Google-Beitrag / Contribution licence](https://github.com/c2pa-org/public-testfiles/blob/ae61d4c5cee15cf641cd9455916c75db81753567/LICENSE)

## Prüfsummen / Input SHA-256

| Datei / File | SHA-256 |
|---|---|
| `adobe-20220124-A.jpg` | `f999fd78bfe8a83c96e468a078830ba94485bc1bc6fd086fb94a43bd29dd0f23` |
| `adobe-20220124-CA.jpg` | `cafc48c53e651f7ba4622d1f72783827074211e42b9634cc863ec3be3c7651b3` |
| `adobe-20220124-E-sig-CA.jpg` | `0d4c2774f1b7e94b9613bb952b0a76b6a178d22ac6d206d257d2af1376cbbff2` |
| `adobe-20220124-E-dat-CA.jpg` | `dae9d121060cec4b6f27ee8acda85ad461cf75f2261d90b463319b787342d7f9` |
| `truepic-20230212-camera.jpg` | `379aabc7d04ee8c8fb04e18925428463353ab6fb6696ee3d7aa11710c6b2e147` |
| `a.jpg` | `1994444eeec5d30a90e52f793f2764aa51e164a10334c60b991444369ccd30c6` |
| `b.jpg` | `d949c56121ddbbc39ce05c8520816e531281aedb9d6ab345bb31db044fcacaeb` |

## Reproduktion / Reproduction

Im Repository-Hauptverzeichnis mit installiertem ExifTool und der Projektumgebung aus dem README ausführen. Getestet unter Linux mit Python 3.14.4, ExifTool 13.50, c2pa-python 0.39.0 und Pillow 12.1.1. Prüfzeitpunkt, Vertrauenskonfiguration und SDK-Version können Zertifikatsbefunde beeinflussen.

Run from the repository root with ExifTool on PATH and the project environment installed as described in the README. The recorded Linux environment used Python 3.14.4, ExifTool 13.50, c2pa-python 0.39.0 and Pillow 12.1.1. Validation time, trust settings and SDK version can affect certificate results. [Deutsch](../README.md) · [English](../README_EN.md)

**Einmaliger Bezug / One-time retrieval.** Das versionierbare Skript prüft alle sieben Bilder und sechs Dokumentationsdateien einschließlich der Lizenztexte gegen die eingebauten SHA-256-Werte. Der gesamte Cache einschließlich `SHA256SUMS` liegt im Git-ignorierten Ordner. The script fetches only pinned inputs missing from the cache, verifies bytes before saving and refuses a mismatched existing file. An intact cache can also be copied to the same relative directory on an offline machine. [Skript / Script](../scripts/check_public_controls.py)

```sh
.venv/bin/python scripts/check_public_controls.py --fetch
```

**Offline wiederholen / Repeat offline.** Ohne Schalter verwendet das Skript ausschließlich lokale Dateien. `analyze()` liest Metadaten und prüft eingebettete Herkunftsangaben ohne Netzwerkzugriff. `plan()` prüft nur die Vorschau. Der JSON-Bericht enthält relative Dateinamen, aktive Prüfmeldungen und Aktionen auch aus früheren Manifesten. Run without arguments to verify the cache and repeat the analysis and preview offline. The JSON summary includes relative input names, active validation results and historical actions. No image output or upload is involved.

```sh
(cd research/private/public-controls && sha256sum --check SHA256SUMS)
.venv/bin/python scripts/check_public_controls.py > research/private/public-controls/summary.json
```

Der Erstbezug wurde mit leerem Cache geprüft. Eine manipulierte lokale Testkopie führte zum Prüfsummenabbruch. Ein zweiter Analyselauf unter Linux mit per seccomp gesperrten Netzwerk-Sockets lieferte für alle sieben Bilder denselben JSON-Inhalt.

An empty-cache retrieval passed. A deliberately corrupted temporary copy was rejected by its checksum. A second Linux analysis run with network sockets denied by seccomp reproduced the JSON results for all seven images.

### Umsetzung im Herkunftsbefund / Implementation in the findings view

Die Ansicht `explain` in Version 0.2.0 zeigt zusätzlich zur aktiven Aktion die deklarierten Schritte eindeutig verknüpfter Vorgänger. Bei Google A erscheint im Abschnitt „Frühere Exporte“ die Erzeugung mit trainiertem Modell. Bei Google B erscheinen der Beschnitt und die Mehrbild-Kameraaufnahme. Die Zertifikats- und Dateibindungsanzeige bezieht sich auf das aktive Manifest. Der separate Sidecar-Test erzeugt sein eigenes JPEG und Binärmanifest mit kurzlebigen lokalen Testschlüsseln. Er prüft die passende Datei und anschließend eine ausgetauschte Datei mit fehlschlagender Bindung.

Run `photometaclean explain IMAGE --lang en` for active and linked parent claims. Only explicit, unambiguous parent relationships are followed. A separate synthetic test exercises detached-manifest verification, including mismatched image bytes. [Sidecar test](../tests/test_detached_signature.py)
