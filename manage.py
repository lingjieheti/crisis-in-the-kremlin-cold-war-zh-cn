"""Player entry point for the standalone Simplified Chinese patch."""
import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from steam_game import EXECUTABLE, locate, validate


def game_running():
    tasklist = Path(os.environ["SystemRoot"]) / "System32/tasklist.exe"
    output = subprocess.check_output([str(tasklist), "/FO", "CSV", "/NH", "/FI",
                                      "IMAGENAME eq " + EXECUTABLE], encoding="mbcs", errors="replace")
    return any(row and row[0].casefold() == EXECUTABLE.casefold()
               for row in csv.reader(output.splitlines()))


def main():
    parser = argparse.ArgumentParser(description="《克里姆林宫危机：冷战》简体中文汉化补丁")
    parser.add_argument("action", nargs="?", default="install", choices=["locate", "install", "verify", "restore"])
    parser.add_argument("--game-dir", type=Path, help="手动指定游戏主目录；默认自动识别 Steam 库")
    args = parser.parse_args()
    if os.name != "nt" or sys.maxsize <= 2**32:
        parser.exit(1, "请使用 64 位 Windows。\n")
    game = validate(args.game_dir) if args.game_dir is not None else locate()
    if args.action == "locate":
        print(game, flush=True)
        return 0
    if args.action != "verify" and game_running():
        parser.exit(1, "请先保存进度并退出游戏，再重试。\n")
    backend = ROOT / "games/coldwar/patch.py"
    action = "check" if args.action == "verify" and "coldwar" == "collapse" else args.action
    command = [sys.executable, "-B", "-u", "-X", "utf8"]
    if action == "install":
        result = subprocess.run([*command, str(ROOT / "tools/workshop.py"), "coldwar", "--game-dir", str(game)])
        if result.returncode:
            return result.returncode
    return subprocess.run([*command, str(backend), action, "--game-dir", str(game)]).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
