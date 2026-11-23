"""Locate this Steam app, its Workshop item, and the current Windows player's Unity data."""
from pathlib import Path
import os
import re

APP_ID = '1922740'
ITEM_ID = '3523398274'
INSTALL_NAME = 'Crisis in the Kremlin Cold War'
DATA_FOLDER = Path('Nostalgames/CrisisInTheKremlin2')


def steam_root():
    import winreg
    for hive, subkey, name in [
        (winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Valve\Steam', 'InstallPath'),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\Valve\Steam', 'InstallPath'),
    ]:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, name)
        except OSError:
            continue
        if value:
            return Path(value)
    return None


def libraries(game=None):
    paths = []
    if game:
        for parent in Path(game).resolve().parents:
            if parent.name.casefold() == 'steamapps':
                paths.append(parent.parent)
                break
    steam = steam_root()
    if steam:
        paths.append(steam)
        for config in (steam/'steamapps/libraryfolders.vdf', steam/'config/libraryfolders.vdf'):
            if config.is_file():
                for name, value in re.findall(r'"(path|\d+)"\s*"([^"\r\n]+)"', config.read_text('utf-8-sig'), flags=re.I):
                    lib = Path(value.replace('\\\\','\\'))
                    if lib.is_absolute():
                        paths.append(lib)
    return list(dict.fromkeys(paths))


def game_dir(asset_name):
    for library in libraries():
        apps = library/'steamapps'
        manifest = apps/f'appmanifest_{APP_ID}.acf'
        folders = [INSTALL_NAME]
        if manifest.is_file():
            name = re.search(r'"installdir"\s*"([^"]+)"', manifest.read_text('utf-8-sig'), re.I)
            if name and Path(name[1]).name == name[1] and name[1] not in ('.','..'):
                folders.insert(0, name[1])
        for folder in dict.fromkeys(folders):
            candidate = apps/'common'/folder
            if (candidate/asset_name).is_file():
                return candidate
    raise ValueError('未找到游戏，请用 --game-dir 指定其 Steam 安装目录。')


def workshop(game=None, expected_hash=None):
    import hashlib
    mismatch = None
    for library in libraries(game):
        folder = library/'steamapps/workshop/content'/APP_ID/ITEM_ID
        xml = folder/'text.xml'
        if xml.is_file():
            if expected_hash is None or hashlib.sha256(xml.read_bytes()).hexdigest() == expected_hash:
                return folder
            mismatch = folder
    if mismatch:
        raise ValueError('已找到工坊基包，但版本指纹不同。请核对 Steam 下载与本补丁支持的构建。')
    raise ValueError('未找到工坊物品 3523398274。请在 Steam 下载，或用 --base 指定其文件夹。')


def local_low():
    import ctypes as c
    from uuid import UUID
    # SHGetKnownFolderPath honours a redirected LocalLow even when USERPROFILE is standard.
    guid = (c.c_ubyte * 16).from_buffer_copy(UUID('A520A1A4-1780-4FF6-BD18-167343C5AF16').bytes_le)
    value = c.c_void_p()
    get = c.windll.shell32.SHGetKnownFolderPath
    get.argtypes = [c.c_void_p,c.c_uint32,c.c_void_p,c.POINTER(c.c_void_p)]
    get.restype = c.c_long
    try:
        if get(c.byref(guid), 0x4000, None, c.byref(value)) == 0 and value.value:
            return Path(c.wstring_at(value))
    finally:
        if value.value:
            free = c.windll.ole32.CoTaskMemFree
            free.argtypes = [c.c_void_p]
            free.restype = None
            free(value)
    return Path(os.environ.get('USERPROFILE', str(Path.home())))/'AppData/LocalLow'


def user_data(override=None):
    if override is not None:
        return Path(override)
    current = local_low()/DATA_FOLDER
    legacy = Path(os.environ.get('USERPROFILE', str(Path.home())))/'AppData/LocalLow'/DATA_FOLDER
    record = '.zhcn-coldwar-install.json'
    if legacy != current and (legacy/record).is_file() and not (current/record).is_file():
        return legacy
    return current
