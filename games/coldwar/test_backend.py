"""Offline checks for Cold War's portable path discovery and font rebuild sources."""
from pathlib import Path
from argparse import Namespace
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch as mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import game_paths
import font_patch
import patch


class PortableBackendTests(unittest.TestCase):
    def test_manifest_and_separate_workshop_library(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            client = root/'Steam'
            games = root/'游戏库'
            workshop = root/'工坊库'
            for lib in (client, games, workshop):
                (lib/'steamapps').mkdir(parents=True)
            config = '\n'.join('"path" "' + str(lib).replace('\\','\\\\') + '"' for lib in (games,workshop))
            (client/'steamapps/libraryfolders.vdf').write_text(config,'utf-8')
            manifest = games/f'steamapps/appmanifest_{game_paths.APP_ID}.acf'
            manifest.write_text('"installdir" "Custom folder"','utf-8')
            game = games/'steamapps/common/Custom folder'
            asset = game/font_patch.FILE
            asset.parent.mkdir(parents=True)
            asset.touch()
            item = Path('steamapps/workshop/content')/game_paths.APP_ID/game_paths.ITEM_ID
            for lib,data in ((games,b'stale'),(workshop,b'expected')):
                (lib/item).mkdir(parents=True)
                (lib/item/'text.xml').write_bytes(data)
            with mock.object(game_paths,'steam_root',return_value=client):
                self.assertEqual(font_patch.asset_location(None),asset)
                self.assertEqual(font_patch.asset_location(game),asset)
                self.assertEqual(game_paths.workshop(game,hashlib.sha256(b'expected').hexdigest()),workshop/item)

    def test_redirected_user_data_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            profile = root/'profile'
            low = root/'redirected'
            override = root/'explicit'
            with mock.dict(os.environ,{'USERPROFILE':str(profile)}), mock.object(game_paths,'local_low',return_value=low):
                self.assertEqual(game_paths.user_data(),low/game_paths.DATA_FOLDER)
                self.assertEqual(game_paths.user_data(override),override)

    def test_local_rebuild_materials(self):
        source = HERE/'font-source'
        expected = '5e0db897530eb471208c18ab3af96fe964a6c8887ebded8af95c10850b5d2b6f'
        self.assertEqual(hashlib.sha256((source/'KremlinDonorSC-Regular.ttf').read_bytes()).hexdigest(),expected)
        for name in ('OFL.txt','OFL-Latin.txt'):
            self.assertIn('SIL OPEN FONT LICENSE',(source/name).read_text('utf-8-sig'))
        self.assertEqual(hashlib.sha256((HERE/'font.bsdiff').read_bytes()).hexdigest(),font_patch.DELTA_SHA)

    def test_workshop_needed_until_previous_activation_finishes(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            folder = root / "mods" / patch.MOD
            folder.mkdir(parents=True)
            manifest = root / ".zhcn-coldwar-install.json"
            self.assertFalse(patch.has_local_base(root))
            state = {"format": 1, "files": {"text.xml": patch.V1_2_XML}, "pending_activation": True}
            manifest.write_bytes(patch.json_bytes(state))
            self.assertFalse(patch.has_local_base(root))
            del state["pending_activation"]
            manifest.write_bytes(patch.json_bytes(state))
            self.assertTrue(patch.has_local_base(root))

    def test_interrupted_upgrade_allows_only_a_known_later_xml(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            for filename in patch.OWN_FILES:
                (folder / filename).write_bytes(filename.encode())
            files = {name: patch.sha((folder / name).read_bytes()) for name in patch.OWN_FILES}
            versions = tuple(patch.sha(value) for value in (b"one", b"two", b"three"))
            with mock.object(patch, "GENERATIONS", versions):
                files["text.xml"] = versions[1]
                xml = folder / "text.xml"
                xml.write_bytes(b"three")
                patch.verify_generation(folder, files)
                for other in (b"one", b"custom"):
                    xml.write_bytes(other)
                    with self.assertRaises(ValueError):
                        patch.verify_generation(folder, files)
                xml.write_bytes(b"two")
                (folder / "icon.png").write_bytes(b"custom icon")
                with self.assertRaises(ValueError):
                    patch.verify_generation(folder, files)


@unittest.skipUnless(all(os.environ.get(k) for k in ("COLDWAR_TEST_GAME", "COLDWAR_TEST_BASE", "COLDWAR_OLD_PATCH")),
                     "Requires a local game, Workshop base and v1.2.0 source folder")
class RealUpgradeTests(unittest.TestCase):
    def test_v120_offline_upgrade_and_restore(self):
        game = Path(os.environ["COLDWAR_TEST_GAME"])
        workshop = Path(os.environ["COLDWAR_TEST_BASE"])
        old_patch = Path(os.environ["COLDWAR_OLD_PATCH"]) / "patch.py"
        spec = importlib.util.spec_from_file_location("previous_coldwar_patch", old_patch)
        previous = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(previous)
        self.assertEqual(previous.RELEASE_XML, patch.V1_2_XML)
        original = (game / font_patch.FILE).read_bytes()
        if patch.sha(original) == font_patch.PATCHED_SHA:
            backup = game_paths.user_data() / ".zhcn-original-sharedassets0.assets"
            original = backup.read_bytes()
        self.assertEqual(patch.sha(original), font_patch.ASSET_SHA)
        with tempfile.TemporaryDirectory() as name, ExitStack() as mocks:
            sandbox = Path(name)
            profile = sandbox / "player"
            game_copy = sandbox / "game"
            asset = game_copy / font_patch.FILE
            asset.parent.mkdir(parents=True)
            asset.write_bytes(original)
            pref = [None]
            def read_pref():
                rows = json.loads(pref[0].rstrip(b"\0")) if pref[0] else []
                return pref[0], rows
            for module in (previous, patch):
                mocks.enter_context(mock.object(module, "game_running", return_value=False))
                mocks.enter_context(mock.object(module, "read_pref", read_pref))
                mocks.enter_context(mock.object(module, "write_pref", lambda value: pref.__setitem__(0, value)))
            args = Namespace(action="install", game_dir=game_copy, data_dir=profile, output=None, base=workshop)
            self.assertFalse(patch.has_local_base(profile))
            previous.run(args)
            folder = profile / "mods" / patch.MOD
            self.assertEqual(patch.sha((folder / "text.xml").read_bytes()), patch.V1_2_XML)
            first_backup = profile / ".zhcn-original-sharedassets0.assets"
            stamp = first_backup.stat().st_mtime_ns
            self.assertTrue(patch.has_local_base(profile))
            args.base = None
            rows = read_pref()[1] + [{"id": "another-player-mod", "isLoaded": True}]
            pref[0] = patch.encoded(rows)
            original_pref = pref[0]
            mocks.enter_context(mock.object(patch, "discover", side_effect=AssertionError("Workshop access")))
            patch.run(args)
            args.action = "verify"
            patch.run(args)
            self.assertEqual(patch.sha((folder / "text.xml").read_bytes()), patch.RELEASE_XML)
            self.assertEqual(pref[0], original_pref)
            self.assertEqual(first_backup.stat().st_mtime_ns, stamp)
            args.action = "restore"
            patch.run(args)
            self.assertEqual(asset.read_bytes(), original)
            self.assertEqual(read_pref()[1], [rows[-1]])


if __name__=='__main__':
    unittest.main()
