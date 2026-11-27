"""Recover only a published v1.2.3 assembly to its exact Steam original."""
import hashlib
from pathlib import Path
import stat

import font_patch
import game_paths

FILE = Path("CrisisInTheKremlin2_Data/Managed/Assembly-CSharp.dll")
SIGNATURE = Path("CrisisInTheKremlin2_Data/StreamingAssets/build.sig")
SIGNATURES = {
    "26243566": "dca9b83cf8e1a410c163e14aa2086d520a47a526092d960e8605005923a04531",
    "26891377": "da9ae7e4877f0c69e833503ebb2731d3b64db82f1e4b7210af274241f09a67c7",
    "26955082": "542ce460fd1773680ddb8b14ab65e73cc92f3c85e6e563848a3206a13866ab98",
    "26977018": "84df489d12142391ccf0d92dcee698b15082d4c8d382cf81e39eca5c94517d5a",
}
ASSEMBLIES = {
    "26977018": ("038ba27628d1b79a63440ce3a12fc50977364340db472acfd3ab7aa492731eab", None),
    "26243566": ("1fbd571bbe4dec5cd49928d99c2358adcbe3d8cc21ece99b4508dd6820bfbfc2",
                 "a6224a1d8a104336f6bd819dd25536c662cc414c3b5790fd206f9f9511607ab9"),
    "26891377": ("980c26a8cd82fa47576f74b89edc8b3677b5be34466702b72e569053ef964228",
                 "398a079b800a8f6ce61269b0255ee7ab6239e21576d4964d4241ccb915707c6d"),
    "26955082": ("df0462e258330357be607626e6ae18dc735d6d575af8e42acc999d00b1c19d89",
                 "4bac60c0fdfe114bdd2498faa2d854974bf1aa7a0350f3cf53e22c330a8badb1"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def regular(path):
    return path.is_file() and not (getattr(path.lstat(),"st_file_attributes",0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def manage(game, profile, build, action):
    if action not in ("preflight", "verify", "install", "restore") or build not in ASSEMBLIES:
        raise ValueError("未支持的构建或核验操作。")
    game = Path(game) if game is not None else game_paths.game_dir(FILE)
    path = game / FILE
    backup = profile / (".zhcn-original-assembly-" + build + ".dll")
    original, released_v123 = ASSEMBLIES[build]
    repair = "请先保存自己的修改，并在 Steam 游戏属性的“已安装文件”中验证游戏文件完整性。"
    if not regular(path):
        raise ValueError("无法验证本构建的游戏程序。" + repair)
    current = digest(path)
    if current not in (original, released_v123):
        raise ValueError("游戏程序集与已知的 Steam 构建不符。" + repair)
    signature = game / SIGNATURE
    if not regular(signature) or digest(signature) != SIGNATURES[build]:
        raise ValueError("游戏签名文件与对应 Steam 构建不符。" + repair)
    if released_v123 is None:
        return  # This resource-only build has no legacy assembly or backup to migrate.
    if action == "verify":
        if current != original:
            raise ValueError("仍装有 v1.2.3 的游戏程序。退出游戏后请运行 install 升级到纯资源版。")
        return
    if current == original:
        # Steam may already have restored this file. Leave unrelated backup contents alone.
        if action != "preflight" and regular(backup) and digest(backup) == original:
            backup.unlink()
        return
    if not regular(backup) or digest(backup) != original:
        raise ValueError("找不到经过核验的本构建官方原件备份。" + repair)
    if action == "preflight":
        return
    data = backup.read_bytes()
    if hashlib.sha256(data).hexdigest() != original or digest(path) != released_v123:
        raise ValueError("迁移时游戏程序或备份发生变化。" + repair)
    font_patch.replace_atomic(path, data)
    if digest(path) != original:
        raise ValueError("恢复后的游戏程序未通过官方原件哈希核验。" + repair)
    backup.unlink()
