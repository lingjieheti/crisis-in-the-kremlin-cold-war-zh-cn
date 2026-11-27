"""Steam may update the scene assets before a player updates the mod."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import font_patch as font
import display_layout


class FontMigration(unittest.TestCase):
    def test_resolution_layout_defaults_and_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scene = root / display_layout.FILE
            scene.parent.mkdir()
            scene.write_bytes(b"unrecognized scene")
            for action in ('preflight', 'install', 'verify', 'restore'):
                display_layout.manage(root, '26243566', action)
                with self.assertRaises(ValueError):
                    display_layout.manage(root, '26955082', action)
            self.assertEqual(scene.read_bytes(), b"unrecognized scene")

    def check_real_display_settings(self, game, build):
        raw = (Path(game) / display_layout.FILE).read_bytes()
        _, original, localized = display_layout.SCENES[build]
        self.assertIn(font.digest(raw), (original, localized))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scene = root / display_layout.FILE
            scene.parent.mkdir()
            scene.write_bytes(raw)
            display_layout.manage(root, build, 'restore')
            stock = scene.read_bytes()
            with self.assertRaises(ValueError):
                display_layout.manage(root, build, 'verify')
            display_layout.manage(root, build, 'preflight')
            self.assertEqual(scene.read_bytes(), stock)
            display_layout.manage(root, build, 'install')
            changed = scene.read_bytes()
            self.assertEqual(len(changed), len(stock))
            self.assertEqual(sum(a != b for a, b in zip(stock, changed)), 8)
            display_layout.manage(root, build, 'verify')
            display_layout.manage(root, build, 'install')
            display_layout.manage(root, build, 'restore')
            self.assertEqual(scene.read_bytes(), stock)

    @unittest.skipUnless(os.environ.get('COLDWAR_TEST_GAME'), 'set COLDWAR_TEST_GAME to the newest Steam copy')
    def test_new_resolution_selector(self):
        self.check_real_display_settings(os.environ['COLDWAR_TEST_GAME'], '26977018')

    @unittest.skipUnless(os.environ.get('COLDWAR_TEST_INTERIM_GAME'), 'set COLDWAR_TEST_INTERIM_GAME to the intermediate Steam copy')
    def test_intermediate_resolution_selector(self):
        self.check_real_display_settings(os.environ['COLDWAR_TEST_INTERIM_GAME'], '26891377')

    @unittest.skipUnless(os.environ.get('COLDWAR_TEST_INTERIM_FONT'), 'set COLDWAR_TEST_INTERIM_FONT to the 26891377 Steam original')
    def test_intermediate_depot_font(self):
        raw = Path(os.environ['COLDWAR_TEST_INTERIM_FONT']).read_bytes()
        self.assertEqual(font.digest(raw), font.INTERIM.original)
        rebuilt = font.build_assets(raw, Path(font.__file__).with_name('font.bsdiff').read_bytes())
        self.assertEqual(font.digest(rebuilt), font.INTERIM.patched)
        self.assertEqual(font.digest(font.font_payload(rebuilt)), font.NEW_FONT_SHA)
    def test_builds_use_separate_backups(self):
        old_bytes, old_patch = b'first official depot', b'first localized depot'
        new_bytes, new_patch = b'second official depot', b'second localized depot'
        previous = font.PREVIOUS._replace(original=font.digest(old_bytes), patched=font.digest(old_patch))
        current = font.CURRENT._replace(original=font.digest(new_bytes), patched=font.digest(new_patch))
        with tempfile.TemporaryDirectory() as tmp, patch.object(font, 'PREVIOUS', previous), \
                patch.object(font, 'CURRENT', current), \
                patch.object(font, 'build_assets', side_effect=lambda data, delta: {old_bytes:old_patch, new_bytes:new_patch}[data]):
            root = Path(tmp)
            live = root / 'sharedassets0.assets'
            live.write_bytes(old_bytes)
            font.manage(live, root, 'install')
            first = (root / previous.backup).stat().st_mtime_ns
            live.write_bytes(new_bytes)  # the Steam update
            font.manage(live, root, 'preflight')
            self.assertFalse((root / current.backup).exists())
            font.manage(live, root, 'install')
            second = (root / current.backup).stat().st_mtime_ns
            self.assertEqual(live.read_bytes(), new_patch)
            font.manage(live, root, 'verify')
            font.manage(live, root, 'install')
            self.assertEqual((root / current.backup).stat().st_mtime_ns, second)
            self.assertEqual((root / previous.backup).stat().st_mtime_ns, first)
            font.manage(live, root, 'restore')
            self.assertEqual(live.read_bytes(), new_bytes)
            self.assertFalse((root / current.backup).exists())
            self.assertEqual((root / previous.backup).read_bytes(), old_bytes)

    def test_unknown_version_never_overwrites_a_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset = root / 'sharedassets0.assets'
            asset.write_bytes(b'unknown')
            backup = root / font.CURRENT.backup
            backup.write_bytes(b'existing backup')
            for action in ('install', 'verify', 'restore'):
                with self.assertRaises(ValueError):
                    font.manage(asset, root, action)
                self.assertEqual(asset.read_bytes(), b'unknown')
                self.assertEqual(backup.read_bytes(), b'existing backup')

    @unittest.skipUnless(os.environ.get('COLDWAR_TEST_GAME'), 'set COLDWAR_TEST_GAME to read a real Steam copy')
    def test_new_depot_font_round_trip(self):
        asset = Path(os.environ['COLDWAR_TEST_GAME']) / font.FILE
        data = asset.read_bytes()
        if font.digest(data) == font.PATCHED_SHA:
            import game_paths
            data = (game_paths.user_data() / font.CURRENT.backup).read_bytes()
        self.assertEqual(font.digest(data), font.ASSET_SHA)
        delta = Path(font.__file__).with_name('font.bsdiff').read_bytes()
        built = font.build_assets(data, delta)
        self.assertEqual(font.digest(built), font.PATCHED_SHA)
        self.assertEqual(font.font_payload(built, patched=False), font.font_payload(data, patched=False))
        self.assertEqual(font.digest(font.font_payload(built)), font.NEW_FONT_SHA)

    @unittest.skipUnless(os.environ.get('COLDWAR_TEST_GAME') and os.environ.get('COLDWAR_TEST_OLD_FONT'),
                         'set COLDWAR_TEST_OLD_FONT to the verified 26243566 Steam asset')
    def test_two_real_depots_restore_their_own_original(self):
        new = (Path(os.environ['COLDWAR_TEST_GAME']) / font.FILE).read_bytes()
        if font.digest(new) == font.CURRENT.patched:
            import game_paths
            new = (game_paths.user_data() / font.CURRENT.backup).read_bytes()
        old = Path(os.environ['COLDWAR_TEST_OLD_FONT']).read_bytes()
        self.assertEqual(font.digest(old), font.PREVIOUS.original)
        self.assertEqual(font.digest(new), font.CURRENT.original)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset = root / 'sharedassets0.assets'
            asset.write_bytes(old)
            font.manage(asset, root, 'install')
            self.assertEqual(font.digest(asset.read_bytes()), font.PREVIOUS.patched)
            font.manage(asset, root, 'verify')
            asset.write_bytes(new)
            font.manage(asset, root, 'install')
            self.assertEqual(font.digest(asset.read_bytes()), font.CURRENT.patched)
            font.manage(asset, root, 'verify')
            font.manage(asset, root, 'restore')
            self.assertEqual(asset.read_bytes(), new)
            self.assertEqual((root / font.PREVIOUS.backup).read_bytes(), old)


if __name__ == '__main__':
    unittest.main()
