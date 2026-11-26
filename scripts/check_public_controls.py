"""Inspect the pinned C2PA public controls. Network access requires --fetch."""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "research/private/public-controls"
MAIN = "22beccc075707475b038d8789d0136c009e43143"
PR29 = "ae61d4c5cee15cf641cd9455916c75db81753567"
LIMIT = 4 * 1024 * 1024
# Relative paths mirror upstream. The pr29 prefix isolates the second revision.
FILES = {
    "LICENSE": "23ee78c8bae49cf08ea2f0c84945c66b987ebe4520881fb51b3dad4fb43d07c2",
    "README.md": "e78fd8ff4b6c0cd9ec5dac9a011e67ce44c98444e9787b47aaef88c8b8e7663f",
    "legacy/1.4/image/README.md": "68d283e92f8b943d782ae589011e767f3dec5aebae83f95f6f8c77672b7dc6b8",
    "legacy/1.4/image/jpeg/adobe-20220124-A.jpg": "f999fd78bfe8a83c96e468a078830ba94485bc1bc6fd086fb94a43bd29dd0f23",
    "legacy/1.4/image/jpeg/adobe-20220124-CA.jpg": "cafc48c53e651f7ba4622d1f72783827074211e42b9634cc863ec3be3c7651b3",
    "legacy/1.4/image/jpeg/adobe-20220124-E-sig-CA.jpg": "0d4c2774f1b7e94b9613bb952b0a76b6a178d22ac6d206d257d2af1376cbbff2",
    "legacy/1.4/image/jpeg/adobe-20220124-E-dat-CA.jpg": "dae9d121060cec4b6f27ee8acda85ad461cf75f2261d90b463319b787342d7f9",
    "legacy/1.4/image/jpeg/truepic-20230212-camera.jpg": "379aabc7d04ee8c8fb04e18925428463353ab6fb6696ee3d7aa11710c6b2e147",
    "pr29/samples.json": "c89dd00fe74b339aec3ce280477bf8607b15d58cec235ac42b9429760f0eba23",
    "pr29/README.md": "e78fd8ff4b6c0cd9ec5dac9a011e67ce44c98444e9787b47aaef88c8b8e7663f",
    "pr29/LICENSE": "23ee78c8bae49cf08ea2f0c84945c66b987ebe4520881fb51b3dad4fb43d07c2",
    "pr29/2.2/image/good/jpeg/a.jpg": "1994444eeec5d30a90e52f793f2764aa51e164a10334c60b991444369ccd30c6",
    "pr29/2.2/image/good/jpeg/b.jpg": "d949c56121ddbbc39ce05c8520816e531281aedb9d6ab345bb31db044fcacaeb",
}


def cache_path(name):
    path = CACHE / name
    if path.resolve() != path:
        raise ValueError(f"Unexpected cache symlink: {name}")
    return path


def publish_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
    try:
        temp.write_bytes(data)
        try:
            os.link(temp, path)
        except FileExistsError:
            pass  # The caller also verifies the winning file.
    finally:
        temp.unlink(missing_ok=True)


def verify(name):
    path = cache_path(name)
    if not path.is_file():
        raise ValueError(f"Missing {name}. Populate the cache with --fetch.")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT or hashlib.sha256(data).hexdigest() != FILES[name]:
        raise ValueError(f"SHA-256 mismatch: {name}")


def prepare(fetch):
    for name, expected in FILES.items():
        target = cache_path(name)
        if fetch and not target.exists():
            rev = PR29 if name.startswith("pr29/") else MAIN
            source = name.removeprefix("pr29/")
            url = f"https://raw.githubusercontent.com/c2pa-org/public-testfiles/{rev}/{source}"
            with urlopen(url, timeout=30) as stream:
                data = stream.read(LIMIT + 1)
            if len(data) > LIMIT or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Download failed SHA-256 verification: {name}")
            publish_new(target, data)
        verify(name)
    expected_list = "".join(f"{digest}  {name}\n" for name, digest in FILES.items()).encode()
    sums = cache_path("SHA256SUMS")
    if fetch and not sums.exists():
        publish_new(sums, expected_list)
    if not sums.is_file() or sums.read_bytes() != expected_list:
        raise ValueError("SHA256SUMS is missing or differs from the pinned inventory")


def inspect(name):
    from photometaclean.core.edit import plan
    from photometaclean.metadata.analysis import analyze

    path = cache_path(name)
    result = analyze(path)
    store = result.get("manifest", {})
    checks = store.get("validation_results", {}).get("activeManifest", {})
    histories = []
    for label, manifest in store.get("manifests", {}).items():
        steps = []
        for assertion in manifest.get("assertions", []):
            if assertion["label"].startswith("c2pa.actions"):
                for step in assertion["data"]["actions"]:
                    steps.append([step["action"], step.get("digitalSourceType")])
        histories.append({"active": label == store["active_manifest"], "actions": steps})
    try:
        plan(path, {"JPEG:Comment": None})
        preview = "available"
    except ValueError as exc:
        preview = str(exc)
    verify(name)
    if result["sha256"] != FILES[name] or result.get("validation_error"):
        raise ValueError(f"Incomplete analysis: {name}")
    binding = [{"code": item["code"], "explanation": item.get("explanation")}
               for group in checks.values() for item in group
               if item["code"].startswith("assertion.dataHash.")]
    return {"file": name, "model": result["metadata"].get("IFD0:Main:Model"),
            "resolution": result["resolution"], "pixels": result["frames"][0]["pixels"],
            "jpeg_streams": len(result["codestreams"]), "data_hash_checks": binding,
            "signature": result["signature"], "location": result.get("manifest_location"),
            "active_checks": {level: sorted({item["code"] for item in entries})
                              for level, entries in checks.items()},
            "histories": histories, "classification": result["classification"],
            "preview_comment": preview}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="fetch missing pinned files over HTTPS")
    args = parser.parse_args()
    prepare(args.fetch)
    report = [inspect(name) for name in FILES if name.endswith(".jpg")]
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ImportError) as exc:
        sys.exit(str(exc).replace(str(ROOT), "."))
