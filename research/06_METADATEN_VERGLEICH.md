# Paarvergleich / Pair comparison

Fünf Bildpaare wurden eindeutig nach den implementierten Regeln zugeordnet. Vier weitere Kandidaten blieben unsicher. Damit haben 27 Vorher- und 25 Nachher-Dateien keinen eindeutigen Partner. Alle fünf zugeordneten Paare haben identische Abmessungen und unterschiedliche dekodierte Hauptbildpixel. Keines der zehn Paardokumente enthält einen eingebetteten JPEG-JUMBF-Container.

The matcher compares every cross-folder combination. It measures mean absolute luminance difference on orientation-corrected 16×16 thumbnails. A distance up to 25 or equal filename stem or capture timestamp admits a candidate. Equal primary frame records, or distance up to 8 plus a matching stem or capture timestamp, give strong evidence. Only strong edges unique at both ends are accepted. These thresholds are heuristics. Repeated exports, crops, exposure changes and burst sequences can defeat them.

Private pairs.json records evidence for all candidates and added, removed and changed group-qualified metadata for matched and independently corroborated candidates. Structure comparisons include both segment maps, decoded streams, signatures and manifests. pairs.csv indexes candidates. unmatched.json lists all files without an accepted partner. ExifTool System and SourceFile values describe the filesystem and are excluded when interpreting Adobe changes.
