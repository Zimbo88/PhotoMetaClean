"""Assemble offline ExifTool files from upstream checksum-pinned distributions."""
from hashlib import sha256
from importlib import metadata
from pathlib import Path
import shutil
import tarfile
import urllib.request
import zipfile

ARCHIVES = {
    "Windows": ("exiftool-13.64_64.zip", "72c29c44d1e860eebcaefa71692d979af9858fe9a6d7d791a5e7f1dac77804af"),
    "Perl": ("Image-ExifTool-13.64.tar.gz", "dcb9f6be1f6705ee826a92d1522e3fec1d0b3749cdc061b03c46873d5fe204fc"),
}


def exiftool(system, cache, work):
    name, expected = ARCHIVES["Windows" if system == "Windows" else "Perl"]
    cache.mkdir(exist_ok=True, parents=True)
    archive = cache / name
    if not archive.exists():
        temp = work / name
        sources = [f"https://downloads.sourceforge.net/project/exiftool/{name}",
                   f"https://sourceforge.net/projects/exiftool/files/{name}/download"]
        for url in sources:
            try:
                with urllib.request.urlopen(url, timeout=60) as response, temp.open("wb") as output:
                    shutil.copyfileobj(response, output)
                if sha256(temp.read_bytes()).hexdigest() == expected:
                    temp.replace(archive)
                    break
            except OSError:
                continue
    if not archive.exists() or sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Missing verified ExifTool archive: {name}")
    out = work / "tools"
    if system == "Windows":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(work / "vendor")
        shutil.move(work / "vendor/exiftool-13.64_64", out)
        (out / "exiftool(-k).exe").rename(out / "exiftool.exe")
    else:
        with tarfile.open(archive) as bundle:
            bundle.extractall(work / "vendor", filter="data")
        source = work / "vendor/Image-ExifTool-13.64"
        out.mkdir()
        for filename in ("exiftool", "README"):
            shutil.copy2(source / filename, out)
        shutil.copytree(source / "lib", out / "lib")
    return out


def license_files(stage):
    out = stage / "licenses"
    shutil.copytree(Path(__file__).with_name("licenses"), out)
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        inventory.append(f"{name} {dist.version}")
        for item in dist.files or ():
            if ".dist-info/licenses/" in str(item) or (
                ".dist-info/" in str(item) and item.name.lower().startswith(("license", "copying", "notice"))
            ):
                target = out / name / str(item).split(".dist-info/", 1)[1]
                target.parent.mkdir(parents=True, exist_ok=True)
                source = dist.locate_file(item)
                if source.is_file():
                    shutil.copyfile(source, target)
    (out / "build-environment.txt").write_text("\n".join(sorted(set(inventory))) + "\n", encoding="utf8")
