"""Regression checks for the resource-only release and verified original recovery."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock
import xml.etree.ElementTree as ET

import patch
import runtime_ui


class DisplayLabels(unittest.TestCase):
    def test_reviewed_semantics(self):
        edits = patch.read_json(patch.HERE/"review-1.2.3.zh-CN.json")
        for suffix in ("0","1"):
            value = edits["/achievement_conditions/a29_"+suffix]
            self.assertIn("年满80岁",value)
            self.assertNotIn("超过",value)
        for key in ("var0","var2"):
            body, quote = edits["/doctrine_variant_descs/"+key].split("|",1)
            self.assertTrue(body and quote.startswith("“"))
        self.assertIn("。|<color=",edits["/statistic_values_descs/HousingLevel"])
        for n,amount in enumerate(("2000万","2000万","5000万"),1):
            value = edits[f"/modif_desc/modif62var{n}"]
            self.assertIn(amount+"卢布",value)
            self.assertEqual(value.count("{0}"),int(n<3))
        crisis = edits["/events/events362Adds2"]
        self.assertIn("50%、33%和25%",crisis)
        self.assertIn("贸易封锁",crisis)
        for key in ("/events/events199Adds0","/events/events200Adds2"):
            self.assertIn("每月",edits[key])
        icon = edits["/custom_images/custom_images_notification"]
        for part in ("{0}","125 × 120","512 KB","PNG"):
            self.assertIn(part,icon)

    def test_removes_retired_marker_and_preserves_translated_content(self):
        source = b"<text><!--zhcn-coldwar-local:ui--><settings><name>EN</name><language>Language</language></settings></text>"
        with mock.object(patch, "read_json", side_effect=lambda p: {} if p.name.startswith("proofread") else {"/settings/name":"中文"}):
            result = patch.release_edits(source)
            self.assertEqual(patch.release_edits(result),result)
        self.assertNotIn(b"<!--",result)
        nodes = patch.leaf_nodes(ET.fromstring(result))
        self.assertEqual(nodes["/settings/language"].text,"语言（English 为中文）")
        self.assertEqual(nodes["/settings/name"].text,"中文")

    def test_sparse_corrections_are_authenticated_and_repeatable(self):
        before = "𠀀价格降到到50%，名称的的变化。"
        after = "𠀀价格降到50%，名称的变化。"
        change = {"source": patch.sha(before.encode()), "result": patch.sha(after.encode()),
                  "edits": [[before.index("到到"),"到",""],[before.index("的的"),"的",""]]}
        self.assertEqual(patch.proofread(before,change),after)
        self.assertEqual(patch.proofread(after,change),after)
        with self.assertRaisesRegex(ValueError,"原句不符"):
            patch.proofread("第三方译本",change)

    def test_refuses_unrecognized_assembly_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)/"game"
            assembly = game/runtime_ui.FILE
            assembly.parent.mkdir(parents=True)
            assembly.write_bytes(b"third-party modification")
            for action in ("preflight","install","verify","restore"):
                with self.assertRaisesRegex(ValueError,"构建不符"):
                    runtime_ui.manage(game,Path(temp),patch.BUILD,action)
            self.assertEqual(assembly.read_bytes(),b"third-party modification")

    def test_restores_only_known_previous_build_and_preserves_other_files(self):
        reference = b"official fixture"
        retired = b"released v1.2.3 fixture"
        checks = (patch.sha(reference), patch.sha(retired))
        for build in patch.V123_OUTPUT:
            with self.subTest(build=build), tempfile.TemporaryDirectory() as tmp, mock.dict(runtime_ui.ASSEMBLIES,{build:checks}), \
                    mock.dict(runtime_ui.SIGNATURES,{build:patch.sha(b"unaltered signature sentinel")}):
                profile = Path(tmp)
                game = profile/"game"
                path = game/runtime_ui.FILE
                path.parent.mkdir(parents=True)
                path.write_bytes(retired)
                backup = profile/(".zhcn-original-assembly-"+build+".dll")
                sig=game/runtime_ui.SIGNATURE
                sig.parent.mkdir(parents=True)
                sig.write_bytes(b"unaltered signature sentinel")
                for bad in (None,b"modified backup"):
                    if bad:backup.write_bytes(bad)
                    with self.assertRaisesRegex(ValueError,"Steam"):
                        runtime_ui.manage(game,profile,build,"install")
                    self.assertEqual(path.read_bytes(),retired)
                backup.write_bytes(reference)
                with self.assertRaisesRegex(ValueError,"install"):
                    runtime_ui.manage(game,profile,build,"verify")
                runtime_ui.manage(game,profile,build,"install")
                self.assertFalse(backup.exists())
                self.assertEqual(path.read_bytes(),reference)
                stamp=path.stat().st_mtime_ns
                for action in ("verify","install","restore"):
                    runtime_ui.manage(game,profile,build,action)
                self.assertEqual(path.stat().st_mtime_ns,stamp)
                self.assertEqual(sig.read_bytes(),b"unaltered signature sentinel")
                backup.write_bytes(b"unknown user backup")
                runtime_ui.manage(game,profile,build,"install")
                self.assertEqual(backup.read_bytes(),b"unknown user backup")

    def test_new_build_requires_both_official_files_and_writes_neither(self):
        build = patch.BUILD
        with tempfile.TemporaryDirectory() as tmp, mock.dict(runtime_ui.ASSEMBLIES,{build:(patch.sha(b"official"),None)}), \
                mock.dict(runtime_ui.SIGNATURES,{build:patch.sha(b"signature")}):
            profile = Path(tmp)
            assembly, signature = profile/runtime_ui.FILE, profile/runtime_ui.SIGNATURE
            for file,value in ((assembly,b"official"),(signature,b"unexpected")):
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(value)
            for action in ("preflight","install","verify","restore"):
                with self.assertRaisesRegex(ValueError,"签名"):
                    runtime_ui.manage(profile,profile,build,action)
            self.assertEqual(signature.read_bytes(),b"unexpected")
            signature.write_bytes(b"signature")
            times = [p.stat().st_mtime_ns for p in (assembly,signature)]
            for action in ("install","verify","restore"):
                runtime_ui.manage(profile,profile,build,action)
            self.assertEqual(times,[p.stat().st_mtime_ns for p in (assembly,signature)])

if __name__ == "__main__":
    unittest.main()
