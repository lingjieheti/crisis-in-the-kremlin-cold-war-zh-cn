"""Build only the OFL font delta. Requires fonttools and bsdiff4."""
import argparse
from io import BytesIO
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import font_patch

DONOR = Path(__file__).resolve().parent / 'font-source/KremlinDonorSC-Regular.ttf'
DONOR_SHA = '5e0db897530eb471208c18ab3af96fe964a6c8887ebded8af95c10850b5d2b6f'

def build(base_font, donor_font, xml=None):
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    base = TTFont(base_font, recalcTimestamp=False)
    donor = TTFont(donor_font, recalcTimestamp=False)
    assert base['head'].unitsPerEm == donor['head'].unitsPerEm == 1000
    original_map = base.getBestCmap().copy()
    donor_map = donor.getBestCmap()
    if xml is None:
        targets = sorted(donor_map)
    else:
        root = ET.fromstring(xml.read_bytes())
        targets = sorted({ord(c) for node in root.iter() if not len(node) for c in (node.text or '') if '\u3400' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f' or '\uff01' <= c <= '\uff60' or (c.isprintable() and ord(c) not in original_map)})
    missing = [cp for cp in targets if cp not in donor_map]
    assert not missing, missing
    glyphs = donor.getGlyphSet()
    order = base.getGlyphOrder()[:]
    for cp in targets:
        src = donor_map[cp]
        dst = original_map.get(cp)
        if dst is None:
            dst = f'zhcn{cp:04X}'
            assert dst not in order
            order.append(dst)
            for table in base['cmap'].tables:
                if table.isUnicode() and table.format in {4, 12}:
                    table.cmap[cp] = dst
        record = DecomposingRecordingPen(glyphs)
        glyphs[src].draw(record)
        pen = TTGlyphPen(None)
        record.replay(pen)
        base['glyf'][dst] = pen.glyph()
        base['hmtx'].metrics[dst] = donor['hmtx'].metrics[src]
    base.setGlyphOrder(order)
    base['glyf'].glyphOrder = order
    for rec in base['name'].names:
        names = {1:'Kremlin UI SC', 2:'Regular', 3:'1.0;KremlinUISc-Regular', 4:'Kremlin UI SC Regular', 6:'KremlinUISc-Regular',16:'Kremlin UI SC',17:'Regular'}
        if rec.nameID in names:
            rec.string = names[rec.nameID].encode(rec.getEncoding())
    buffer = BytesIO()
    base.save(buffer)
    payload = buffer.getvalue()
    reread = TTFont(BytesIO(payload))
    assert set(original_map).union(targets) <= set(reread.getBestCmap())
    print(f'{len(targets)} glyphs, {len(set(targets)-set(original_map))} added. {len(payload)} bytes.')
    return payload

def rebuild(game):
    import bsdiff4
    asset = font_patch.asset_location(game)
    base = font_patch.font_payload(asset.read_bytes(), patched=False)
    font_patch.expect(font_patch.digest(DONOR.read_bytes()) == DONOR_SHA, '本项目的捐赠字形文件校验失败。')
    target = build(BytesIO(base), DONOR)
    font_patch.expect(font_patch.digest(target) == font_patch.NEW_FONT_SHA, '重建的字体指纹不符。')
    data = bsdiff4.diff(base, target)
    font_patch.expect(font_patch.digest(data) == font_patch.DELTA_SHA, '重建的差分指纹不符。')
    return data

if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--game-dir', type=Path, help='Steam game directory (auto-detected by default)')
    cli.add_argument('--output', type=Path, help='new path for the reproduced font.bsdiff')
    cli.add_argument('custom', type=Path, nargs='*', metavar='FILE',
                     help='optional custom build: base_font donor_font xml output')
    args = cli.parse_args()
    try:
        if args.custom:
            if len(args.custom) != 4 or args.game_dir or args.output:
                cli.error('自定义构建需要依次传入基础字体、捐赠字体、文本 XML 和输出路径。')
            original, donor, xml, output = args.custom
            import bsdiff4
            base = original.read_bytes()
            target = build(original, donor, xml)
            data = bsdiff4.diff(base, target)
            font_patch.expect(bsdiff4.patch(base, data) == target, '自定义字体差分校验失败。')
        else:
            if not args.output:
                cli.error('请用 --output 指定一个新文件。')
            output = args.output
            data = rebuild(args.game_dir)
        with output.open('xb') as stream:
            stream.write(data)
        print(font_patch.digest(data), output)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    except ImportError:
        sys.exit('字体维护工具需要 fonttools==4.62.1 和 bsdiff4==1.4.4。')
