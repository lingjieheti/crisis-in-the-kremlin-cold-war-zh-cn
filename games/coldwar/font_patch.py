"""Rebuild the OFL Chinese fallback in this exact Steam build (stdlib only)."""
import bz2
import hashlib
import os
from pathlib import Path
import struct
import tempfile
from typing import NamedTuple

ASSET_SHA = "98cb77fc3fa197e58ef69cf9c947dc0d52685fcb32b34fe68f0a8c238f968636"
FONT_SHA = "2f2cee5fbb2403df352ca2005247f6c4faa70f3086ebd31b6c62308b5f2f9865"
NEW_FONT_SHA = "451d556e01e42cab95ad3beba0d5c5ca1f6639662272e59e6b177ae94d3f663e"
DELTA_SHA = "92a47e1493caa64e54b96299689cd9329091b47d602f468b525c214a3236efa7"
PATCHED_SHA = "9a56ef96532edba1f0746da8f37ee30290ec1e1c7ca67b2e9b4cc976f20a2772"
RAW_START = 13724120
FONT_SIZE = 15515760
OBJECT_START = 13724024
OBJECT_SIZE = 15515910
ENTRY = 3840
DATA_START = 21872
FILE = "CrisisInTheKremlin2_Data/sharedassets0.assets"

class AssetLayout(NamedTuple):
    original: str
    patched: str
    data_start: int
    object_start: int
    backup: str


CURRENT = AssetLayout(ASSET_SHA, PATCHED_SHA, DATA_START, OBJECT_START,
                      ".zhcn-original-sharedassets0-26955082.assets")
INTERIM = AssetLayout("a576c46e61b2bdd7d9f6c2408d3e0d300da1cfd6dc066d97fc1dae0a5147650a",
                      "58cea05ac2ea84b753c66516fc062080e7cc87a97a0064f3720257ffa9b33df3",
                      21600, 13723752,
                      ".zhcn-original-sharedassets0-26891377.assets")
PREVIOUS = AssetLayout("1a60905fd2166bd95ed1378f97b687c1611ecafcb880cc8ab09783e37d548adb",
                       "9aa1fd1f314ca38ee87bbff95abfeb93d5066068d96f6952ec57e70603a23dc5",
                       20480, 13721160, ".zhcn-original-sharedassets0.assets")

def asset_layout(checksum):
    for layout in (CURRENT, INTERIM, PREVIOUS):
        if checksum in (layout.original, layout.patched):
            return layout
    raise ValueError("当前游戏字体资源与已适配的 Steam 构建不符。")

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
    checksum = digest(original)
    layout = asset_layout(checksum)
    expect(checksum == layout.original, "重建字体需要该版本的 Steam 原件。")
    raw_start = layout.object_start + 96
    expected_record = struct.pack("<qQIi", 145, layout.object_start-layout.data_start, OBJECT_SIZE, 7)
    expect(original[ENTRY:ENTRY+24] == expected_record, "Unity 字体对象表与已测试版本不同。")
    old = original[raw_start:raw_start+FONT_SIZE]
    expect(digest(old) == FONT_SHA, "未找到原始字体。")
    new = apply_bsdiff(old, delta)
    # Relocate only Font 145. All other serialized objects retain their offsets.
    obj = original[layout.object_start:raw_start-4] + struct.pack("<I",len(new)) + new
    obj += bytes((-len(obj)) % 4)
    obj += original[raw_start+FONT_SIZE:layout.object_start+OBJECT_SIZE]
    result = bytearray(original)
    result.extend(bytes((-len(result)) % 8))
    offset = len(result)
    result.extend(obj)
    struct.pack_into("<QI", result, ENTRY+8, offset-layout.data_start, len(obj))
    struct.pack_into(">Q", result, 24, len(result))
    return bytes(result)

def font_payload(asset, patched=True):
    """Read the active patched font or the original OFL font from either known build."""
    checksum = digest(asset)
    layout = asset_layout(checksum)
    if patched:
        expect(checksum == layout.patched, "需要读取已经安装的中文字体。")
        offset = layout.data_start + struct.unpack_from("<Q", asset, ENTRY + 8)[0] + 96
        length = struct.unpack_from("<I", asset, offset - 4)[0]
    else:
        # A patched asset appends Font 145 and retains the original bytes in place.
        offset, length = layout.object_start + 96, FONT_SIZE
    payload = asset[offset:offset + length]
    expect(digest(payload) == (NEW_FONT_SHA if patched else FONT_SHA), "字体内容校验失败。")
    return payload

def asset_location(game, base=None):
    if game is None:
        import game_paths
        game = game_paths.game_dir(FILE)
    return Path(game)/FILE

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
    current = path.read_bytes()
    hash_now = digest(current)
    layout = asset_layout(hash_now)
    backup = root / layout.backup
    if action in ("install", "preflight"):
        if backup.exists():
            expect(digest(backup.read_bytes()) == layout.original, "本地原始字体备份的校验不符。")
        if hash_now == layout.patched:
            expect(backup.exists(), "汉化字体已写入，但原始资源备份缺失。")
            return
        if action == "preflight":
            return
        patched = build_assets(current, (Path(__file__).parent/"font.bsdiff").read_bytes())
        expect(digest(patched) == layout.patched, "写入前字体资源校验失败。")
        if not backup.exists():
            replace_atomic(backup, current)
        replace_atomic(path, patched)
    elif action == "verify":
        expect(hash_now == layout.patched and backup.exists() and digest(backup.read_bytes()) == layout.original, "当前游戏字体或原始备份不匹配。")
    elif action == "restore":
        if hash_now == layout.patched:
            expect(backup.is_file() and digest(backup.read_bytes()) == layout.original, "无法还原：原始字体备份不完整。")
            replace_atomic(path, backup.read_bytes())
        if backup.exists():
            expect(digest(backup.read_bytes()) == layout.original, "备份已被修改，已保留。")
            backup.unlink()
