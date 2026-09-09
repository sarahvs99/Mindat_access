"""Shared Mindat API helpers used by fetch_mindat_localities and fetch_mindat_mineral_info."""

from __future__ import annotations

import re
import time
import unicodedata

import requests

BASE = "https://api.mindat.org"
headers: dict = {}
S: requests.Session | None = None
GM_BRIEF_CACHE: dict = {}
GM_BRIEF_FIELDS = "id,name,synid,varietyof,entrytype,ima_status,ima_notes"
LOC_NAME = ""


def configure(
    api_key: str,
    *,
    base: str = "https://api.mindat.org",
    loc_name: str = "",
    gm_brief_fields: str | None = None,
) -> None:
    """Set API credentials and module globals."""
    global BASE, headers, S, GM_BRIEF_CACHE, GM_BRIEF_FIELDS, LOC_NAME
    BASE = base
    LOC_NAME = loc_name
    if gm_brief_fields:
        GM_BRIEF_FIELDS = gm_brief_fields
    headers = {"Authorization": "Token " + api_key}
    S = requests.Session()
    S.headers.update(headers)
    GM_BRIEF_CACHE = {}


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


def fold_text(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.casefold().strip()


def norm_key(s: str, drop_hyphens: bool = False) -> str:
    s = fold_text(s).replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9\-\(\)]+", "", s)
    if drop_hyphens:
        s = s.replace("-", "")
    return s


def is_ima_species(rec: dict) -> bool:
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
    status = rec.get("ima_status") or ""
    return ("APPROVED" in status) or ("GRANDFATHERED" in status)


def fetch_geomaterials_brief_by_ids(ids):
    ids = [int(i) for i in ids if i is not None]
    missing = [i for i in ids if i not in GM_BRIEF_CACHE]
    if not missing:
        return

    batch_size = 200
    id_param = "id_in"
    endpoint = "/geomaterials/" if BASE.endswith("/v1") else "/v1/geomaterials/"

    for i in range(0, len(missing), batch_size):
        batch = ",".join(map(str, missing[i : i + batch_size]))
        params = {
            id_param: batch,
            "fields": GM_BRIEF_FIELDS,
            "format": "json",
            "page-size": 1000,
        }
        for rec in iter_pages(BASE + endpoint, params=params):
            GM_BRIEF_CACHE[int(rec["id"])] = rec


def canonical_geomaterial_id(gid: int, max_hops: int = 5):
    if gid is None:
        return None, None
    gid = int(gid)
    fetch_geomaterials_brief_by_ids([gid])
    visited = set()
    hops = 0
    while hops < max_hops and gid not in visited:
        visited.add(gid)
        rec = GM_BRIEF_CACHE.get(gid, {})
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
        return None, None, "blank"

    path = "/geomaterials-search/" if BASE.endswith("/v1") else "/v1/geomaterials-search/"
    try:
        hits = get(BASE + path, params={"q": q, "format": "json"})
    except requests.HTTPError:
        return None, None, "search_endpoint_not_found"

    if not hits:
        return None, None, "not_found"

    hit_ids = [int(h["id"]) for h in hits if h.get("id") is not None]
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
        cid, cname = canonical_geomaterial_id(hid)
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
        crec = GM_BRIEF_CACHE.get(cid, {})
        if is_ima_species(crec):
            score += 10
        else:
            score -= 10
        scored.append((score, mt, cid, cname, hid, hname))

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, mt, cid, cname, hid, hname = scored[0]
    return cid, cname, mt


def load_api_key(key_file) -> str:
    """Load API key from file or prompt the user."""
    from pathlib import Path

    path = Path(key_file)
    if path.is_file():
        key = path.read_text(encoding="utf-8").strip()
        if key:
            return key
    return input("Enter your Mindat API key: ").strip()
