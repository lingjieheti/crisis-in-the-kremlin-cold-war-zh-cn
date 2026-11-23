"""Build only the OFL font delta. Requires fonttools and bsdiff4."""
import argparse
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import bsdiff4
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

def build(base_font, donor_font, xml):
    base = TTFont(base_font, recalcTimestamp=False)
    donor = TTFont(donor_font, recalcTimestamp=False)
    assert base['head'].unitsPerEm == donor['head'].unitsPerEm == 1000
    original_map = base.getBestCmap().copy()
    donor_map = donor.getBestCmap()
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

if __name__ == '__main__':
    cli=argparse.ArgumentParser()
    for name in ['base_font','donor_font','xml','output']:
        cli.add_argument(name,type=Path)
    args=cli.parse_args()
    out=build(args.base_font,args.donor_font,args.xml)
    delta=bsdiff4.diff(args.base_font.read_bytes(),out)
    assert bsdiff4.patch(args.base_font.read_bytes(),delta)==out
    args.output.write_bytes(delta)
