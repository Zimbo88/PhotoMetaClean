"""Build native artifacts using only the installed application and explicit launchers."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
from zipfile import ZipFile, ZIP_DEFLATED

from vendors import exiftool, license_files

HERE = Path(__file__).resolve().parent
DIST = HERE.parent / "dist"
RUNTIME_URL = "https://api.github.com/repos/AppImage/type2-runtime/releases/assets/657374641"
RUNTIME_SHA256 = "617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46"


ICON = HERE.parent / "src/photometaclean/gui/photometaclean.svg"


def native_icon(work, system):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PIL import Image

    renderer = QSvgRenderer(str(ICON))
    if not renderer.isValid():
        raise ValueError("Invalid application icon")
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    png = work / "PhotoMetaClean.png"
    if not image.save(str(png)):
        raise ValueError("Could not render the application icon")
    target = work / ("PhotoMetaClean.ico" if system == "Windows" else "PhotoMetaClean.icns")
    with Image.open(png) as bitmap:
        bitmap.save(target)
    return target


def sign_windows(launcher):
    thumbprint = os.environ.get("PHOTOMETACLEAN_SIGNING_THUMBPRINT")
    if not thumbprint:
        return
    tool = os.environ.get("PHOTOMETACLEAN_SIGNTOOL", "signtool.exe")
    subprocess.run([tool, "sign", "/sha1", thumbprint, "/fd", "SHA256", "/tr",
                    "http://timestamp.digicert.com", "/td", "SHA256", launcher], check=True)
    subprocess.run([tool, "verify", "/pa", "/all", launcher], check=True)


def appimage(stage, target, work):
    appdir = work / "AppDir"
    shutil.copytree(HERE / "linux", appdir)
    shutil.copy2(ICON, appdir)
    shutil.copytree(stage, appdir / "usr/bin", symlinks=True)
    (appdir / ".DirIcon").symlink_to("photometaclean.svg")
    cache = DIST / ".cache" / RUNTIME_SHA256
    if cache.is_file():
        runtime = cache.read_bytes()
    else:
        request = Request(RUNTIME_URL, headers={"Accept": "application/octet-stream"})
        with urlopen(request, timeout=60) as response:
            runtime = response.read()
    if hashlib.sha256(runtime).hexdigest() != RUNTIME_SHA256:
        raise ValueError("AppImage runtime checksum mismatch")
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        verified = work / "verified-runtime"
        verified.write_bytes(runtime)
        os.replace(verified, cache)
    filesystem = work / "filesystem.squashfs"
    subprocess.run(["mksquashfs", appdir, filesystem, "-noappend", "-all-root",
                    "-comp", "gzip", "-no-progress"], check=True)
    image = work / target.name
    with image.open("wb") as dest, filesystem.open("rb") as source:
        dest.write(runtime)
        shutil.copyfileobj(source, dest)
    image.chmod(0o755)
    subprocess.run([image, "--appimage-extract-and-run", "--cli", "--help"], check=True)
    os.replace(image, target)


def check_cli(binary, work):
    from PIL import Image

    sample = work / "synthetic test.jpg"
    Image.new("RGB", (13, 7), "orange").save(sample, comment=b"synthetic")
    result = subprocess.run([binary, "analyze", sample, "--workers", "2"],
                            check=True, capture_output=True, timeout=120)
    analysis = json.loads(result.stdout)["analysis"]
    if analysis["resolution"] != [13, 7] or not analysis["frames"][0]["pixels"]:
        raise ValueError("Frozen CLI failed the synthetic JPEG analysis")

    out = work / "verified copies"
    result = subprocess.run([binary, "edit", sample, "--changes", '{"JPEG:Comment":null}',
                             "--apply", "--output", out], check=True, capture_output=True, timeout=120)
    audit = json.loads(result.stdout.splitlines()[-1])["result"]["audit"]
    copy = out / sample.name
    if (audit["integrity_before"] != audit["integrity_after"]
            or hashlib.sha256(copy.read_bytes()).hexdigest() != audit["output_sha256"]
            or hashlib.sha256(sample.read_bytes()).hexdigest() != audit["source_sha256"]):
        raise ValueError("Frozen CLI failed the verified copy test")


def main():
    for mode in ("gui", "cli"):
        module = f"photometaclean.{mode}.app"
        if importlib.util.find_spec(module) is None:
            raise SystemExit(f"Missing build input: {module}. Install the complete project first.")
    system = platform.system()
    arch = platform.machine().lower().replace("amd64", "x86_64")
    if (system, arch) not in {("Linux", "x86_64"), ("Windows", "x86_64"),
                              ("Darwin", "x86_64"), ("Darwin", "arm64")}:
        raise SystemExit(f"Unsupported build host: {system} {arch}")
    DIST.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=DIST) as temp:
        work = Path(temp)
        stage = work / "stage"
        stage.mkdir()
        for notice in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(HERE.parent / notice, stage)
        for guide in ("START.md", "marker.md", "jpeg-export.md", "editing-history.md"):
            shutil.copy2(HERE.parent / "docs" / guide, stage)
        vendor = exiftool(system, DIST / ".cache", work)
        license_files(stage)
        icon_args = ["--icon", native_icon(work, system)] if system in ("Windows", "Darwin") else []
        for mode, name in (("gui", "PhotoMetaClean"), ("cli", "photometaclean-cli")):
            subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                            "--distpath", work / "frozen", "--workpath", work / "cache",
                            "--collect-all", "c2pa", "--specpath", work, "--name", name,
                            "--add-data", f"{vendor}:tools", "--onedir",
                            *(["--collect-data", "photometaclean.gui", *icon_args] if mode == "gui" else []),
                            "--contents-directory", f"_{mode}",
                            "--windowed" if mode == "gui" else "--console",
                            HERE / f"{mode}_entry.py"], check=True)
            directory = work / "frozen" / name
            if system == "Darwin" and mode == "gui":
                app = directory.with_suffix(".app")
                shutil.move(app, stage / app.name)
                launcher = stage / app.name / "Contents/MacOS" / name
            else:
                for path in directory.iterdir():
                    dest = stage / path.name
                    if system == "Linux" and mode == "cli" and path.name == name:
                        dest = stage / "photometaclean"
                    shutil.move(path, dest)
                launcher = stage / ("photometaclean" if mode == "cli" and system == "Linux" else name)
                if system == "Windows":
                    launcher = launcher.with_suffix(".exe")
                    sign_windows(launcher)
            if mode == "cli":
                check_cli(launcher, work)
            else:
                subprocess.run([launcher, "--smoke-test"], check=True, timeout=120,
                               env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
        if system == "Linux":
            appimage(stage, DIST / "PhotoMetaClean-linux-x86_64.AppImage", work)
            portable = work / "PhotoMetaClean"
            stage.rename(portable)
            archive = shutil.make_archive(str(work / "PhotoMetaClean-linux-x86_64"), "gztar",
                                          root_dir=work, base_dir=portable.name)
            os.replace(archive, DIST / Path(archive).name)
        else:
            if system == "Darwin":
                chip = {"x86_64": "Intel", "arm64": "Apple-Silicon"}[arch]
                archive = work / f"PhotoMetaClean-Mac-{chip}.zip"
                subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", stage, archive], check=True)
            else:
                archive = work / f"PhotoMetaClean-{system}-{arch}.zip"
                with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
                    for path in stage.rglob("*"):
                        if path.is_file():
                            bundle.write(path, path.relative_to(stage))
            os.replace(archive, DIST / archive.name)


if __name__ == "__main__":
    main()
