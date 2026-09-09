import re
import time
import html
import requests
import unicodedata
import pandas as pd
from tqdm import tqdm


def s(x): return "" if x is None else str(x)


def get(url, params=None, polite_sleep=0.05):
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    if polite_sleep:
        time.sleep(polite_sleep)
    return r.json()


def iter_pages(url, params=None):
    data = get(url, params=params)
    if isinstance(data, dict) and "results" in data:
        while True:
            for item in data.get("results", []):
                yield item
            nxt = data.get("next")
            if not nxt:
                break
            data = get(nxt)
    elif isinstance(data, list):
        yield from data
    else:
        raise ValueError(f"Unexpected paging shape for {url}")


def uniq_join(vals, sep="; "):
    return sep.join(sorted({str(v).strip() for v in vals if v is not None and str(v).strip()}))


def fold_text(s: str) -> str:
    """
    Diacritic/ligature insensitive, case-insensitive comparison string.
    Å -> A, æ -> ae, etc.
    """
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.casefold().strip()


def norm_key(s: str, drop_hyphens: bool = False) -> str:
    """
    Normalise for matching
    """
    s = fold_text(s).replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9\-\(\)]+", "", s)
    if drop_hyphens:
        s = s.replace("-", "")
    return s


def is_ima_species(rec: dict) -> bool:
    """
    Heuristic to avoid group/subgroup/variety records.
      - entrytype: "entry type & 1 in query are all the IMA minerals"
      - ima_notes can contain "IMA Approved Group Name" (exclude)
      - varietyof present -> variety (exclude)
    """
    try:
        et = rec.get("entrytype", None)
        if et is not None and int(et) != 1:
            return False
    except Exception:
        pass

    if rec.get("varietyof"):
        return False

    notes = (rec.get("ima_notes") or "").upper()
    if "GROUP NAME" in notes:
        return False

    status = (rec.get("ima_status") or "")
    return ("APPROVED" in status) or ("GRANDFATHERED" in status)


def fetch_geomaterials_brief_by_ids(ids):
    """
    Fetch brief geomaterial records for given IDs into _GM_BRIEF_CACHE.
    """
    ids = [int(i) for i in ids if i is not None]
    missing = [i for i in ids if i not in GM_BRIEF_CACHE]
    if not missing:
        return

    BATCH = 200
    id_param = "id_in"

    if BASE.endswith("/v1"):
        endpoint = "/geomaterials/"
    else:
        endpoint = "/v1/geomaterials/"

    for i in range(0, len(missing), BATCH):
        batch = ",".join(map(str, missing[i:i + BATCH]))
        params = {
            id_param: batch,
            "fields": GM_BRIEF_FIELDS,
            "format": "json",
            "page-size": 1000,
        }
        for rec in iter_pages(BASE + endpoint, params=params):
            GM_BRIEF_CACHE[int(rec["id"])] = rec


def canonical_geomaterial_id(gid: int, max_hops: int = 5):
    """
    Follow synid and varietyof chains to reach the canonical record.
    """
    if gid is None:
        return None, None

    gid = int(gid)
    fetch_geomaterials_brief_by_ids([gid])

    visited = set()
    hops = 0
    while hops < max_hops and gid not in visited:
        visited.add(gid)
        rec = GM_BRIEF_CACHE.get(gid, {})

        # synid means "this record is a synonym of synid"
        nxt = rec.get("synid") or rec.get("varietyof")
        if nxt:
            gid = int(nxt)
            fetch_geomaterials_brief_by_ids([gid])
            hops += 1
            continue
        break

    rec = GM_BRIEF_CACHE.get(gid, {})
    return gid, (rec.get("name") or "")


