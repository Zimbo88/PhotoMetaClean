"""Measure sustained CLI analysis throughput using generated, unrelated files."""
import argparse
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from PIL import Image
from photometaclean.core.batch import analyses, discover


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    with TemporaryDirectory() as folder:
        root = Path(folder)
        for index in range(args.files):
            path = root / str(index // 100) / f"{index}.jpg"
            path.parent.mkdir(exist_ok=True)
            Image.new("RGB", (320, 240), (index % 255, 35, 71)).save(path)
        started = perf_counter()
        count = 0
        for _, result in analyses(discover(root), args.workers):
            if result.get("error"):
                raise RuntimeError(result["error"])
            count += 1
        elapsed = perf_counter() - started
        print(f"{count} files, {args.workers} workers, {elapsed:.2f} s, {count / elapsed:.2f} files/s")


if __name__ == "__main__":
    main()
