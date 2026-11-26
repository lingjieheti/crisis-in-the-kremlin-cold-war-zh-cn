"""Offline checks for Cold War's portable path discovery and font rebuild sources."""
from pathlib import Path
from argparse import Namespace
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
import shutil
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
import audit


class PortableBackendTests(unittest.TestCase):
    def test_mixed_steam_depots_fail_before_patching(self):
        data = b"current font bytes"
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "sharedassets0.assets"
            asset.write_bytes(data)
            current = font_patch.CURRENT._replace(original=patch.sha(data))
            with mock.object(font_patch,"CURRENT",current):
                patch.check_font_build(asset,patch.BUILD)
                with self.assertRaisesRegex(ValueError,"不同 Steam 构建"):
                    patch.check_font_build(asset,patch.PLANETARIUM_BUILD)
            self.assertEqual(asset.read_bytes(),data)

    def test_hotfix_offline_and_direct_paths_have_identical_bytes(self):
        legacy = b"<t><ui><old>old</old><apply>apply</apply></ui></t>"
        interim = b"<t build='7'><ui><old>old</old><apply>apply</apply><planet>new</planet></ui></t>"
        latest = b"<t build='8'><ui><new>hint</new><planet>new</planet><old>old</old></ui></t>"
        updates7 = {"/ui/apply":"应用","/ui/planet":"天体"}
        updates8 = {"/ui/new":"新提示"}
        chinese7 = patch.merge_language(interim, legacy, updates7)
        chinese8 = patch.merge_language(latest, chinese7, updates8)
        legacy_sha, interim_sha, latest_sha = (patch.sha(blob) for blob in (legacy, chinese7, chinese8))
        hashes = {patch.LEGACY_BUILD:legacy_sha, patch.PLANETARIUM_BUILD:interim_sha, patch.BUILD:latest_sha}
        def load(path):
            return (updates7 if path.name == "game1257.zh-CN.json" else updates8).copy()
        with mock.object(patch,"OUTPUT_XML",hashes), mock.object(patch,"PLANETARIUM_XML",interim_sha), \
                mock.object(patch,"GENERATIONS",(legacy_sha,interim_sha,latest_sha)), \
                mock.object(patch,"legacy_text",return_value=legacy), mock.object(patch,"release_edits",side_effect=lambda raw:raw), \
                mock.object(patch,"read_json",side_effect=load):
            self.assertEqual(patch.render_text(legacy,patch.PLANETARIUM_BUILD,interim),chinese7)
            for source in (legacy,chinese7,chinese8):
                self.assertEqual(patch.render_text(source,patch.BUILD,latest),chinese8)
            self.assertEqual(audit.tree_layout(chinese8),audit.tree_layout(latest))
            with self.assertRaisesRegex(ValueError,"还原汉化"):
                patch.render_text(chinese8,patch.PLANETARIUM_BUILD,interim)

    def test_merge_uses_current_tree_indexed_leaves_and_new_attributes(self):
        old = b'<t><s><slot id="old">a</slot><slot>b</slot><obsolete>x</obsolete></s></t>'
        english = b'<t build="new"><s><slot id="new">A</slot><added>C</added><slot>B</slot></s></t>'
        edits = {"/s/added":"新增","/s/slot[1]":"第二项"}
        result = patch.merge_language(english, old, edits)
        self.assertEqual(audit.tree_layout(result), audit.tree_layout(english))
        self.assertEqual(audit.leaves(result), {
            "/s/slot[0]":("a",{"id":"new"}), "/s/added":("新增",{}), "/s/slot[1]":("第二项",{})})
        with self.assertRaisesRegex(ValueError, "缺少 1 个"):
            patch.merge_language(english, old, {})
        with self.assertRaisesRegex(ValueError, "不存在的键"):
            patch.merge_language(english, old, {**edits,"/s/obsolete":"x"})

    def test_current_and_legacy_languages_must_match_a_known_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / patch.RESOURCE
            asset.parent.mkdir()
            layouts = {tag:{"en":(off, len(buf), patch.sha(buf))} for tag, off, buf in
                       ((patch.BUILD, 4,b'new'), (patch.LEGACY_BUILD, 0,b'old'))}
            with mock.object(patch,'LANGUAGES',layouts):
                for tag, raw, english in ((patch.BUILD,b'xxxxnew',b'new'),
                                          (patch.LEGACY_BUILD,b'old',b'old')):
                    asset.write_bytes(raw)
                    self.assertEqual(patch.language_data(root), (tag,english))
                asset.write_bytes(b'xxxxNEW')
                with self.assertRaisesRegex(ValueError, "不支持"):
                    patch.language_data(root)

    def test_controller_markers_and_keyboard_keys(self):
        self.assertEqual(audit.FORMAT.findall("{pad:ls} / {0} / {pad:rclick} / {pad:ls}"),
                         ["{pad:ls}", "{0}", "{pad:rclick}", "{pad:ls}"])
        self.assertEqual(audit.missing_shortcuts('/ui/event_answers_eye_hint', '', '按 E 显示，空格键确认'), [])
        self.assertEqual(audit.missing_shortcuts('/ui/event_answers_eye_hint', '', 'SELECT，空格确认'), ['E'])

    def test_photo_attribution_preserves_community_credits_after_retry(self):
        photos = ['example by '+author+' (commons.wikimedia.org/wiki/File:test.jpg)' for author in
                  ('Retro Lenses, CC BY 4.0','Mikhail Semin, CC BY 4.0','Frank Kovalchek, CC BY 2.0')]
        source = '|'.join(['Original credit','','Planetarium art: examples',*photos,'','Font license'])
        old = '旧有鸣谢||本作使用Noto字体，许可如下||原许可'
        expected = '|'.join(['旧有鸣谢','','天象馆说明',*photos,'','本作使用Noto字体，许可如下','','原许可'])
        self.assertEqual(patch.planetarium_credits(source, old, '天象馆说明'), expected)
        self.assertEqual(patch.planetarium_credits(source, expected, '天象馆说明'), expected)
        with self.assertRaisesRegex(ValueError, '许可或链接'):
            patch.planetarium_credits(source.replace('CC BY 2.0','CC BY 4.0'), old, '天象馆说明')

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


