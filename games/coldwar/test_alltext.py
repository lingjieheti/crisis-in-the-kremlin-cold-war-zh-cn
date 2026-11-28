"""Resource-only localization and round-trip checks without Steam or a controller."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch as mock

import controller_text as controller
import patch


class ReferenceTests(unittest.TestCase):
    def test_distributable_tables(self):
        reviews = patch.read_json(patch.HERE / "proofread-1.2.6.json")
        self.assertIn("/modif_desc/modif25var5", reviews)
        self.assertIn("/events/events368Desc", reviews)
        self.assertIn("/ruler_polls/change", reviews)
        for key, change in reviews.items():
            self.assertRegex(key, r"^/\w+/\w+$")
            self.assertRegex(change["source"], r"^[0-9a-f]{64}$")
            self.assertRegex(change["result"], r"^[0-9a-f]{64}$")
            self.assertNotEqual(change["source"], change["result"])
            last_end = 0
            for offset, before, after in change["edits"]:
                self.assertGreaterEqual(offset, last_end)
                self.assertNotEqual(before, after)
                last_end = offset + len(before)
        profiles = patch.read_json(patch.HERE / "controller-profiles.json")
        self.assertIn("steam_input_manifest.vdf", profiles)
        self.assertEqual(len(profiles), 9)
        for original, localized in profiles.values():
            self.assertNotEqual(original, localized)
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", h) for h in (original, localized)))

    def test_fallback_only_fills_empty_encyclopedia_fields(self):
        previous = '''<r><char_wiki_links><one/><two>https://zh.wikipedia.org/wiki/Test</two>
        <blank/></char_wiki_links><events><news>消息</news></events></r>'''.encode()
        english = b"""<r><char_wiki_links><one>https://en.wikipedia.org/wiki/One</one>
        <two>https://en.wikipedia.org/wiki/Two</two><blank/></char_wiki_links>
        <events><news>https://example.org</news></events></r>"""
        with mock.object(patch, "read_json", return_value={}):
            result = patch.review_current(previous, english)
            self.assertEqual(result, patch.review_current(result, english))
            self.assertIn(b"https://en.wikipedia.org/wiki/One", result)
            self.assertIn(b"https://zh.wikipedia.org/wiki/Test", result)
            self.assertNotIn(b"https://example.org", result)
            self.assertIn("<news>消息</news>".encode(), result)
            self.assertIn(b"<blank />", result)


class ControllerTests(unittest.TestCase):
    def test_preserves_mappings_and_custom_edits(self):
        names = ["controller_neptune.vdf", "controller_ps5.vdf", "controller_xboxone.vdf"]
        original = (b'"controller_mappings"\r\n{\r\n\t"localization"\r\n\t{\r\n'
                    b'\t\t"english"\r\n\t\t{\r\n\t\t\t"title" "Test"\r\n'
                    b'\t\t\t"description" "Description"\r\n\t\t\t"quicksave" "Save"\r\n\t\t}\r\n'
                    b'\t\t"russian"\r\n\t\t{\r\n\t\t\t"title" "Test"\r\n\t\t}\r\n\t}\r\n'
                    b'\t"binding" "xinput_button a, #quicksave"\r\n}\r\n')
        sha = lambda data: hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            folder = game / "steam_input"
            folder.mkdir()
            records = {}
            targets = {}
            for name in names:
                block = controller.block(name, original)
                result = original.replace(controller.ANCHOR, block + controller.ANCHOR)
                self.assertEqual(result.replace(block, b""), original)
                self.assertIn("按住快速存档".encode() if "neptune" in name else "快速存档".encode(), block)
                self.assertEqual("触控板移动光标".encode() in block, "xbox" not in name)
                records[name] = (sha(original), sha(result))
                targets[name] = result
                (folder / name).write_bytes(original)
            (game / "controller-profiles.json").write_text(json.dumps(records), "utf8")
            with mock.object(controller, "HERE", game):
                for action in ("preflight", "install", "install", "verify"):
                    controller.manage(game, patch.BUILD, action)
                self.assertEqual({n:(folder/n).read_bytes() for n in names}, targets)
                custom = targets[names[-1]] + b"\r\n// custom binding"
                (folder/names[-1]).write_bytes(custom)
                controller.manage(game, patch.BUILD, "restore")
                self.assertEqual((folder/names[-1]).read_bytes(), custom)
                self.assertEqual((folder/names[0]).read_bytes(), original)
                with self.assertRaisesRegex(ValueError, "重新安装"):
                    controller.manage(game, patch.BUILD, "verify")


if __name__ == "__main__":
    unittest.main()
