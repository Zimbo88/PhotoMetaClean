"""Synthetic XMP packets exercise namespace resolution and exact byte offsets."""
from xml.etree import ElementTree

import pytest

from photometaclean.formats.xmp import FIELDS, locations

FIELD = "XMP-iptcExt:DigitalSourceType"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
IPTC = "http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
MM = "http://ns.adobe.com/xap/1.0/mm/"
VALUE = "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"


def packet(body, attributes="", subject='r:about=""'):
    return (f'<x:xmpmeta xmlns:x="adobe:ns:meta/"><r:RDF xmlns:r="{RDF}" xmlns:i="{IPTC}">'
            f'<r:Description {subject} {attributes}>{body}</r:Description>'
            '</r:RDF></x:xmpmeta>').encode()


@pytest.mark.parametrize("prop", [
    f'<i:DigitalSourceType>{VALUE}</i:DigitalSourceType>',
    f'<DigitalSourceType xmlns="{IPTC}">{VALUE}</DigitalSourceType >',
    f'<π:DigitalSourceType xmlns:π="{IPTC}" r:resource =\n\'{VALUE}\'  />',
    f'<i:DigitalSourceType xmlns:p="{RDF}" p:resource="{VALUE}">\r\n </i:DigitalSourceType>',
])
def test_simple_property_exact_span(prop):
    # Same bytes in a comment, non-ASCII prefix bytes and an adjacent sibling.
    history = f'<m:History xmlns:m="{MM}">Frühere Änderungen</m:History>'
    data = packet(f'<!--{prop}-->{history}{prop}<other/>')
    start = data.rindex(prop.encode())
    end = start + len(prop.encode())
    assert locations(data, [FIELD]) == [(FIELD, start, end, VALUE)]
    edited = data[:start] + b" " * (end - start) + data[end:]
    assert len(edited) == len(data)
    assert locations(edited, [FIELD]) == []
    assert ElementTree.fromstring(edited).find(f".//{{{MM}}}History").text == "Frühere Änderungen"


@pytest.mark.parametrize("prop", [
    '<i:DigitalSourceType/>',
    '<i:DigitalSourceType r:resource=" "/>',
    '<i:DigitalSourceType> \n </i:DigitalSourceType>',
    '<i:DigitalSourceType>one two</i:DigitalSourceType>',
    '<i:DigitalSourceType r:resource="one">two</i:DigitalSourceType>',
    '<i:DigitalSourceType><r:Bag><r:li>one</r:li></r:Bag></i:DigitalSourceType>',
    '<i:DigitalSourceType r:parseType="Resource"><r:value>one</r:value></i:DigitalSourceType>',
    '<i:DigitalSourceType xml:lang="en">one</i:DigitalSourceType>',
    '<i:DigitalSourceType other="qualified" r:resource="one"/>',
    '<i:DigitalSourceType resource="wrong-namespace"/>',
    '<i:DigitalSourceType xmlns:r="urn:other" r:resource="wrong-namespace"/>',
    '<i:DigitalSourceType>one<!--retain history--></i:DigitalSourceType>',
    '<i:DigitalSourceType><?keep info?>one</i:DigitalSourceType>',
    '<i:DigitalSourceType><![CDATA[one]]></i:DigitalSourceType>',
    '<other><i:DigitalSourceType>one</i:DigitalSourceType></other>',
    '<r:Description i:DigitalSourceType="elsewhere"/>',
])
def test_non_simple_properties_are_refused(prop):
    with pytest.raises(ValueError):
        locations(packet(prop), [FIELD])


@pytest.mark.parametrize("content,attributes", [
    ('<i:DigitalSourceType>one</i:DigitalSourceType>', 'i:DigitalSourceType="one"'),
    ('<i:DigitalSourceType>one</i:DigitalSourceType><i:DigitalSourceType r:resource="two"/>', ''),
    ('<i:DigitalSourceType>one</i:DigitalSourceType></r:Description>'
     '<r:Description i:DigitalSourceType="two">', ''),
])
def test_repeated_field_requires_review(content, attributes):
    with pytest.raises(ValueError, match="Repeated"):
        locations(packet(content, attributes), [FIELD])


@pytest.mark.parametrize("subject", ['r:about="urn:other"', 'r:about="DJI Meta Data"',
                                     'r:ID="other"', 'r:nodeID="other"'])
def test_references_to_other_subjects_are_protected(subject):
    with pytest.raises(ValueError):
        locations(packet('<i:DigitalSourceType>one</i:DigitalSourceType>', subject=subject), [FIELD])


