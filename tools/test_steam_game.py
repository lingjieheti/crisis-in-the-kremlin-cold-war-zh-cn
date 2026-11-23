"""Regression tests for this project's Steam installation discovery. No Steam client is needed."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import steam_game


def vdf_path(path):
    return str(path).replace("\\", "\\\\")


class SteamGameTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="steam-locate-")
        self.addCleanup(workspace.cleanup)
        self.workspace = Path(workspace.name).resolve()
        self.client = self.workspace / "Steam 客户端"
        self.library = self.workspace / "第二个 Steam 库"
        self.apps = self.client / "steamapps"
        self.apps.mkdir(parents=True)

    def make_game(self, game):
        for marker in (steam_game.EXECUTABLE, steam_game.ASSET):
            file = game / marker
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"fixture")
        return game

    def manifest(self, library, folder):
        apps = library / "steamapps"
        apps.mkdir(parents=True, exist_ok=True)
        path = apps / f"appmanifest_{steam_game.APP_ID}.acf"
        path.write_text(f'"AppState"\n{{\n"appid" "{steam_game.APP_ID}"\n"installdir" "{folder}"\n}}\n',
                        encoding="utf-8-sig")

    def test_modern_library_and_custom_install_dir(self):
        config = ('"libraryfolders"\n{\n"0"\n{\n"path" "' + vdf_path(self.client) +
                  '"\n}\n"1"\n{\n"path" "' + vdf_path(self.library) +
                  '"\n"apps"\n{\n"' + steam_game.APP_ID + '" "4294967296"\n}\n}\n}\n')
        (self.apps / "libraryfolders.vdf").write_text(config, encoding="utf-8-sig")
        folder = "自定义 安装目录"
        self.manifest(self.library, folder)
        game = self.make_game(self.library / "steamapps/common" / folder)
        self.assertEqual(steam_game.libraries([self.client]), [self.client, self.library])
        self.assertEqual(steam_game.locate([self.client]), game)
        self.assertEqual(steam_game.validate(game), game)

    def test_legacy_libraries_ignore_relative_entries_and_duplicates(self):
        config = ('"LibraryFolders"\n{\n"1" "' + vdf_path(self.library) +
                  '"\n"2" "relative_path"\n"3" "' + vdf_path(self.library) + '"\n}\n')
        (self.apps / "libraryfolders.vdf").write_text(config, encoding="utf-8")
        game = self.make_game(self.library / "steamapps/common" / steam_game.GAME_FOLDER)
        self.assertEqual(steam_game.libraries([self.client, self.library]), [self.client, self.library])
        self.assertEqual(steam_game.locate([self.client]), game)

    def test_manifest_name_precedes_default_within_same_library(self):
        self.make_game(self.apps / "common" / steam_game.GAME_FOLDER)
        custom = self.make_game(self.apps / "common/另一安装目录")
        self.manifest(self.client, custom.name)
        self.assertEqual(steam_game.locate([self.client]), custom)

    def test_invalid_manifest_cannot_select_other_directories(self):
        common = self.apps / "common"
        common.mkdir()
        outside = self.make_game(self.apps / "outside")
        nested = self.make_game(common / "subdir/game")
        # Each of these paths is absolute, has a directory component, or
        # names the parent. None is a single Steam install-folder name.
        for invalid in ("../outside", r"..\outside", str(outside), vdf_path(outside),
                        "subdir/game", r"subdir\game", ".", ".."):
            with self.subTest(invalid=invalid):
                self.manifest(self.client, invalid)
                with self.assertRaises(ValueError):
                    steam_game.locate([self.client])
        self.assertTrue((outside / steam_game.ASSET).is_file())
        self.assertTrue((nested / steam_game.EXECUTABLE).is_file())

    def test_missing_installation_and_mismatched_markers(self):
        self.manifest(self.client, "尚未安装")
        with self.assertRaises(ValueError):
            steam_game.locate([self.client])
        for marker in (steam_game.EXECUTABLE, steam_game.ASSET):
            with self.subTest(marker=marker):
                with tempfile.TemporaryDirectory(dir=self.workspace) as location:
                    game = Path(location)
                    partial = game / marker
                    partial.parent.mkdir(parents=True, exist_ok=True)
                    partial.write_bytes(b"wrong installation")
                    with self.assertRaises(ValueError):
                        steam_game.validate(game)
        with self.assertRaises(ValueError):
            steam_game.validate(self.workspace / "目录不存在")


if __name__ == "__main__":
    unittest.main()
