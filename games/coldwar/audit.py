"""Read-only audit of the player's two Steam source languages and generated Chinese XML."""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
import io
import json
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import font_patch
import patch

HERE = Path(__file__).resolve().parent
FORMAT = re.compile(r"\{(?:\d+(?:,[^}:]+)?(?::[^}]+)?|pad:[a-z0-9_]+)\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"[+−-]?\d+(?:[.,]\d+)?(?:\s*[%％])?")
BAD = re.compile(r"вЂ|ï¿½|�|锟斤拷|Ã.|â€")
WIKI = {"positions_wiki", "char_wiki_links", "decision_wiki_links", "doctrine_wiki_links"}
# The format call in Decision13 supplies eight arguments. English strings 0/1
# are misplaced introductions. Slots 5/6 are the active relationship/social
# multipliers, including the reduced coefficient after Web research.
DECISION_ARGS = [
    [7], [0, 1, 5, 7], [0, 2, 5, 7], [0, 7, 7], [0, 5, 7], [0, 3, 5, 7],
    [0, 5, 7], [6, 7], [6, 7], [6, 7], [6, 7], [6, 7],
]
RUNTIME_FORMATS = {f"/decision_desc/decision12var{i}": Counter("{"+str(n)+"}" for n in nums)
                   for i, nums in enumerate(DECISION_ARGS)}
# Event74.StartEvent supplies the leader address in slot 0 on build 26891377.
# The Russian alternate description uses it; this English row omits it.
CURRENT_FORMATS = {**RUNTIME_FORMATS, "/events/events74Desc1": Counter(["{0}"])}


def leaves(blob):
    return {k:(node.text or "", node.attrib) for k,node in patch.leaf_nodes(ET.fromstring(blob)).items()}

def tree_layout(blob):
    return [(node.tag, sorted(node.attrib.items()), len(node)) for node in ET.fromstring(blob).iter()]

def sources(game):
    return [leaves(patch.language_data(game, language)[1]) for language in ("en", "ru")]


KEY_ALIASES = {
    "SPACE": ("Space", "空格"), "Backspace": ("Backspace", "退格"),
    "Tab": ("Tab", "制表"), "Select": ("Select", "选择键"),
    "+": ("+", "＋", "加号"), "–": ("-", "−", "–", "－", "减号"),
    ",": (",", "逗号"), ".": (".", "句号", "句点"),
}
KEY_ROWS = {"/hotkey/open_event": ("E",), "/ui/event_answers_eye_hint": ("E","SPACE"),
            "/ui/pad_cursor_hint": ("Select","A","X"), "/tutorial/part125": ("Ctrl","Shift"),
            "/tutorial/part125_pad": ("+","–")}

def missing_shortcuts(key, english, chinese):
    if key in ("/tutorial/part2", "/tutorial/part123"):
        keys = set(re.findall("“([^”]+)”", english))
    else:
        keys = KEY_ROWS.get(key, ())
    missing = []
    for label in keys:
        variants = KEY_ALIASES.get(label, (label,))
        if not any(re.search(r"(?<![a-zA-Z0-9])" + re.escape(v) + r"(?![a-zA-Z0-9])",
                             chinese, re.I) for v in variants):
            missing.append(label)
    return sorted(missing)


def number_tokens(text):
    result = NUMBER.findall(TAG.sub("", FORMAT.sub("", text)))
    return Counter(n.replace(",", ".").replace("−", "-").replace("％", "%").replace(" ", "") for n in result)


def glyph_test(asset, chinese):
    # The game's Unicode full-repertoire format-12 cmap is pinned by both font hashes.
    raw = asset.read_bytes()
    checksum = patch.sha(raw)
    if checksum == font_patch.asset_layout(checksum).original:
        raw = font_patch.build_assets(raw, (HERE / "font.bsdiff").read_bytes())
    font = font_patch.font_payload(raw, patched=True)
    patch.ensure(patch.sha(font) == font_patch.NEW_FONT_SHA, "字体内容校验失败。")
    tables, = struct.unpack_from(">H", font, 4)
    for i in range(tables):
        tag, _, offset, _ = struct.unpack_from(">4sIII", font, 12 + 16*i)
        if tag == b"cmap":
            break
    else:
        raise ValueError("找不到 Unicode 字形映射。")
    count, = struct.unpack_from(">H", font, offset+2)
    for i in range(count):
        platform, encoding, inner = struct.unpack_from(">HHI", font, offset+4+8*i)
        sub = offset + inner
        if (platform, encoding) == (3, 10) and struct.unpack_from(">H", font, sub)[0] == 12:
            break
    else:
        raise ValueError("字体全字符映射不匹配。")
    count, = struct.unpack_from(">I", font, sub+12)
    spans = [struct.unpack_from(">III", font, sub+16+12*i) for i in range(count)]
    ends = [span[1] for span in spans]
    chars = {ord(c) for text, _ in chinese.values() for c in text if c.isprintable()}
    missing = []
    for code in sorted(chars):
        i = bisect_left(ends, code)
        if i == count or code < spans[i][0] or spans[i][2] + code - spans[i][0] == 0:
            missing.append(f"U+{code:04X}")
    return {"printable_distinct": len(chars), "han_distinct":sum(0x3400<=c<=0x9FFF for c in chars),
            "missing":missing}


def semantic_review(path, keys, en, ru, zh, limit):
    # Optional. Use only local safetensors. No requests are made by this command.
    import torch
    import torch.nn.functional as functional
    import numpy as np
    from transformers import AutoModel, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModel.from_pretrained(path, local_files_only=True, use_safetensors=True).eval().to(device)
    if device == "cuda":
        model = model.half()
    def norm(s):
        return re.sub(r"\s+", " ", re.sub(r"[@|]|\{\d+[^}]*\}|<[^>]*>", " ", s)).strip() or "0"
    keys = [k for k in keys if k.split("/")[1] not in WIKI and en[k][0].strip() and zh[k][0].strip()
            and not en[k][0].startswith(("http:", "https:")) and any(c.isalpha() for c in en[k][0])]
    textsets = [[norm(data[k][0]) for k in keys] for data in (en, ru, zh)]
    vocab = sorted({s for texts in textsets for s in texts}, key=lambda s:(len(s), s))
    index = {s:i for i,s in enumerate(vocab)}
    all_vectors = []
    with torch.inference_mode():
        for i in range(0, len(vocab), 128):
            batch = tokenizer(vocab[i:i+128], padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
            result = model(**batch).last_hidden_state.float()
            mask = batch.attention_mask.unsqueeze(2)
            all_vectors.append(functional.normalize((result*mask).sum(1)/mask.sum(1), dim=1).cpu().numpy())
    vectors = np.concatenate(all_vectors)
    e, r, z = [vectors[[index[s] for s in texts]] for texts in textsets]
    groups = defaultdict(list)
    for i,k in enumerate(keys):
        groups[k.split("/")[1]].append(i)
    candidates = []
    for group in groups.values():
        similarity = z[group] @ ((e[group]+r[group])/2).T
        for j,i in enumerate(group):
            other = int(similarity[j].argmax())
            if other != j:
                candidates.append((float(similarity[j,other]-similarity[j,j]),keys[i],keys[group[other]]))
    return {"eligible":len(keys), "distinct_normalized":len(vocab), "top_other_keys": sorted(candidates, reverse=True)[:limit]}


def main(args):
    build, english = patch.language_data(args.game_dir)
    ru_build, russian = patch.language_data(args.game_dir, "ru")
    en, ru = leaves(english), leaves(russian)
    base = leaves((args.base / "text.xml").read_bytes())
    patch.ensure(build == ru_build and en.keys() == ru.keys(), "两份原版语言的构建或键集合不同。")
    expected = {patch.LEGACY_BUILD:(0,0,18133), patch.PLANETARIUM_BUILD:(1338,8,19463),
                patch.ECONOMY_BUILD:(1501,10,19624), patch.BUILD:(1508,10,19631)}[build]
    patch.ensure((len(en.keys()-base.keys()),len(base.keys()-en.keys()),len(en)) == expected,
                 "原版与工坊文本的新增、删除或现有项数不符。")
    if args.compare_xml:
        result = args.compare_xml.read_bytes()
    else:
        result = patch.render(args.base, build, english)["text.xml"]
    final = leaves(result)
    patch.ensure(en.keys() == final.keys(), "生成版键集合不同。")
    if build != patch.LEGACY_BUILD:
        patch.ensure(tree_layout(result) == tree_layout(english), "新英文原版与生成版节点顺序、属性或层次不同。")
    issues = defaultdict(list)
    duplicate = defaultdict(list)
    hints = defaultdict(list)
    rules = CURRENT_FORMATS if build != patch.LEGACY_BUILD else RUNTIME_FORMATS
    for k,(eng,attrs) in en.items():
        rus = ru[k][0]
        zh, zh_attrs = final[k]
        section = k.split("/")[1]
        if attrs != zh_attrs:issues["属性差异"].append(k)
        if BAD.search(zh):issues["乱码"].append(k)
        if section not in WIKI:
            if build != patch.LEGACY_BUILD and re.search(r"[{}]",FORMAT.sub("",zh)):
                issues["异常占位符"].append(k)
            expected = rules.get(k, Counter(FORMAT.findall(eng)))
            if Counter(FORMAT.findall(zh)) != expected:issues["格式参数差异"].append(k)
            if build != patch.LEGACY_BUILD and (missing := missing_shortcuts(k,eng,zh)):
                issues["实体按键缺失"].append((k,missing))
            if eng.strip() and not zh.strip():issues["空译文"].append(k)
            if re.search(r"[а-яёА-ЯЁ]{3,}", zh):hints["西里尔文残留"].append(k)
            if re.search(r"(?<![a-z])[A-Za-z]+ [a-z]+ [a-z]+",zh):hints["连续英文"].append(k)
            if eng.count("|") != zh.count("|"):hints["分段数不同"].append(k)
            if len(eng)>=100 and len(zh)<.16*len(eng) and len(rus)>.6*len(eng):hints["明显偏短"].append(k)
            if number_tokens(eng)==number_tokens(rus) and number_tokens(eng)!=number_tokens(zh):hints["数字字面量不同"].append(k)
            if len(eng)>40 and len(zh)>16:duplicate[(section,zh)].append(k)
        elif eng.strip() and not zh.strip():
            hints["有外文链接但中文留空"].append(k)
    distinct = [rows for rows in duplicate.values() if len({en[k][0] for k in rows})>1]
    def attributes(rows):
        return {(key, name): value for key, (_, attrs) in rows.items() for name, value in attrs.items()}
    base_attrs, target_attrs = attributes(base), attributes(en)
    report = {"Steam构建":build, "文本项":len(en), "分区":len({k.split('/')[1] for k in en}),
              "新增项":len(en.keys()-base.keys()), "移除项":len(base.keys()-en.keys()),
              "节点总数":len(tree_layout(result)), "叶属性总数":len(target_attrs),
              "新增叶属性":len(target_attrs.keys()-base_attrs.keys()),
              "移除叶属性":len(base_attrs.keys()-target_attrs.keys()),
              "原键属性值改变":sum(base_attrs[k]!=target_attrs[k] for k in base_attrs.keys() & target_attrs.keys()),
              "中文改动项":sum(k not in base or base[k][0]!=final[k][0] for k in en),
              "格式例外规则":len(rules),
              "中文百科链接":sum(final[k][0].startswith("https://zh.wikipedia.org/") for k in en),
              "候选":{k:len(v) for k,v in hints.items()},
              "同区长中文重复且英文不同的组":len(distinct), "错误":dict(issues)}
    if args.show:
        report["候选示例"]={k:v[:args.show] for k,v in hints.items()}
    if args.font:
        report["字体"] = glyph_test(args.game_dir/font_patch.FILE, final)
    if args.semantic_model:
        report["语义候选"] = semantic_review(args.semantic_model, en.keys(), en, ru, final, args.show or 20)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return bool(issues or (args.font and report["字体"]["missing"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True, help="Steam game folder")
    parser.add_argument("--base", type=Path, required=True, help="Workshop translation folder")
    parser.add_argument("--compare-xml", type=Path, help="audit an existing local text.xml instead of rendering the patch")
    parser.add_argument("--show", type=int, default=0, help="show up to this many candidate IDs per check")
    parser.add_argument("--font", action="store_true", help="check every printable code point against the rebuilt game font")
    parser.add_argument("--semantic-model", type=Path, help="optional local multilingual MiniLM model directory")
    try:
        sys.exit(main(parser.parse_args()))
    except (ValueError,OSError,KeyError,ImportError) as error:
        parser.exit(1, f"{error}\n")