@pytest.mark.parametrize("sibling,before", [
    (b'<r:Description r:about="other"/>', True),
    (b'<r:Description r:about="other"/>', False),
    (b'<p:Camera xmlns:p="urn:other"/>', False),
])
def test_dji_privacy_requires_a_single_top_level_subject(sibling, before):
    field = "XMP-aux:SerialNumber"
    uri, local = FIELDS[field]
    raw = packet("", f'xmlns:a="{uri}" a:{local}="example"', 'r:about="DJI Meta Data"')
    at = raw.index(b"<r:Description" if before else b"</r:RDF>")
    with pytest.raises(ValueError, match="single top-level"):
        locations(raw[:at] + sibling + raw[at:], [field])


@pytest.mark.parametrize("subject", ['r:about="unrelated"', 'r:about="DJI Meta Data" r:nodeID="other"',
                                     'r:about="DJI Meta Data" r:ID="other"'])
def test_privacy_on_other_or_ambiguous_subjects_requires_review(subject):
    field = "XMP-aux:SerialNumber"
    uri, local = FIELDS[field]
    with pytest.raises(ValueError, match="unrelated"):
        locations(packet("", f'xmlns:a="{uri}" a:{local}="example"', subject), [field])


def test_dji_privacy_does_not_reach_nested_records():
    field = "XMP-aux:SerialNumber"
    uri, local = FIELDS[field]
    child = f'<ref><r:Description r:about="DJI Meta Data" xmlns:a="{uri}" a:{local}="example"/></ref>'
    with pytest.raises(ValueError, match="Nested"):
        locations(packet(child, subject='r:about="DJI Meta Data"'), [field])


def test_top_level_means_rdf_document_or_xmp_envelope():
    raw = packet('<i:DigitalSourceType>one</i:DigitalSourceType>')
    with pytest.raises(ValueError):
        locations(b'<attachment>' + raw + b'</attachment>', [FIELD])


@pytest.mark.parametrize("qualifier", [b'xml:base="https://example.invalid/other"', b'xml:lang="de"'])
def test_inherited_qualifier_requires_review(qualifier):
    raw = packet('<i:DigitalSourceType>relative</i:DigitalSourceType>')
    with pytest.raises(ValueError, match="Inherited"):
        locations(raw.replace(b'<r:RDF ', b'<r:RDF ' + qualifier + b' '), [FIELD])


def test_rebound_namespace_does_not_mask_attribute_or_extend_its_range():
    raw = packet('<i:DigitalSourceType xmlns:i="urn:else">other</i:DigitalSourceType>',
                 'xmlns:π="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" π:DigitalSourceType="one"')
    field, start, end, old = locations(raw, [FIELD])[0]
    assert (field, old, raw[start:end]) == (FIELD, "one", ' π:DigitalSourceType="one"'.encode())


def test_namesake_fields_and_provenance_outside_the_namespaces_are_ignored():
    data = packet('<else xmlns:i="urn:other" i:DigitalSourceType="other" i:provenance="other">'
                  '<i:DigitalSourceType>other</i:DigitalSourceType></else>'
                  '<DigitalSourceType>other</DigitalSourceType>')
    assert locations(data, [FIELD]) == []


@pytest.mark.parametrize("body,attr", [
    ('<ref:provenance r:resource="https://example.invalid/store"/>', 'xmlns:ref="http://purl.org/dc/terms/"'),
    ('', f'xmlns:m="{MM}" m:Provenance="https://example.invalid/store"'),
    (f'<Manifest xmlns="{MM}"/>', ''),
    ('<sig:Signature xmlns:sig="http://www.w3.org/2000/09/xmldsig#"/>', ''),
])
def test_provenance_holds_entire_packet_even_for_jpeg_comment_edits(body, attr):
    with pytest.raises(ValueError, match="provenance"):
        locations(packet(body, attr), [])


@pytest.mark.parametrize("key", [key for key in FIELDS if key != FIELD])
def test_simple_privacy_elements_and_opaque_structures(key):
    uri, local = FIELDS[key]
    prop = f'<e:{local} xmlns:e="{uri}">synthetic value</e:{local}>'
    data = packet(prop)
    start = data.index(prop.encode())
    assert locations(data, [key]) == [(key, start, start + len(prop.encode()), "synthetic value")]
    for complex_value in (prop.replace("synthetic value", "<nested/>"),
                          prop.replace("xmlns:e=", 'xml:lang="en" xmlns:e=')):
        with pytest.raises(ValueError):
            locations(packet(complex_value), [key])
