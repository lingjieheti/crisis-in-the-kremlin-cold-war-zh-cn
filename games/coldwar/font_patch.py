"""Rebuild the OFL Chinese fallback in this exact Steam build (stdlib only)."""
import bz2
import hashlib
import os
from pathlib import Path
import struct
import tempfile

ASSET_SHA = "1a60905fd2166bd95ed1378f97b687c1611ecafcb880cc8ab09783e37d548adb"
FONT_SHA = "2f2cee5fbb2403df352ca2005247f6c4faa70f3086ebd31b6c62308b5f2f9865"
NEW_FONT_SHA = "451d556e01e42cab95ad3beba0d5c5ca1f6639662272e59e6b177ae94d3f663e"
DELTA_SHA = "92a47e1493caa64e54b96299689cd9329091b47d602f468b525c214a3236efa7"
PATCHED_SHA = "9aa1fd1f314ca38ee87bbff95abfeb93d5066068d96f6952ec57e70603a23dc5"
RAW_START = 13721256
FONT_SIZE = 15515760
OBJECT_START = 13721160
OBJECT_SIZE = 15515910
ENTRY = 3840
DATA_START = 20480
FILE = "CrisisInTheKremlin2_Data/sharedassets0.assets"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def expect(ok, message):
    if not ok:
        raise ValueError(message)

def signed(value):
    magnitude = int.from_bytes(value, "little")
    return -(magnitude & ((1 << 63) - 1)) if magnitude >> 63 else magnitude

def apply_bsdiff(original, delta):
    expect(digest(delta) == DELTA_SHA and delta[:8] == b"BSDIFF40", "字体差分文件损坏。")
    ctl_len, diff_len, size = [signed(delta[i:i+8]) for i in (8, 16, 24)]
    pos = 32 + ctl_len
    ctl = bz2.decompress(delta[32:pos])
    diff = bz2.decompress(delta[pos:pos+diff_len])
    extra = bz2.decompress(delta[pos+diff_len:])
    output = bytearray()
    oi = di = ei = 0
    for i in range(0, len(ctl), 24):
        add, insert, advance = [signed(ctl[j:j+8]) for j in (i, i+8, i+16)]
        expect(add >= 0 and insert >= 0 and len(output) + add + insert <= size, "无效字体差分。")
        chunk = bytearray(diff[di:di+add])
        lo = max(0, -oi)
        hi = min(add, len(original) - oi)
        if hi > lo:
            chunk[lo:hi] = bytes((a+b) & 255 for a,b in zip(chunk[lo:hi], original[oi+lo:oi+hi]))
        output.extend(chunk)
        output.extend(extra[ei:ei+insert])
        oi += add + advance
        di += add
        ei += insert
    expect(len(output) == size and digest(output) == NEW_FONT_SHA, "字体重建校验失败。")
    return bytes(output)

def build_assets(original, delta):
    expect(digest(original) == ASSET_SHA, "游戏字体资源版本不匹配。")
    expected_record = struct.pack("<qQIi", 145, OBJECT_START-DATA_START, OBJECT_SIZE, 7)
    expect(original[ENTRY:ENTRY+24] == expected_record, "Unity 字体对象表与已测试版本不同。")
    old = original[RAW_START:RAW_START+FONT_SIZE]
    expect(digest(old) == FONT_SHA, "未找到原始字体。")
    new = apply_bsdiff(old, delta)
    # Relocate only Font 145. All other serialized objects retain their offsets.
    obj = original[OBJECT_START:RAW_START-4] + struct.pack("<I",len(new)) + new
    obj += bytes((-len(obj)) % 4)
    obj += original[RAW_START+FONT_SIZE:OBJECT_START+OBJECT_SIZE]
    result = bytearray(original)
    result.extend(bytes((-len(result)) % 8))
    offset = len(result)
    result.extend(obj)
    struct.pack_into("<QI", result, ENTRY+8, offset-DATA_START, len(obj))
    struct.pack_into(">Q", result, 24, len(result))
    return bytes(result)

def asset_location(game, base=None):
    if game is not None:
        return Path(game) / FILE
    import winreg, re
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
        steam = Path(winreg.QueryValueEx(key, "SteamPath")[0])
    libraries = [steam]
    libraries.extend(Path(p.replace("\\\\","\\")) for p in re.findall(r'"path"\s+"([^"]+)"', (steam/"steamapps/libraryfolders.vdf").read_text("utf-8-sig")))
    for lib in dict.fromkeys(libraries):
        p = lib/"steamapps/common/Crisis in the Kremlin Cold War"/FILE
        if p.is_file():
            return p
    raise ValueError("找不到游戏目录，请用 --game-dir 指定。")

def replace_atomic(path, payload, staging_dir=None):
    fd, temp = tempfile.mkstemp(dir=staging_dir or path.parent, prefix=".zhcn-")
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        Path(temp).unlink(missing_ok=True)

def manage(path, root, action):
    backup = root / ".zhcn-original-sharedassets0.assets"
    current = path.read_bytes()
    hash_now = digest(current)
    if action in ("install", "preflight"):
        expect(hash_now in (ASSET_SHA, PATCHED_SHA), "游戏资源已更新或由其他模组改动；请使用适配此版本的补丁。")
        if backup.exists():
            expect(digest(backup.read_bytes()) == ASSET_SHA, "本地原始字体备份的校验不符。")
        if hash_now == PATCHED_SHA:
            expect(backup.exists(), "汉化字体已写入，但原始资源备份缺失。")
            return
        if action == "preflight":
            return
        patched = build_assets(current, (Path(__file__).parent/"font.bsdiff").read_bytes())
        expect(digest(patched) == PATCHED_SHA, "写入前字体资源校验失败。")
        if not backup.exists():
            replace_atomic(backup, current)
        replace_atomic(path, patched)
    elif action == "verify":
        expect(hash_now == PATCHED_SHA and backup.exists() and digest(backup.read_bytes()) == ASSET_SHA, "当前游戏字体或原始备份不匹配。")
    elif action == "restore":
        if hash_now == PATCHED_SHA:
            expect(backup.is_file() and digest(backup.read_bytes()) == ASSET_SHA, "无法还原：原始字体备份不完整。")
            replace_atomic(path, backup.read_bytes())
        if backup.exists():
            expect(hash_now in (ASSET_SHA, PATCHED_SHA), "游戏资源已由其他程序更改，已保留备份供手动核对。")
            expect(digest(backup.read_bytes()) == ASSET_SHA, "备份已被修改，已保留。")
            backup.unlink()
