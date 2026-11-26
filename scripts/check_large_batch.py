"""Exercise the CLI with generated high-ISO-like noise and a nested JPEG batch."""
import argparse
import hashlib
import json
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from time import monotonic

from PIL import Image

from photometaclean.cli.app import main as cli


def make_large(path):
    random = Random(430)
    width = height = 10_000
    with Image.new("RGB", (width, height)) as image:
        for top in range(0, height, 50):
            strip = Image.frombytes("RGB", (width, 50), random.randbytes(width * 50 * 3))
            image.paste(strip, (0, top))
        image.save(path, quality=100, subsampling=0, comment=b"synthetic comment")


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(source, work, count):
    report = work / "edit.jsonl"
    output = work / "copies"
    started = monotonic()
    status = cli(["edit", str(source), "--changes", '{"JPEG:Comment":null}',
                  "--apply", "--output", str(output), "--report", str(report)])
    if status:
        raise RuntimeError("CLI reported one or more failed edits")
    elapsed = monotonic() - started
    verified = 0
    with report.open(encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if "result" not in row:
                continue
            audit = row["result"]["audit"]
            origin = Path(audit["source"])
            copy = output / origin.relative_to(source)
            journal = Path(row["result"]["journal"])
            assert not journal.is_relative_to(output)
            entries = [json.loads(s)["state"] for s in journal.read_text(encoding="utf8").splitlines()]
            if (file_hash(origin) != audit["source_sha256"] or file_hash(copy) != audit["output_sha256"]
                    or audit["integrity_after"] != audit["integrity_before"]
                    or entries != ["approved", "verified"]):
                raise RuntimeError("Independent file, journal or integrity check failed")
            verified += 1
    if verified != count:
        raise RuntimeError("Batch count mismatch")
    print(f"{verified} verified copies in {elapsed:.2f} s")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["large", "batch"])
    parser.add_argument("--files", type=int, default=2000, help="Number of files in batch mode")
    args = parser.parse_args()
    if args.files < 1:
        parser.error("--files must be positive")
    with TemporaryDirectory() as tmp:
        work = Path(tmp).resolve()
        source = work / "inputs"
        source.mkdir()
        if args.case == "large":
            photo = source / "100MP.jpg"
            make_large(photo)
            report = work / "read.jsonl"
            if cli(["analyze", str(photo), "--workers", "1", "--report", str(report)]):
                raise RuntimeError("Large-photo analysis failed")
            row = json.loads(report.read_text(encoding="utf8"))["analysis"]
            if row["resolution"] != [10_000, 10_000] or row["sha256"] != file_hash(photo):
                raise RuntimeError("Unexpected resolution or source digest")
            print(f'{row["size"]} bytes, 100 megapixels')
            check(source, work, 1)
        else:
            for index in range(args.files):
                folder = source / str(index // 100)
                folder.mkdir(exist_ok=True)
                Image.new("RGB", (80, 60), (index % 256, 48, 76)).save(
                    folder / f"image {index % 100}.jpg", comment=f"synthetic {index}".encode())
            check(source, work, args.files)


if __name__ == "__main__":
    main()