def name_to_geomaterial(name: str):
    q = (name or "").strip()
    if not q:
        return (None, None, "blank")

    if BASE.endswith("/v1"):
        path = "/geomaterials-search/"
    else:
        path = "/v1/geomaterials-search/"

    try:
        hits = get(BASE + path, params={"q": q, "format": "json"})
    except requests.HTTPError:
        return None, None, "search_endpoint_not_found"

    if not hits:
        return None, None, "not_found"

    hit_ids = []
    for h in hits:
        if h.get("id") is not None:
            hit_ids.append(int(h["id"]))
    fetch_geomaterials_brief_by_ids(hit_ids)

    q_fold = fold_text(q)
    q_key = norm_key(q, drop_hyphens=True)

    scored = []
    for h in hits:
        hid = h.get("id")
        hname = h.get("name") or ""
        if hid is None or not hname:
            continue
        hid = int(hid)

        # resolves synonym records to the real species
        cid, cname = canonical_geomaterial_id(hid)

        # Use the HIT name to decide how well the query matched what search returned,
        hn_fold = fold_text(hname)
        hn_key = norm_key(hname, drop_hyphens=True)

        if hname == q:
            score, mt = 100, "exact_name"
        elif hn_fold == q_fold:
            score, mt = 95, "diacritic_insensitive"
        elif hn_key == q_key:
            score, mt = 90, "hyphen_insensitive"
        else:
            score, mt = 10, "fallback"

        # Prefer canonical records that look like IMA species
        crec = GM_BRIEF_CACHE.get(cid, {})
        if is_ima_species(crec):
            score += 10
        else:
            score -= 10

        scored.append((score, mt, cid, cname, hid, hname))

    scored.sort(reverse=True, key=lambda x: x[0])
    best = scored[0]
    best_score, mt, cid, cname, hid, hname = best
    return cid, cname, mt


def fetch_geomaterials_by_ids(ids):
    ids = [str(int(i)) for i in ids if i is not None]
    if not ids:
        return {}

    out = {}
    BATCH = 200
    id_param = "id_in"

    if BASE.endswith("/v1"):
        endpoint = "/geomaterials/"
    else:
        endpoint = "/v1/geomaterials/"

    with tqdm(total=len(ids)) as pbar:
        for i in range(0, len(ids), BATCH):
            batch = ",".join(ids[i:i + BATCH])
            params = {
                id_param: batch,
                "fields": GEOMATERIAL_FIELDS,
                "format": "json",
                "page-size": 1000,
            }
            for rec in iter_pages(BASE + endpoint, params=params):
                out[int(rec["id"])] = rec

            # advance by the number we *attempted* in this batch (stable progress even if one fails to return)
            pbar.update(len(ids[i:i + BATCH]))

    return out


def prefer_formula(g):
    ima = (g.get("ima_formula") or "").strip()
    return ima if ima else (g.get("mindat_formula") or "").strip()


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s)


def mindat_formula_to_unicode(raw: str, keep_box: bool = True):
    """
        Converts Mindat HTML-ish formula strings to a more readable Unicode form.
        """
    if not raw:
        return ""
    s = html.unescape(str(raw))

    # Convert sub/sup blocks first
    def sub_repl(m):
        inner = strip_tags(m.group(1))
        return inner.translate(_SUB_MAP)

    def sup_repl(m):
        inner = strip_tags(m.group(1))
        return inner.translate(_SUP_MAP)

    s = re.sub(r"<sub>(.*?)</sub>", sub_repl, s, flags=re.IGNORECASE)
    s = re.sub(r"<sup>(.*?)</sup>", sup_repl, s, flags=re.IGNORECASE)

    s = strip_tags(s)

    if not keep_box:
        s = s.replace(BOX_UNICODE, "")

    # tidy whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def mindat_formula_to_ascii(raw: str, box_ascii: str, keep_box: bool = True):
    """
    ASCII-ish rendering
    """
    if not raw:
        return ""
    s = html.unescape(str(raw))

    def sub_repl(m):
        inner = strip_tags(m.group(1)).strip()
        return f"_{inner}" if inner else ""

    def sup_repl(m):
        inner = strip_tags(m.group(1)).strip()
        return f"^{inner}" if inner else ""

    s = re.sub(r"<sub>(.*?)</sub>", sub_repl, s, flags=re.IGNORECASE)
    s = re.sub(r"<sup>(.*?)</sup>", sup_repl, s, flags=re.IGNORECASE)

    s = strip_tags(s)

    if keep_box:
        s = s.replace(BOX_UNICODE, box_ascii)
    else:
        s = s.replace(BOX_UNICODE, "")

    # replace any remaining non-ascii chars
    s = s.replace("–", "-").replace("—", "-")

    s = re.sub(r"\s+", " ", s).strip()
    return s


