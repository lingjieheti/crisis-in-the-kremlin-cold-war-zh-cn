"""Build the Windows x64 single-file installer. Run from a 64-bit Python 3.12 on Windows."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EDIT = ROOT / "installer"
GAME = "coldwar"
NAME = "crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe"
EMBED = "python-3.12.10-embed-amd64.zip"
PYTHON_SHA = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def build(dest, cache):
    if os.name != "nt" or sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
        raise SystemExit("构建安装程序需要 Windows x64 和 Python 3.12。")
    cache.mkdir(exist_ok=True, parents=True)
    source = cache / EMBED
    if not source.is_file() or digest(source) != PYTHON_SHA:
        with tempfile.TemporaryDirectory(dir=cache) as pending:
            item = Path(pending) / EMBED
            url = "https://www.python.org/ftp/python/3.12.10/" + EMBED
            with urllib.request.urlopen(url, timeout=120) as response, item.open("wb") as output:
                shutil.copyfileobj(response, output)
            if digest(item) != PYTHON_SHA:
                raise ValueError("CPython 下载校验失败。")
            os.replace(item, source)

    dest.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(prefix="zhcn-build-") as tmp:
        work = Path(tmp)
        payload = work / "payload"
        runtime = payload / "runtime"
        runtime.mkdir(parents=True)
        with zipfile.ZipFile(source) as zf:
            zf.extractall(runtime)
        (runtime / "python312._pth").write_text("python312.zip\n.\nLib/site-packages\n", "ascii")
        lock = EDIT / "requirements.lock"
        if lock.is_file():
            install = [sys.executable, "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
                       "--require-hashes", "--no-deps", "--no-compile", "--target", str(runtime/"Lib/site-packages")]
            if (cache / "wheels").is_dir():
                install += ["--no-index", "--find-links", str(cache / "wheels"), "--no-build-isolation"]
            subprocess.run(install + ["-r", str(lock)], check=True)
            # pip's optional console wrappers point to the builder's Python. The patch
            # imports these libraries directly and the portable runtime has its own exe.
            site = runtime / "Lib/site-packages"
            wrappers = site / "bin"
            if wrappers.is_dir():
                for wrapper in wrappers.iterdir():
                    wrapper.unlink()
                wrappers.rmdir()
                for record in site.glob("*.dist-info/RECORD"):
                    with record.open(encoding="utf-8", newline="") as src:
                        rows = list(csv.reader(src))
                    cleaned = [row for row in rows if not row[0].replace("\\", "/").startswith(("../../Scripts/", "../../bin/"))]
                    if cleaned != rows:
                        with record.open("w", encoding="utf-8", newline="") as out:
                            csv.writer(out).writerows(cleaned)
        shutil.copy2(ROOT / "manage.py", payload)
        (payload / "tools").mkdir()
        shutil.copy2(ROOT / "tools/steam_game.py", payload / "tools")
        if GAME == "coldwar":
            shutil.copy2(ROOT / "tools/workshop.py", payload / "tools")
        if (ROOT / "fonts").is_dir():
            shutil.copytree(ROOT / "fonts", payload / "fonts")
        shutil.copytree(ROOT / "games" / GAME, payload / "games" / GAME,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "AUDIT.md", "audit*.py",
                                                      "rank_text.py", "build_font_delta.py", "test_backend.py"))
        subprocess.run([str(runtime / "python.exe"), "-B", "-X", "utf8", str(payload / "manage.py"), "--help"],
                       cwd=payload, check=True)
        if GAME == "mao":
            subprocess.run([str(runtime / "python.exe"), "-B", "-c", "import UnityPy; import PIL.Image"],
                           cwd=runtime, check=True)
        archive = work / "payload.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for file in sorted(payload.rglob("*")):
                if file.is_file():
                    zf.write(file, file.relative_to(payload))
        compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        if not compiler.is_file():
            raise ValueError("未找到 Windows .NET Framework C# 编译器。")
        binary = work / NAME
        subprocess.run([str(compiler), "/nologo", "/target:winexe", "/platform:x64", "/optimize+",
                        "/utf8output", "/codepage:65001", "/win32manifest:" + str(EDIT / "setup.manifest"),
                        "/resource:" + str(archive) + ",patch.zip", "/out:" + str(binary),
                        "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll", "/r:System.IO.Compression.dll",
                        str(EDIT / "Setup.cs")], check=True)
        final = dest / NAME
        shutil.copy2(binary, final)
        sha = digest(final)
        (dest / "SHA256SUMS.txt").write_text(sha + "  " + NAME + "\n", encoding="ascii", newline="\n")
        print(f"{final.name}  {final.stat().st_size:,} bytes  SHA-256 {sha}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "zhcn-installer-build")
    args = parser.parse_args()
    build(args.output.resolve(), args.cache.resolve())
