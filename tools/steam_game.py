"""Locate this Steam game using registered libraries and its AppID manifest."""
import os
from pathlib import Path, PureWindowsPath
import re

APP_ID = "1922740"
GAME_FOLDER = "Crisis in the Kremlin Cold War"
EXECUTABLE = "CrisisInTheKremlin2.exe"
ASSET = "CrisisInTheKremlin2_Data/resources.assets"


def steam_roots():
    import winreg
    for hive, name, view in (
        (winreg.HKEY_CURRENT_USER, "SteamPath", 0),
        (winreg.HKEY_LOCAL_MACHINE, "InstallPath", winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_LOCAL_MACHINE, "InstallPath", winreg.KEY_WOW64_64KEY),
    ):
        try:
            with winreg.OpenKey(hive, r"Software\Valve\Steam", 0, winreg.KEY_READ | view) as key:
                yield Path(winreg.QueryValueEx(key, name)[0])
        except OSError:
            continue
    for key in ("ProgramFiles(x86)", "ProgramFiles"):
        if os.environ.get(key):
            yield Path(os.environ[key]) / "Steam"


def read_config(file):
    try:
        return file.read_text("utf-8-sig", errors="replace")
    except OSError:
        return ""


def libraries(roots=None):
    paths = []
    for root in (steam_roots() if roots is None else roots):
        paths.append(root)
        config = read_config(root / "steamapps/libraryfolders.vdf")
        entries = re.findall(r'^\s*"(?:path|\d+)"\s*"([^"\r\n]+)"', config, re.M | re.I)
        for entry in entries:
            folder = Path(entry.replace("\\\\", "\\"))
            if folder.is_absolute():
                paths.append(folder)
    return list(dict.fromkeys(paths))


def validate(game):
    game = Path(game).resolve()
    if not ((game / EXECUTABLE).is_file() and (game / ASSET).is_file()):
        raise ValueError("所选目录中没有找到本游戏。请在 Steam 的「管理 → 浏览本地文件」中查看游戏目录。")
    return game


def manifest_install(apps):
    data = read_config(apps / ("appmanifest_" + APP_ID + ".acf"))
    if not re.search(r'"appid"\s*"' + APP_ID + r'"', data, re.I):
        return None, None
    name = re.search(r'"installdir"\s*"([^"\r\n]+)"', data, re.I)
    if not name or PureWindowsPath(name[1]).name != name[1] or name[1] in (".", ".."):
        return None, None
    build = re.search(r'"buildid"\s*"([1-9][0-9]*)"', data, re.I)
    return (apps / "common" / name[1]), (build[1] if build else None)


def installed_build(game):
    game = Path(game).resolve()
    registered, build = manifest_install(game.parent.parent)
    return build if registered is not None and registered == game else None


def locate(roots=None):
    registered, fallback = [], []
    for library in libraries(roots):
        apps = library / "steamapps"
        game, _ = manifest_install(apps)
        if game is not None:
            registered.append(game)
        fallback.append(apps / "common" / GAME_FOLDER)
    # A Steam move can leave an old copy in the first library. Exhaust valid
    # manifests from every library before considering folders found by name.
    for game in dict.fromkeys(registered + fallback):
        try:
            return validate(game)
        except (ValueError, OSError):
            continue
    raise ValueError("未找到游戏。请先在 Steam 安装，或点击「选择目录」指定游戏文件夹。")
