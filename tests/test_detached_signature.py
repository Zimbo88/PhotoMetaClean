"""Create an ephemeral certificate chain and a detached manifest entirely offline."""
import io
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import c2pa
from PIL import Image
import pytest

from photometaclean.core.edit import plan
from photometaclean.metadata.analysis import analyze
from photometaclean.metadata.provenance import OFFLINE


@pytest.mark.parametrize("embed", [False, True])
def test_manifest_binds_the_exact_asset(tmp_path, embed):
    openssl = shutil.which("openssl")
    if not openssl or not subprocess.check_output([openssl, "version"]).startswith(b"OpenSSL 3."):
        pytest.skip("Synthetic certificate creation uses the OpenSSL 3 CLI")

    with TemporaryDirectory(dir=tmp_path) as keys:
        directory = Path(keys)

        def run(*args):
            subprocess.run([openssl, *args], cwd=directory, capture_output=True, check=True)

        key_args = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes", "-sha256"]
        run("req", "-new", "-x509", *key_args, "-subj", "/CN=Test issuer", "-days", "1",
            "-keyout", "ca.key", "-out", "ca.pem", "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign")
        run("req", "-new", *key_args, "-subj", "/CN=Test signer", "-keyout", "leaf.key", "-out", "leaf.csr")
        (directory / "extensions").write_text(
            "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\n"
            "extendedKeyUsage=emailProtection\nauthorityKeyIdentifier=keyid\nsubjectKeyIdentifier=hash\n")
        run("x509", "-req", "-in", "leaf.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-set_serial", "2",
            "-days", "1", "-sha256", "-extfile", "extensions", "-out", "leaf.pem")
        chain = (directory / "leaf.pem").read_bytes() + (directory / "ca.pem").read_bytes()
        info = c2pa.C2paSignerInfo("es256", chain, (directory / "leaf.key").read_bytes(), None)
        claim = {
            "claim_generator_info": [{"name": "PhotoMetaClean test"}], "format": "image/jpeg",
            "assertions": [{"label": "c2pa.actions.v2", "data": {"actions": [{"action": "c2pa.created",
                "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"}]}}],
        }
        raw, output = io.BytesIO(), io.BytesIO()
        Image.new("RGB", (8, 8), "blue").save(raw, "JPEG")
        raw.seek(0)
        with (c2pa.Context.from_dict(OFFLINE) as context, c2pa.Signer.from_info(info) as signer,
              c2pa.Builder(claim, context=context) as builder):
            if not embed:
                builder.set_no_embed()
            detached = builder.sign(signer, "image/jpeg", raw, output)

    photo = tmp_path / "control.jpg"
    photo.write_bytes(output.getvalue())
    if embed:
        from photometaclean.core.patch import patch_file
        from photometaclean.formats.share import EXPORT
        import base64
        original = photo.read_bytes()
        dest = tmp_path / "out.jpg"
        record = patch_file(photo, dest, {EXPORT}, False, camera_confirmation="Export of our synthetic test asset")
        assert "postcheck" in record, record.get("reason")
        assert record["postcheck"]["state"] == "clear" and not record["postcheck"]["provenance"]
        recovered = bytearray(dest.read_bytes())
        for piece in reversed(record["audit"]["recovery"]):
            pos = piece["output_offset"]
            recovered[pos:pos+piece["output_length"]] = base64.b64decode(piece["original_base64"])
        assert bytes(recovered) == photo.read_bytes() == original and dest.read_bytes() != original
        assert record["audit"]["integrity_before"] == record["audit"]["integrity_after"]
        return
    photo.with_suffix(".c2pa").write_bytes(detached)
    confirmed = analyze(photo)
    assert confirmed["manifest_location"] == "sidecar"
    assert confirmed["signature"] == "Valid"
    assert confirmed["validation_failures"] == ["signingCredential.untrusted"]
    with pytest.raises(ValueError, match="External manifest"):
        plan(photo, {"JPEG:Comment": None})

    Image.new("RGB", (8, 8), "red").save(photo)
    mismatched = analyze(photo)
    assert mismatched["signature"] == "Invalid"
    assert "assertion.dataHash.mismatch" in mismatched["validation_failures"]