@unittest.skipUnless(all(os.environ.get(k) for k in ("COLDWAR_TEST_GAME", "COLDWAR_TEST_BASE", "COLDWAR_OLD_PATCH",
                                                     "COLDWAR_TEST_OLD_FONT")),
                     "Requires a current game, Workshop base, released prior source and stock 26243566 font asset")
class RealUpgradeTests(unittest.TestCase):
    def test_older_release_offline_upgrade_after_steam_update_and_restore(self):
        game = Path(os.environ["COLDWAR_TEST_GAME"])
        workshop = Path(os.environ["COLDWAR_TEST_BASE"])
        old_patch = Path(os.environ["COLDWAR_OLD_PATCH"]) / "patch.py"
        spec = importlib.util.spec_from_file_location("previous_coldwar_patch", old_patch)
        previous = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(previous)
        font_spec = importlib.util.spec_from_file_location("previous_coldwar_font", old_patch.with_name("font_patch.py"))
        previous.font_patch = importlib.util.module_from_spec(font_spec)
        font_spec.loader.exec_module(previous.font_patch)
        self.assertIn(previous.RELEASE_XML, (patch.V1_2_XML, patch.V122_OUTPUT[patch.LEGACY_BUILD]))
        original = (game / font_patch.FILE).read_bytes()
        if patch.sha(original) == font_patch.PATCHED_SHA:
            backup = game_paths.user_data() / font_patch.CURRENT.backup
            original = backup.read_bytes()
        self.assertEqual(patch.sha(original), font_patch.ASSET_SHA)
        old_font = Path(os.environ["COLDWAR_TEST_OLD_FONT"]).read_bytes()
        self.assertEqual(patch.sha(old_font), previous.font_patch.ASSET_SHA)
        with tempfile.TemporaryDirectory() as name, ExitStack() as mocks:
            sandbox = Path(name)
            profile = sandbox / "player"
            game_copy = sandbox / "game"
            asset = game_copy / font_patch.FILE
            asset.parent.mkdir(parents=True)
            asset.write_bytes(old_font)
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
            self.assertEqual(patch.sha((folder / "text.xml").read_bytes()), previous.RELEASE_XML)
            first_backup = profile / ".zhcn-original-sharedassets0.assets"
            stamp = first_backup.stat().st_mtime_ns
            self.assertTrue(patch.has_local_base(profile))
            args.base = None
            rows = read_pref()[1] + [{"id": "another-player-mod", "isLoaded": True}]
            pref[0] = patch.encoded(rows)
            original_pref = pref[0]
            mocks.enter_context(mock.object(patch, "discover", side_effect=AssertionError("Workshop access")))
            # Steam replaces the game assets. The user profile, mod, receipt and original backup stay.
            asset.write_bytes(original)
            (game_copy / patch.RESOURCE).write_bytes((game / patch.RESOURCE).read_bytes())
            level = patch.RESOURCE.with_name("level3")
            (game_copy/level).write_bytes((game/level).read_bytes())
            managed = patch.runtime_ui.FILE.parent
            shutil.copytree(game/managed,game_copy/managed)
            # The local player might already have v1.2.3. Start the fixture from
            # the player's verified stock backup if that is the case.
            assembly = game_copy/patch.runtime_ui.FILE
            if patch.sha(assembly.read_bytes()) == patch.runtime_ui.ASSEMBLIES[patch.BUILD][1]:
                backup = game_paths.user_data()/(".zhcn-original-assembly-"+patch.BUILD+".dll")
                shutil.copyfile(backup,assembly)
            patch.display_layout.manage(game_copy,patch.BUILD,"restore")
            patch.run(args)
            args.action = "verify"
            patch.run(args)
            self.assertEqual(patch.sha((folder / "text.xml").read_bytes()), patch.RELEASE_XML)
            self.assertEqual(pref[0], original_pref)
            self.assertEqual(first_backup.stat().st_mtime_ns, stamp)
            updated = (folder / "text.xml").stat().st_mtime_ns
            args.action = "install"
            patch.run(args)
            self.assertEqual((folder / "text.xml").stat().st_mtime_ns, updated)
            args.action = "restore"
            patch.run(args)
            self.assertEqual(asset.read_bytes(), original)
            self.assertEqual(first_backup.read_bytes(),old_font)
            self.assertFalse((profile / font_patch.CURRENT.backup).exists())
            self.assertEqual(read_pref()[1], [rows[-1]])


if __name__=='__main__':
    unittest.main()
