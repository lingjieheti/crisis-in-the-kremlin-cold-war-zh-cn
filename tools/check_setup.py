"""Exercise the distributed Windows installer against a temporary Steam manifest."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from steam_game import APP_ID, ASSET, EXECUTABLE


def run(exe, args, cwd, expected, message):
    # Only the bundled interpreter is available to the installer.
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV")}
    env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    result = subprocess.run([str(exe), *map(str, args)], cwd=cwd, env=env, capture_output=True,
                            encoding="utf-8", errors="replace", timeout=120)
    output = result.stdout if expected == 0 else result.stderr
    if result.returncode != expected or message not in output or "Traceback" in result.stderr:
        raise AssertionError((args[0], result.returncode, output))


def check(exe):
    with tempfile.TemporaryDirectory(prefix="汉化 检查 ") as tmp:
        root = Path(tmp)
        run(exe, ["--locate", root], root, 1, "Steam")
        apps = root / "steamapps"
        game = apps / "common/测试版本"
        for name in (EXECUTABLE, ASSET):
            file = game / name
            file.parent.mkdir(exist_ok=True, parents=True)
            file.touch()
        run(exe, ["--build", game], root, 0, "unknown")
        acf = apps / ("appmanifest_" + APP_ID + ".acf")
        acf.write_text(f'"appid" "{APP_ID}"\n"installdir" "{game.name}"\n"buildid" "246810"\n', encoding="utf-8")
        run(exe, ["--build", game], root, 0, "246810")
        run(exe, ["--locate", game], root, 0, str(game.resolve()))
    print("Packaged EXE passed directory validation and Steam build checks.")


if __name__ == "__main__":
    check(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else next((HERE.parent / "dist").glob("*-Setup.exe")))
