import pytest
from photometaclean.metadata.classification import SOURCE_TYPES, interpret


@pytest.mark.parametrize("term", SOURCE_TYPES)
def test_declaration_is_not_verified_history(term):
    result = interpret({"XMP-iptcExt:DigitalSourceType":
                        "http://cv.iptc.org/newscodes/digitalsourcetype/" + term})
    assert result["declarations"][0]["meaning"] == SOURCE_TYPES[term]
    assert result["creation_history"] == "unverified"


def test_software_alone_is_insufficient():
    assert not interpret({"IFD0:Software": "Adobe Photoshop"})["declarations"]


def test_conflicting_fields():
    result = interpret({"a:DigitalSourceType": "unknown", "b:DigitalSourceType": "other"})
    assert result["review_multiple_declarations"]
