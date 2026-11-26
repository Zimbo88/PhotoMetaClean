# JPEG-Struktur / JPEG structure

Die Segmentkarte erfasst Offset, Länge und SHA-256 einschließlich Markern und Segmentlängen. Sie verfolgt Scans bis zum nächsten Marker und berücksichtigt Byte-Stuffing, Restart-Marker, progressive Scans und unmittelbar anschließende JPEG-Bildströme. Verbleibende Bytes werden separat gehasht. Für Haupt- und Zusatzbilder liegen außerdem dekodierte Pixelhashes und Abmessungen vor.

Observed containers include APP1 EXIF, standard and extended XMP, APP2 ICC, MPF and ISO 21496-1, APP11 JUMBF, APP13 Photoshop and APP14 Adobe. All 51 two-stream files carry gain-map signalling. A comparison of the primary RGB pixels alone misses changes to auxiliary image data, rendering metadata and color profiles. Segment hashes preserve evidence for unknown payloads without interpreting them. This reader is an inventory tool for the observed JPEG layout. It does not simulate HDR display output.
