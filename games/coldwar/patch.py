"""Build a local-only Chinese translation from the player's Workshop copy."""
import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re

import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
# Windows' embedded runtime can omit the executed script's folder from sys.path.
sys.path.insert(0, str(HERE))
import font_patch
import game_paths

MOD = "zhcn-coldwar-local"
ORIGINAL_ID = "114514"
ITEM = "3523398274"
GAME = "1922740"
BUILD = "26243566"
XML_HASH = "d4aa3fa9c02d761a11e70dabb7dcd5dd643af5d772ea1b4307403935cce17061"
V1_XML = "ea80a26f85d54e6f1c7ca3e83ba607a41502d7f903e5cb7047e22048e5aa8314"
V1_2_XML = "1936bf8b50353cbf81bd7b64616bc372e259465bbbc9fcc73e02d2719ede31aa"
RELEASE_XML = "9b52edb3378c45b98beab0cfdc2ec45cc43d59bf332bd3cceb10d30fcc4bf2a1"
GENERATIONS = (V1_XML, V1_2_XML, RELEASE_XML)
REGKEY = r"Software\Nostalgames\CrisisInTheKremlin2"
PREF = "modsPrefsList_h752420768"
OWN_FILES = {"text.xml", "info.json", "icon.png"}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def read_json(path):
    return json.loads(path.read_text("utf-8-sig"))

def ensure(ok, message):
    if not ok:
        raise ValueError(message)

def game_running():
    executable = Path(os.environ["SystemRoot"]) / "System32/tasklist.exe"
    listing = subprocess.check_output([str(executable), "/fi", "imagename eq CrisisInTheKremlin2.exe", "/fo", "csv", "/nh"], creationflags=subprocess.CREATE_NO_WINDOW)
    return b"crisisinthekremlin2.exe" in listing.lower()

def discover(game=None):
    return game_paths.workshop(game, XML_HASH)

def render_text(xml):
    root = ET.fromstring(xml)
    patch = read_json(HERE / "patch.json")
    links = read_json(HERE / "wiki_zh.json")
    for path, url in links.items():
        ensure(re.fullmatch(r"/(char_wiki_links|decision_wiki_links|doctrine_wiki_links|positions_wiki)/\w+", path)
               and re.fullmatch(r"https://zh\.wikipedia\.org/wiki/[A-Za-z0-9%._~()-]+", url)
               and path not in patch, "百科链接差分无效。")
    patch.update(links)
    # All paths in this patch have exactly one section and one unique leaf.
    for path, translation in patch.items():
        ensure(re.fullmatch(r"/[\w]+/[\w]+", path), f"无效键名 {path}")
        nodes = root.findall("." + path)
        ensure(len(nodes) == 1 and len(nodes[0]) == 0 and isinstance(translation, str), f"键无法唯一匹配 {path}")
        nodes[0].text = translation
    result = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    checked = ET.fromstring(result)
    ensure(sum(1 for node in checked.iter() if not len(node)) == 18133, "文本项数校验失败。")
    ensure(all(checked.findtext("." + k) == v for k, v in patch.items()), "中文回读校验失败。")
    ensure(sha(result) == RELEASE_XML, "生成的中文指纹与本版本不符。")
    return result

def render(base):
    info = read_json(base / "info.json")
    ensure(info.get("id") == ORIGINAL_ID and info.get("modType") == "Translation", "所选目录不是支持的社区中文翻译。")
    xml = (base / "text.xml").read_bytes()
    ensure(sha(xml) == XML_HASH, "社区中文基包版本不同，已停止，以免覆盖新译文。")
    info["id"] = MOD
    info.pop("steamPublishedFileId", None)
    info["displayedName"] = "社区中文翻译 · 本地校订"
    info["description"] = "使用本机 Steam 社区中文翻译生成。" + info["description"]
    return {"text.xml": render_text(xml), "info.json": json_bytes(info), "icon.png": (base / "icon.png").read_bytes()}

def read_pref():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGKEY) as key:
            data, kind = winreg.QueryValueEx(key, PREF)
    except FileNotFoundError:
        return None, []
    ensure(kind == winreg.REG_BINARY, "游戏模组配置的注册表类型与预期不同。")
    values = json.loads(data.rstrip(b"\0").decode("utf-8-sig") or "[]")
    ensure(isinstance(values, list) and all(isinstance(x, dict) and isinstance(x.get("id"), str) and isinstance(x.get("isLoaded"), bool) for x in values), "无法识别现有模组配置。")
    return data, values

def write_pref(data):
    import winreg
    if data is None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGKEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, PREF)
        except FileNotFoundError:
            pass
    else:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REGKEY, access=winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, PREF, 0, winreg.REG_BINARY, data)