def main(input_csv):
    df_in = pd.read_csv(input_csv, header=None, sep=",")
    mineral_col = df_in.columns[0]

    input_names = [str(x).strip() for x in df_in[mineral_col].tolist()]
    input_names = [x for x in input_names if x]

    # Step 1 - resolve names
    resolved = []
    print("Resolving mineral names via geomaterials-search...")
    for nm in tqdm(input_names):
        gid, rname, how = name_to_geomaterial(nm)
        resolved.append({"input_name": nm, "mindat_id": gid, "resolved_name": rname, "match_type": how})
    df_res = pd.DataFrame(resolved)
    ids = sorted({int(x) for x in df_res["mindat_id"].dropna().tolist()})
    print(f"Resolved IDs: {len(ids)} / {len(df_res)}")

    # Step 2 - Fetch geomaterial info
    print("Fetching geomaterial details...")
    gmap = fetch_geomaterials_by_ids(ids)

    # Step 3 - Make table
    out_rows = []
    for _, rr in df_res.iterrows():
        mid = rr["mindat_id"]

        if pd.isna(mid):
            out_rows.append({
                "input_name": rr["input_name"],
                "mindat_id": "",
                "mindat_name": "",
                "match": "",
                "ima_status": "",
                "formula_preferred": "",
                "strunz10": "",
                "dana8": "",
            })
            continue

        mid = int(mid)
        g = gmap.get(mid, {})
        raw_formula = prefer_formula(g)

        out_rows.append({
            "input_name": rr["input_name"],
            "mindat_id": mid,
            "mindat_name": g.get("name") or rr.get("resolved_name") or "",
            "match": rr["match_type"],
            "ima_status": [x for x in g.get("ima_status") if x != "GRANDFATHERED"] or "",
            "formula_unicode": mindat_formula_to_unicode(raw_formula, keep_box=True),
            "formula_ascii": mindat_formula_to_ascii(raw_formula, keep_box=True, box_ascii="[]"),
            "strunz10": f"{s(g.get('strunz10ed1'))}.{s(g.get('strunz10ed2'))}{s(g.get('strunz10ed3'))}.{s(g.get('strunz10ed4'))}"
            if "APPROVED" in g.get("ima_status") else "",
            "dana8": f"{s(g.get('dana8ed1'))}.{s(g.get('dana8ed2'))}.{s(g.get('dana8ed3'))}.{s(g.get('dana8ed4'))}"
            if "APPROVED" in g.get("ima_status") else "",
        })

    pd.DataFrame(out_rows).to_csv(f"{LOC_NAME}_minerals.csv", index=False, encoding="utf-8-sig")

    print("Wrote:")
    print(f" - {LOC_NAME}_minerals.csv")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    _dir = Path(__file__).resolve().parent
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))
    from mindat_api import configure, load_api_key

    BASE = "https://api.mindat.org"
    LOC_NAME = "Scotland"
    API_KEY = load_api_key(_dir / "API_key.txt")
    configure(
        API_KEY,
        loc_name=LOC_NAME,
        gm_brief_fields="id,name,synid,varietyof,entrytype,ima_status,ima_notes,weighting",
    )

    headers = {'Authorization': 'Token ' + API_KEY}
    S = requests.Session()
    S.headers.update(headers)

    GM_BRIEF_CACHE = {}
    GM_BRIEF_FIELDS = "id,name,synid,varietyof,entrytype,ima_status,ima_notes,weighting"

    GEOMATERIAL_FIELDS = ",".join([
        "id,name,ima_status,ima_formula,mindat_formula,"
        "strunz10ed1,strunz10ed2,strunz10ed3,strunz10ed4",
        "dana8ed1,dana8ed2,dana8ed3,dana8ed4",
    ])

    TAG_RE = re.compile(r"<[^>]+>")
    _SUB_MAP = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")
    _SUP_MAP = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")
    BOX_UNICODE = "◻"
    BOX_ASCII = "[]"

    main(input_csv=str(_dir / "minerals.csv"))
