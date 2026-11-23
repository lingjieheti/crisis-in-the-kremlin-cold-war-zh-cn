"""Validate the distributable patch files without Steam, network access, or third-party modules."""
import bz2
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import runpy
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "games"
sys.dont_write_bytecode = True


def require(value, message):
    if not value:
        raise ValueError(message)

def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"{path.name}: duplicate key {key}")
            result[key] = value
        return result
    return json.loads(path.read_text("utf-8-sig"), object_pairs_hook=unique)

def text_line(value):
    require(isinstance(value, str) and value.strip(), f"Empty or invalid text: {value!r}")
    require("\ufffd" not in value and "\0" not in value, "Text contains an invalid character")
    return value

def bsd_int(raw):
    number = int.from_bytes(raw, "little")
    return -(number & ((1 << 63) - 1)) if number >> 63 else number

def check_coldwar(chars):
    folder = GAMES / "coldwar"
    patch = read_json(folder / "patch.json")
    require(len(patch) >= 598, "Cold War patch has lost translation entries")
    for key, value in patch.items():
        require(re.fullmatch(r"/\w+/\w+", key), f"Invalid XML key: {key}")
        chars.update(text_line(value))
    require(sum(k.startswith("/player_country_desc/") for k in patch) >= 397, "Country-name set incomplete")
    for key, counts in (("text", [24, 26, 34, 4]), ("patch_1_2_5_6_text", [3, 8, 2])):
        items = []
        for line in patch["/patchnotes/" + key].split("|"):
            if not line:
                continue
            if any(c.isalpha() for c in line) and not any(c.islower() for c in line):
                items.append(0)
            else:
                require(items, "Patch notes start with an item outside a section")
                items[-1] += 1
        require(items == counts, f"Invalid in-game patch-note grouping in {key}: {items}")
    font = runpy.run_path(str(folder / "font_patch.py"))
    delta = (folder / "font.bsdiff").read_bytes()
    require(hashlib.sha256(delta).hexdigest() == font["DELTA_SHA"], "Cold War font delta hash mismatch")
    require(delta[:8] == b"BSDIFF40", "Unexpected font patch format")
    ctl_size, diff_size, total = [bsd_int(delta[i:i+8]) for i in (8, 16, 24)]
    require(0 < ctl_size < len(delta) and 0 < diff_size < len(delta) - 32 - ctl_size, "Invalid delta header")
    end = 32 + ctl_size + diff_size
    control = bz2.decompress(delta[32:32+ctl_size])
    diff = bz2.decompress(delta[32+ctl_size:end])
    extra = bz2.decompress(delta[end:])
    additions = insertions = 0
    for add_raw, insert_raw, _ in struct.iter_unpack("8s8s8s", control):
        add, insert = bsd_int(add_raw), bsd_int(insert_raw)
        require(add >= 0 and insert >= 0, "Invalid font-delta control block")
        additions += add
        insertions += insert
    require((additions, insertions) == (len(diff), len(extra)) and additions + insertions == total,
            "Cold War font-delta streams do not reconstruct the declared byte count")
    print(f"Cold War: {len(patch)} entries, country names, patch-note groups and font delta verified")

def check_revised_text():
    links = read_json(GAMES / "coldwar/wiki_zh.json")
    for key, value in links.items():
        require(re.fullmatch(r"/(?:char_wiki_links|decision_wiki_links|doctrine_wiki_links|positions_wiki)/\w+", key),
                f"Invalid encyclopedia field: {key}")
        require(re.fullmatch(r"https://zh\.wikipedia\.org/wiki/[A-Za-z0-9%._~()-]+",value)
                and not re.search(r"%(?![0-9a-fA-F]{2})", value), f"Malformed Chinese encyclopedia URL: {key}")
    revised = read_json(GAMES / "coldwar/patch.json")
    require("单方" in revised["/pseudoModificator/modif184var2"], "Unilateral détente has the wrong direction")
    seats = revised["/high_council_window/party_seats"]
    require("{1}%" in seats and "{2}%" in seats, "Faction and parliamentary seat shares must both be percentages")
    require(all(f"/decision_desc/decision12var{i}" in revised for i in range(12)),
            "Economic union decision rows missing")


def main():
    check_revised_text()
    for path in ROOT.rglob("*.py"):
        if ".git" not in path.parts:
            compile(path.read_bytes(), str(path.relative_to(ROOT)), "exec")
    chars = set()
    check_coldwar(chars)

    for path in ("manage.py", "games/coldwar/patch.py"):
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / path), "--help"],
                              capture_output=True, encoding="utf-8", timeout=30)
        require(proc.returncode == 0 and "install" in proc.stdout and "restore" in proc.stdout,
                f"Player entry point failed: {path}")
    print("Release files and both player entry points passed.")

if __name__ == "__main__":
    main()