def encoded(rows):
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\0"

def activate(rows):
    result = [dict(row) for row in rows if row["id"] != MOD]
    for row in result:
        if row["id"] == ORIGINAL_ID:
            row["isLoaded"] = False
    result.append({"id": MOD, "isLoaded": True})
    return result

def b64(data):
    return base64.b64encode(data).decode("ascii") if data is not None else None

def source_bytes(value):
    return base64.b64decode(value) if value is not None else None

def reparse(path):
    return bool(getattr(os.lstat(path), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)

def verify_files(folder, hashes):
    ensure(folder.is_dir() and not reparse(folder), "找不到本补丁目录或路径已重定向。")
    entries = list(folder.iterdir())
    ensure({x.name for x in entries} == OWN_FILES and set(hashes) == OWN_FILES, "补丁目录有其他文件，请先将其移出后再操作。")
    for file in entries:
        ensure(file.is_file() and not reparse(file) and sha(file.read_bytes()) == hashes[file.name], f"{file.name} 已被修改，请先保存个人改动。")

def verify_generation(folder, hashes):
    # Only the generated XML changed since v1. An interrupted atomic replacement can
    # leave the fully written new XML next to the old installation record.
    expected = hashes.copy()
    text = folder / "text.xml"
    recorded = hashes.get("text.xml")
    if recorded in GENERATIONS and text.is_file() and not reparse(text):
        actual = sha(text.read_bytes())
        if actual in GENERATIONS[GENERATIONS.index(recorded):]:
            expected["text.xml"] = actual
    verify_files(folder, expected)

def has_local_base(data_dir=None):
    """A settled installation can supply the base. The backend verifies it under its lock."""
    root = game_paths.user_data(data_dir)
    manifest = root / ".zhcn-coldwar-install.json"
    if not manifest.exists():
        return False
    ensure(manifest.is_file() and not reparse(manifest), "安装记录已被重定向。")
    state = read_json(manifest)
    return (state.get("format") == 1 and not state.get("pending_activation")
            and state.get("files", {}).get("text.xml") in GENERATIONS
            and (root / "mods" / MOD).is_dir())

def upgrade(folder, state_file, state, payload, hashes):
    old = state["files"]
    ensure(old.get("text.xml") in GENERATIONS[:-1] and old == {**hashes, "text.xml": old["text.xml"]}
           and hashes["text.xml"] == RELEASE_XML,
           "当前安装记录与支持的旧版不符，请先核对原先的基包和个人改动。")
    verify_generation(folder, old)
    target = folder / "text.xml"
    if sha(target.read_bytes()) != RELEASE_XML:
        font_patch.replace_atomic(target, payload["text.xml"], staging_dir=state_file.parent)
    verify_files(folder, hashes)
    # Keep the v1 preference snapshot for eventual restoration. Later mod toggles
    # belong to the player, including temporarily disabling this translation.
    state["files"] = hashes
    font_patch.replace_atomic(state_file, json_bytes(state))

def restore_pref(state):
    old = source_bytes(state["previous"])
    current, rows = read_pref()
    if b64(current) == state["applied"] or current == old:
        return old
    original = json.loads(old.rstrip(b"\0").decode("utf-8-sig") or "[]") if old else []
    source = {x["id"]: x for x in original}
    merged = [dict(x) for x in rows if x["id"] != MOD]
    for row in merged:
        if row["id"] == ORIGINAL_ID and ORIGINAL_ID in source:
            row["isLoaded"] = source[ORIGINAL_ID]["isLoaded"]
    return encoded(merged) if merged else (None if old is None else encoded([]))

def find_conflicting(base, mods, rows):
    active = {r["id"] for r in rows if r["isLoaded"]} - {ORIGINAL_ID, MOD}
    if not active:
        return
    for parent in {mods, base.parent}:
        for filename in parent.glob("*/info.json"):
            try:
                info = read_json(filename)
            except (OSError, ValueError):
                continue
            ensure(info.get("id") not in active or info.get("modType") != "Translation", "请先在游戏中关闭另一份已启用的翻译模组。")

@contextmanager
def locked(root):
    # Windows releases a byte-range lock even when the process is interrupted.
    import msvcrt
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".zhcn-coldwar.lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)

def run(args):
    if args.action == "build":
        ensure(args.output is not None and not args.output.exists(), "请用 --output 指定一个尚不存在的输出目录。")
        payload = render(args.base or discover(args.game_dir))
        args.output.mkdir(parents=True)
        for name, data in payload.items():
            write_new(args.output / name, data)
        return
    ensure(os.name == "nt", "安装和回退仅支持 Windows。")
    root = game_paths.user_data(getattr(args, "data_dir", None))
    folder = root / "mods" / MOD
    state_file = root / ".zhcn-coldwar-install.json"
    if args.action in ("verify", "restore"):
        ensure(state_file.is_file(), "本补丁尚未安装。")
    with locked(root):
        if args.action != "verify":
            ensure(not game_running(), "请先退出游戏。")
        if state_file.exists():
            ensure(state_file.is_file() and not reparse(state_file), "安装记录已被重定向。")
        asset = font_patch.asset_location(args.game_dir)
        if args.action == "install":
            font_patch.manage(asset, root, "preflight")
        if args.action == "restore":
            ensure(state_file.exists(), "找不到本补丁的安装记录。")
            state = read_json(state_file)
            ensure(state.get("format") == 1, "不能识别安装记录。")
            if folder.exists():
                verify_generation(folder, state["files"])
            font_patch.manage(asset, root, "restore")
            write_pref(restore_pref(state))
            if folder.exists():
                for name in OWN_FILES:
                    (folder / name).unlink()
                folder.rmdir()
            state_file.unlink()
            return
        if args.action == "verify":
            ensure(state_file.is_file(), "本补丁尚未安装。")
            state = read_json(state_file)
            ensure(state.get("format") == 1 and state["files"].get("text.xml") == RELEASE_XML,
                   "请先运行本版本的 install 完成更新。")
            verify_files(folder, state["files"])
            font_patch.manage(asset, root, "verify")
            _, active = read_pref()
            ensure(any(x["id"] == MOD and x["isLoaded"] for x in active), "本地校订模组未启用。")
            return
        mods = folder.parent
        mods.mkdir(exist_ok=True)
        ensure(not reparse(mods), "模组目录是重定向路径，请手动安装。")
        state = read_json(state_file) if state_file.exists() else None
        if state is not None:
            ensure(state.get("format") == 1, "不能识别安装记录。")
        base = args.base
        if base is None and has_local_base(root):
            verify_generation(folder, state["files"])
            payload = {name: (folder / name).read_bytes() for name in OWN_FILES}
            payload["text.xml"] = render_text(payload["text.xml"])
        else:
            base = base or discover(args.game_dir)
            payload = render(base)
        hashes = {name: sha(data) for name, data in payload.items()}
        current, rows = read_pref()
        if state is not None:
            if state["files"] != hashes:
                if state.get("pending_activation") and not folder.exists():
                    old = state["files"]
                    ensure(old.get("text.xml") in GENERATIONS[:-1]
                           and old == {**hashes, "text.xml": old["text.xml"]}, "首次安装记录与基包不符。")
                    state["files"] = hashes
                    font_patch.replace_atomic(state_file, json_bytes(state))
                else:
                    upgrade(folder, state_file, state, payload, hashes)
            if folder.exists():
                verify_files(folder, hashes)

        else:
            ensure(args.action == "install", "本补丁尚未安装。")
            ensure(not folder.exists() and not any(r["id"] == MOD for r in rows), "相同名称的模组已经存在。")
            find_conflicting(base, mods, rows)
            changed = encoded(activate(rows))
            state = {"format": 1, "files": hashes, "previous": b64(current), "applied": b64(changed), "pending_activation": True}
            font_patch.replace_atomic(state_file, json_bytes(state))
        if not folder.exists():
            with tempfile.TemporaryDirectory(dir=mods) as staging:
                staged = Path(staging) / MOD
                staged.mkdir()
                for name, data in payload.items():
                    write_new(staged / name, data)
                verify_files(staged, hashes)
                os.rename(staged, folder)
        verify_files(folder, hashes)
        font_patch.manage(asset, root, "install")
        if state.get("pending_activation"):
            find_conflicting(base, mods, rows)
            desired = activate(rows)
            if rows != desired:
                write_pref(encoded(desired))
            del state["pending_activation"]
            font_patch.replace_atomic(state_file, json_bytes(state))

if __name__ == "__main__":
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument("action", choices=["build", "install", "restore", "verify"])
    argp.add_argument("--game-dir", type=Path, help="Steam game directory (auto-detected by default)")
    argp.add_argument("--data-dir", type=Path, help="Unity player data folder (defaults to current user LocalLow)")
    argp.add_argument("--base", type=Path, help="Steam Workshop item 3523398274 folder")
    argp.add_argument("--output", type=Path, help="new output directory for build")
    try:
        run(argp.parse_args())
        print("完成。")
    except (OSError, ValueError, KeyError) as error:
        argp.exit(1, f"{error}\n")
