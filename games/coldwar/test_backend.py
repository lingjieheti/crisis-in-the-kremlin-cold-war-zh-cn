"""Offline checks for Cold War's portable path discovery and font rebuild sources."""
from pathlib import Path
import hashlib
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


if __name__=='__main__':
    unittest.main()
