"""Check the published Chinese encyclopedia destinations with the MediaWiki Action API."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit
import patch

def titles_for(en, ru, base):
    result = {}
    for k, (eng, _) in en.items():
        if k.split("/")[1] not in audit.WIKI:
            continue
        urls = [urlsplit(s) for s in (base[k][0], eng, ru[k][0])]
        if urls[0].netloc and not urls[0].netloc.endswith("wikipedia.org"):
            continue
        seeds = []
        for url in urls:
            if url.netloc in {"en.wikipedia.org", "ru.wikipedia.org"} and url.path.startswith("/wiki/") and not url.fragment:
                seed = (url.netloc[:2], unquote(url.path[6:]).replace("_"," "))
                if seed not in seeds:
                    seeds.append(seed)
        if seeds:
            result[k] = seeds
    return result

def query(lang, batch):
    params = {"action":"query","format":"json","prop":"langlinks|pageprops","redirects":1,"lllang":"zh",
              "lllimit":"max","ppprop":"wikibase_item","titles":"|".join(batch)}
    url = f"https://{lang}.wikipedia.org/w/api.php?"+urlencode(params)
    request = Request(url, headers={"User-Agent":"Nostalgames-localization/1.1 (Steam game encyclopedia link verification)"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)["query"]
        except HTTPError as error:
            if error.code not in (429,502,503,504) or attempt==3:
                raise
            delay = error.headers.get("Retry-After", "")
            time.sleep(max(60, int(delay)) if delay.isdigit() else 60)
        except (TimeoutError, URLError):
            if attempt==3:
                raise
            time.sleep(3*(attempt+1))

def destinations(seeds):
    resolved = {}
    for lang in ("en","ru"):
        titles = sorted({title for seq in seeds.values() for language,title in seq if language==lang})
        for i in range(0,len(titles),40):
            batch = titles[i:i+40]
            data = query(lang,batch)
            redirects = {r["from"]:r["to"] for r in data.get("normalized",[])+data.get("redirects",[])}
            pages = {p["title"]:p for p in data["pages"].values()}
            for title in batch:
                current = title
                visited = set()
                while current in redirects and current not in visited:
                    visited.add(current)
                    current = redirects[current]
                p = pages.get(current,{})
                resolved[lang,title] = (p.get("pageprops",{}).get("wikibase_item"),
                    next((item["*"] for item in p.get("langlinks",[]) if item["lang"]=="zh"),None))
            time.sleep(3)
    out = {}
    conflict = []
    for k, seq in seeds.items():
        vals = [resolved[t] for t in seq]
        ids = {qid for qid,_ in vals if qid}
        names = {name for _,name in vals if name}
        if len(ids)>1 or len(names)>1:
            conflict.append(k)
        elif len(names)==1:
            out[k] = "https://zh.wikipedia.org/wiki/"+quote(names.pop().replace(" ","_"),safe="_()-")
    return out, conflict

def main(args):
    en,ru = audit.sources(args.game_dir)
    base = audit.leaves((args.base/"text.xml").read_bytes())
    seeds = titles_for(en,ru,base)
    found,conflicts = destinations(seeds)
    current = patch.read_json(audit.HERE/"wiki_zh.json")
    changed = {k:found.get(k) for k,url in current.items() if found.get(k)!=url}
    new = sorted(found.keys()-current.keys())
    print(json.dumps({"候选键":len(seeds),"目前可匹配中文页":len(found),"多语身份冲突":len(conflicts),
                      "已收录地址发生变化":changed,"新匹配":new},ensure_ascii=False,indent=2))
    return bool(changed)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir",type=Path,required=True)
    parser.add_argument("--base",type=Path,required=True)
    try:
        sys.exit(main(parser.parse_args()))
    except (OSError,ValueError,KeyError) as error:
        parser.exit(1,f"{error}\n")
