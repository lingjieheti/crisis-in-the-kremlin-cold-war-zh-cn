"""Keep the screen mode and refresh rate on one line in the graphics settings."""

from pathlib import Path

import font_patch


FILE = "CrisisInTheKremlin2_Data/level3"
# Canvas/Back/ScreenSettings/Scroll View/Viewport/Content/Text (0)/Selector/Selected.
# Unity serializes the same TMP fields at the same local offsets in these two releases.
SCENES = {
    "26891377": (174008,
                 "667080c08a37f81e423a90322cc427d4ab91a8e88178e53882e385632630ee94",
                 "e9a7127bf38b563811dc01f787133b77d0e91b81b5452b9677b513dc9faec822"),
    "26955082": (178744,
                 "7b989187422ff1dbf353e5b4153a93f6685fcb9de153a693fd1c7dba193693bf",
                 "3bf2cdd9e1e721fd820cf131f4a1e32172ed4efafbc1a15f29fccb790956718b"),
}
# Enable auto-sizing from 24 to 50, disable wrapping and leave 20 units by each arrow.
FIELDS = ((304, 0, 1), (310, 144, 192), (314, 144, 72), (356, 1, 0),
          (454, 0, 160), (455, 0, 65), (462, 0, 160), (463, 0, 65))


def manage(game_dir, build, action):
    if str(build) == "26243566":
        return
    profile = SCENES.get(str(build))
    if profile is None:
        raise ValueError("此游戏构建没有经过校验的显示设置布局。")
    if action not in ("install", "preflight", "restore", "verify"):
        raise ValueError("无法识别显示设置布局操作。")
    if game_dir is None:
        import game_paths
        game_dir = game_paths.game_dir(FILE)
    path = Path(game_dir) / FILE
    source = path.read_bytes()
    start, original, localized = profile
    checksum = font_patch.digest(source)
    if checksum not in (original, localized):
        raise ValueError("游戏设置场景的校验值与当前 Steam 构建不符。")
    if action == "verify":
        if checksum != localized:
            raise ValueError("请先安装本版本的分辨率排版修订。")
        return
    if action == "preflight":
        return
    restoring = action == "restore"
    target = original if restoring else localized
    if checksum == target:
        return
    result = bytearray(source)
    for relative, before, after in FIELDS:
        result[start + relative] = before if restoring else after
    if font_patch.digest(result) != target:
        raise ValueError("游戏设置场景的写入前校验未通过。")
    font_patch.replace_atomic(path, result)
