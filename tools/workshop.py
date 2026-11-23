"""Locate a community base on disk, or ask the game's Steamworks client to cache it."""
import argparse
import ctypes as c
import hashlib
import os
from pathlib import Path
import sys
import time

ITEMS = {
    "coldwar": (1922740, 3523398274, "Crisis in the Kremlin Cold War", "CrisisInTheKremlin2_Data",
                "e082bf5c9f881c822b1540a76b74f9d15e18019a73ebd206a559595badcb7f65", "text.xml"),
}

GAME_FILES = Path(__file__).resolve().parents[1] / "games/coldwar"
sys.path.insert(0, str(GAME_FILES))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from game_paths import workshop
from steam_game import locate, validate

class Callback(c.Structure):
    _fields_ = [("user", c.c_int32), ("kind", c.c_int32), ("data", c.c_void_p), ("size", c.c_int32)]

def fetch(game, app, item, dll, expected):
    if hashlib.sha256(dll.read_bytes()).hexdigest() != expected:
        raise ValueError("游戏随附的 Steamworks 版本已变化，请通过创意工坊获取基包。")
    os.environ["SteamAppId"] = os.environ["SteamGameId"] = str(app)
    os.chdir(game)
    client = c.CDLL(str(dll))
    def bind(name, result, *arguments):
        f = getattr(client, name)
        f.restype, f.argtypes = result, list(arguments)
        return f
    ptr = c.c_void_p
    err = c.create_string_buffer(1024)
    if bind("SteamAPI_InitFlat", c.c_int, ptr)(err):
        raise ValueError("请先启动 Steam，登录拥有本游戏的账号。")
    try:
        bind("SteamAPI_ManualDispatch_Init", None)()
        pipe = bind("SteamAPI_GetHSteamPipe", c.c_int32)()
        ugc = bind("SteamAPI_SteamUGC_v021", ptr)()
        download = bind("SteamAPI_ISteamUGC_DownloadItem", c.c_bool, ptr, c.c_uint64, c.c_bool)
        if not ugc or not download(ugc, item, False):
            raise ValueError("Steam 未能开始下载。")
        frame = bind("SteamAPI_ManualDispatch_RunFrame", None, c.c_int32)
        poll = bind("SteamAPI_ManualDispatch_GetNextCallback", c.c_bool, c.c_int32, c.POINTER(Callback))
        free = bind("SteamAPI_ManualDispatch_FreeLastCallback", None, c.c_int32)
        deadline = time.monotonic() + 120
        msg = Callback()
        while time.monotonic() < deadline:
            frame(pipe)
            while poll(pipe, c.byref(msg)):
                try:
                    if msg.kind != 3406 or msg.size not in (16, 20, 24):
                        continue
                    payload = c.string_at(msg.data, msg.size)
                    offset = 4 if msg.size == 16 else 8
                    if int.from_bytes(payload[:4], "little") != app:
                        continue
                    if int.from_bytes(payload[offset:offset+8], "little") != item:
                        continue
                    result = int.from_bytes(payload[offset+8:offset+12], "little")
                    if result != 1:
                        raise ValueError(f"Steam 下载结果为 {result}。")
                    return
                finally:
                    free(pipe)
            time.sleep(0.15)
        raise ValueError("等待 Steam 下载超时。请在 Steam 下载页面查看进度。")
    finally:
        bind("SteamAPI_Shutdown", None)()

def obtain(key, game_dir=None):
    app, item, _, data_dir, sha, _ = ITEMS[key]
    game = validate(game_dir) if game_dir else locate()
    # Use the same fingerprint as the patch backend before deciding to download.
    from patch import XML_HASH
    try:
        workshop(game, XML_HASH)
        return
    except ValueError:
        pass
    print("正在通过 Steam 下载社区翻译底包…", flush=True)
    fetch(game, app, item, game / data_dir / "Plugins/x86_64/steam_api64.dll", sha)
    workshop(game, XML_HASH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", choices=ITEMS)
    parser.add_argument("--game-dir", type=Path)
    args = parser.parse_args()
    try:
        obtain(args.game, args.game_dir)
    except (OSError, ValueError, AttributeError) as error:
        sys.exit(f"{error}\n也可在 Steam 订阅社区翻译后重试：\nhttps://steamcommunity.com/sharedfiles/filedetails/?id={ITEMS[args.game][1]}")
