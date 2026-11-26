"""Tests for the renderer's opt-in marker, input hints and the reviewed numeric thresholds."""
from pathlib import Path
import os
import subprocess
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

    def test_marker_preserves_game_nodes_and_is_idempotent(self):
        source = b"<text>\n <settings><name>EN</name></settings>\n</text>"
        with mock.object(patch,"read_json",side_effect=lambda p: {} if p.name.startswith("proofread") else {"/settings/name":"中文"}):
            marked = patch.release_edits(source)
            self.assertEqual(patch.release_edits(marked),marked)
        self.assertEqual(marked.count(b"<!--zhcn-coldwar-local:ui-->"),1)
        self.assertEqual(list(patch.leaf_nodes(ET.fromstring(marked))),["/settings/name"])

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

    @unittest.skipUnless(os.name=="nt","Windows .NET Framework")
    def test_native_interaction_formatting_and_xml_opt_in(self):
        program = r'''using System;
using System.Xml.Linq;
class Fixture {
    static void Check(bool v) { if (!v) throw new Exception("Unexpected label"); }
    static void Main() {
        Check(!LabelText.IsOurDocument(null));
        Check(!LabelText.IsOurDocument(XDocument.Parse("<r><a/></r>")));
        Check(!LabelText.IsOurDocument(XDocument.Parse("<r><!--other--><a/></r>")));
        Check(LabelText.IsOurDocument(XDocument.Parse("<r>\n <!--zhcn-coldwar-local:ui--><a/></r>",LoadOptions.SetLineInfo)));
        const string marker = "<?xml version='1.0'?><Root><!--zhcn-coldwar-local:ui--><system/></Root>";
        Check(LabelText.IsOurSource("zhcn-coldwar-local",marker));
        Check(!LabelText.IsOurSource("another-translation",marker));
        Check(!LabelText.IsOurSource("zhcn-coldwar-local","<Root><system/></Root>"));
        Check(LabelText.LanguageRow("Язык","ru",true).Contains("после выхода из настроек"));
        Check(LabelText.LanguageRow("语言","en",true).Contains("关闭设置后生效"));
        Check(LabelText.LanguageRow("语言","en",false)=="语言");
        Check(LabelText.LanguageRow("Langue","fr",true)==null);
        Check(LabelText.Bindings("Press O", "O") == "按 O");
        Check(LabelText.Bindings("Press R", "R") == "按 R");
        Check(LabelText.Bindings("Press A | Hold R1", "A | R1") == "按 A | 长按 R1");
        Check(LabelText.Bindings("Tap X | O", "X | O") == "轻按 X | O");
        Check(LabelText.Bindings("Press Press key", "Press key") == "按 Press key");
        Check(LabelText.Bindings("Debug Press key", "Debug Press key") == "Debug Press key");
        Check(LabelText.Bindings("Custom Trigger A", "A") == "Custom Trigger A");
        Check(LabelText.Bindings("Press O | X", "Q") == "Press O | X");
        XDocument notices = XDocument.Parse("<r><!--zhcn-coldwar-local:ui--><system><error_occured>发送日志</error_occured><open_log_file>打开日志</open_log_file><OK>确定</OK><steam_error>同步失败</steam_error><steam_error_no_pipe>无法连接</steam_error_no_pipe></system></r>");
        string raw = "[Steam] SteamAPI init failed after 5x2 attempts. Result: k_ESteamAPIInitResult_FailedGeneric. Message: No appID found. IsSteamRunning: True.";
        string rendered = LabelText.SteamBody("original notice\n"+raw,notices);
        Check(rendered.Contains("未取得游戏的应用编号") && rendered.Contains(raw));
        Check(LabelText.SteamBody("ordinary game notice",notices) == null);
        Check(LabelText.SteamBody("Steam synchronization failed.\n\nCause: no connection to it could be established.",notices) == "同步失败\n\n无法连接");
        Check(LabelText.SteamButton("Open log file",notices) == "打开日志");
        Check(LabelText.SteamButton("Unrelated action",notices) == null);
    }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            source = temp/"Fixture.cs"
            source.write_text(program,encoding="utf-8-sig")
            csc = Path(os.environ["WINDIR"])/"Microsoft.NET/Framework64/v4.0.30319/csc.exe"
            executable = temp/"Fixture.exe"
            subprocess.run([csc,"/nologo","/optimize+","/codepage:65001","/r:System.Xml.Linq.dll",
                            "/out:"+str(executable),source,runtime_ui.HERE/"LabelText.cs"],check=True)
            subprocess.run([executable],check=True)


if __name__=="__main__":
    unittest.main()
