"""Localize only the game's bundled Steam Input profiles, preserving every binding."""
import hashlib
import json
from pathlib import Path
import re
import stat

import font_patch
import game_paths


HERE = Path(__file__).resolve().parent
ANCHOR = b'\t\t"russian"\r\n'
FIELDS = {
    "title": "克里姆林宫危机：冷战", "click": "点击", "rclick": "右键点击",
    "event": "打开事件", "pause": "暂停", "quicksave": "快速存档",
    "slower": "减慢游戏速度", "faster": "加快游戏速度", "modeprev": "上一个地图模式",
    "modenext": "下一个地图模式", "nav": "移动焦点", "back": "返回", "winprev": "上一个窗口",
    "winnext": "下一个窗口", "winmap": "返回地图", "scrollup": "向上滚动",
    "scrolldown": "向下滚动", "winopen": "从地图打开窗口", "zoomout": "缩小地图／上一个窗口",
    "zoomin": "放大地图／下一个窗口",
}
DECK = ("右触控板移动光标，按下为左键点击。左触控板滚动，按下为右键点击。方向键或左摇杆移动焦点，"
        "背键 L4、R4 切换窗口，L5 返回地图。右摇杆移动视野，扳机键缩放，肩键调整游戏速度，菜单键暂停。")
GAMEPAD = ("方向键或左摇杆移动焦点。A 点击，B 返回，Y 打开事件，X 从地图打开窗口。右摇杆移动视野，"
           "扳机键缩放地图或切换窗口，肩键调整游戏速度，菜单键暂停，视图键快速存档。")


def block(name, original):
    english = re.search(rb'"english"\s*\{([^{}]+)\}', original)
    if not english or original.count(ANCHOR) != 1:
        raise ValueError("手柄布局的语言段与已验证结构不符。")
    fields = FIELDS.copy()
    if name in ("steam_input_manifest.vdf", "controller_neptune.vdf"):
        fields.update(description=DECK, quicksave="光标（按住快速存档）")
    else:
        fields["description"] = GAMEPAD
        if name in ("controller_ps4.vdf", "controller_ps5.vdf"):
            fields["description"] += "触控板移动光标，按下为左键点击。"
    keys = re.findall(rb'^\s*"([a-z]+)"\s+"[^"\r\n]*"\s*$', english[1], re.M)
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("手柄布局文字标签无法唯一识别。")
    lines = ['\t\t"schinese"', '\t\t{']
    for name_bytes in keys:
        key = name_bytes.decode("ascii")
        lines.append(f'\t\t\t"{key}"\t\t"{fields[key]}"')
    return ("\r\n".join([*lines, '\t\t}', ''])).encode("utf8")


def manage(game_dir, build, action):
    if str(build) != "26977018" and action != "restore":
        return
    if action not in {"preflight", "verify", "install", "restore"}:
        raise ValueError("无法识别手柄布局操作。")
    folder = Path(game_dir or game_paths.game_dir("steam_input/steam_input_manifest.vdf")) / "steam_input"
    if not folder.exists() and str(build) != "26977018":
        return
    records = json.loads((HERE / "controller-profiles.json").read_text("utf8"))
    pending = []
    skipped = []
    for name, (original_sha, localized_sha) in records.items():
        path = folder / name
        if (not path.is_file() or folder.is_symlink() or path.is_symlink()
                or getattr(folder.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                or getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            skipped.append(name)
            continue
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest not in (original_sha, localized_sha):
            skipped.append(name)
            continue
        if action == "verify" and digest != localized_sha:
            raise ValueError(f"请重新安装手柄说明汉化：{name}")
        if action in ("preflight", "verify"):
            continue
        if action == "install" and digest == original_sha:
            updated = content.replace(ANCHOR, block(name, content) + ANCHOR, 1)
            target = localized_sha
        elif action == "restore" and digest == localized_sha:
            updated = content.replace(block(name, content) + ANCHOR, ANCHOR, 1)
            target = original_sha
        else:
            continue
        if hashlib.sha256(updated).hexdigest() != target:
            raise ValueError(f"手柄布局生成后的校验失败：{name}")
        pending.append((path, digest, updated))
    for path, expected, content in pending:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"手柄布局在安装过程中发生变化，请重试：{path.name}")
        font_patch.replace_atomic(path, content)
    if skipped and action != "preflight":
        print("以下手柄默认布局缺失或已有其他版本，已保留现状：" + "、".join(skipped))
