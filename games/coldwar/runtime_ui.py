"""Build and verify opt-in interface language support from the player's original assembly."""
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import zipfile

import font_patch
import game_paths


HERE = Path(__file__).resolve().parent / "runtime"
FILE = Path("CrisisInTheKremlin2_Data/Managed/Assembly-CSharp.dll")
CECIL_SHA = "d2a23832aaa948ba9a01acc42b5726e34c5f995958f1b30d45c0e7c70b3a72d5"
ASSEMBLIES = {
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


def compile_rules(path, build):
    path = path.resolve()
    csc = Path(os.environ["WINDIR"])/"Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not csc.is_file():
        csc = Path(os.environ["WINDIR"])/"Microsoft.NET/Framework/v4.0.30319/csc.exe"
    if not csc.is_file():
        raise ValueError("没有找到 Windows .NET Framework 编译器。")
    package = HERE/"mono.cecil.0.11.6.nupkg"
    if digest(package) != CECIL_SHA:
        raise ValueError("离线构建组件的校验值不符。")
    with tempfile.TemporaryDirectory(prefix="coldwar-labels-") as tmp:
        work = Path(tmp)
        with zipfile.ZipFile(package) as archive:
            (work/"Mono.Cecil.dll").write_bytes(archive.read("lib/net40/Mono.Cecil.dll"))
        def run(args):
            result = subprocess.run(args, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
            if result.returncode:
                detail = result.stdout.decode(errors="replace")[-1200:]
                raise ValueError("无法构建当前游戏的界面文字：" + detail)
        run([csc,"/nologo","/optimize+","/codepage:65001","/target:library","/r:System.Xml.Linq.dll",
             "/out:LabelText.dll",str(HERE/"LabelText.cs")])
        run([csc,"/nologo","/optimize+","/codepage:65001","/r:Mono.Cecil.dll",
             "/out:BuildLabels.exe",str(HERE/"BuildLabels.cs")])
        run([work/"BuildLabels.exe",path,work/"localized.dll",work/"LabelText.dll",build])
        localized = work/"localized.dll"
        if digest(localized) != ASSEMBLIES[build][1]:
            raise ValueError("生成的界面文本程序集与本版本不符。")
        return localized.read_bytes()


def manage(game, profile, build, action):
    game = Path(game) if game is not None else game_paths.game_dir(FILE)
    path = game/FILE
    original, patched = ASSEMBLIES[build]
    backup = profile / (".zhcn-original-assembly-" + build + ".dll")
    if not regular(path) or (backup.exists() and not regular(backup)):
        raise ValueError("找不到游戏程序集，或原件备份位置已被重定向。")
    current = digest(path)
    if current not in (original,patched) or (backup.exists() and digest(backup) != original):
        raise ValueError("游戏程序集或已有备份与本 Steam 构建不符。请先保存自己的修改。")
    if current == patched and not backup.exists():
        raise ValueError("找不到本构建的原始程序集备份。")
    if action == "preflight":
        return
    if action == "verify":
        if current != patched:
            raise ValueError("请先安装本版界面汉化。")
    elif action == "install":
        if current == original:
            localized = compile_rules(path,build)
            if not backup.exists():
                font_patch.replace_atomic(backup,path.read_bytes())
            font_patch.replace_atomic(path,localized)
    elif action == "restore":
        if current == patched:
            font_patch.replace_atomic(path,backup.read_bytes())
        if backup.exists():
            backup.unlink()
    else:
        raise ValueError("无法识别界面文字处理命令。")
