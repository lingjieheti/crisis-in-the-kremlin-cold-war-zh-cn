"""Install, verify, or restore the Simplified Chinese patch for 克里姆林宫危机：冷战."""
import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ACTIONS = {"install": "安装或更新", "verify": "核验安装", "restore": "还原"}

def choose(prompt, choices):
    print(prompt)
    for index, (_, label) in enumerate(choices, 1):
        print(f"  {index}. {label}")
    print("  0. 退出")
    while True:
        answer = input("请选择编号：").strip()
        if answer == "0":
            raise SystemExit(0)
        if answer.isascii() and answer.isdecimal() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1][0]
        print("请输入上面列出的编号。")

def game_running(exe):
    tasklist = Path(os.environ["SystemRoot"]) / "System32/tasklist.exe"
    output = subprocess.check_output([str(tasklist), "/FO", "CSV", "/NH", "/FI",
                                      f"IMAGENAME eq {exe}"], encoding="mbcs", errors="replace")
    return any(row and row[0].casefold() == exe.casefold() for row in csv.reader(output.splitlines()))

def main():
    parser = argparse.ArgumentParser(description="《克里姆林宫危机：冷战》简体中文补丁")
    parser.add_argument("action", choices=ACTIONS, nargs="?")
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info < (3, 11) or sys.maxsize <= 2**32:
        parser.exit(1, "请使用 Windows 和 64 位 Python 3.11 或更高版本。\n")
    action = args.action or choose("《克里姆林宫危机：冷战》简体中文补丁", list(ACTIONS.items()))
    if action != "verify" and game_running("CrisisInTheKremlin2.exe"):
        parser.exit(1, "请先退出游戏，再执行此操作。\n")
    if action == "install":
        fetched = subprocess.run([sys.executable, "-B", str(ROOT / "tools/workshop.py"), "coldwar"])
        if fetched.returncode:
            return fetched.returncode
    return subprocess.run([sys.executable, "-B", str(ROOT / "games/coldwar/patch.py"), action]).returncode

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
