import re
import time
import requests
import unicodedata
import pandas as pd
from tqdm import tqdm


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
        return None, None, "blank"

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


def fetch_geomaterial_names_by_ids(ids):
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

    batches = [ids[i:i+BATCH] for i in range(0, len(ids), BATCH)]
    for batch_ids in tqdm(batches):
        batch = ",".join(batch_ids)
        params = {
            id_param: batch,
            "fields": "id,name",
            "format": "json",
            "page-size": 1000,
        }
        for rec in iter_pages(BASE + endpoint, params=params):
            out[int(rec["id"])] = rec.get("name", "")
    return out


def get_revtxtd(loc_id: int):
    if BASE.endswith("/v1"):
        path = f"/localities/{loc_id}"
    else:
        path = f"/v1/localities/{loc_id}"

    sc = get(BASE + path)
    rev = (sc.get("revtxtd") or "").strip()
    if not rev:
        raise RuntimeError(f"{LOC_NAME} locality record has no revtxtd; cannot filter via lorevtxtd.")
    return rev, sc


def iter_occurrences_for_minerals(min_ids, revtxtd):
    params = {
        "min": ",".join(map(str, min_ids)),
        "lorevtxtd": revtxtd,
        "fields": "id,min,loc,rarity",
        "format": "json",
        "page-size": 1000,
    }

    if BASE.endswith("/v1"):
        path = f"/occurrences/"
    else:
        path = f"/v1/occurrences/"

    yield from iter_pages(BASE + path, params=params)


def get_locality_type_map():
    """
    Returns dict: {lt_id: lt_text}
    """
    global LOCALITY_TYPE_MAP
    if LOCALITY_TYPE_MAP is not None:
        return LOCALITY_TYPE_MAP

    if BASE.endswith("/v1"):
        path = f"/locality-type/"
    else:
        path = f"/v1/locality-type/"

    m = {}
    for rec in iter_pages(BASE + path, params={"format": "json", "page-size": 1000}):
        lt_id = rec.get("lt_id")
        lt_text = rec.get("lt_text")
        if lt_id is not None:
            m[int(lt_id)] = lt_text or ""

    LOCALITY_TYPE_MAP = m
    return m


def fetch_localities_by_ids(ids):
    """
        Fetch locality name + lat/lon for a list of locality IDs, batched.
    """
    ids = [int(i) for i in ids if i is not None]
    if not ids:
        return {}

    type_map = get_locality_type_map()

    out = {}
    BATCH = 200
    batches = [ids[i:i + BATCH] for i in range(0, len(ids), BATCH)]

    if BASE.endswith("/v1"):
        path = f"/localities/"
    else:
        path = f"/v1/localities/"

    for batch in tqdm(batches):
        params = {
            "id_in": ",".join(map(str, batch)),
            "fields": "id,txt,latitude,longitude,locality_type",
            "format": "json",
            "page-size": 1000,
        }
        page_results = list(iter_pages(BASE + path, params=params))

        returned_ids = {int(r["id"]) for r in page_results if "id" in r}
        if returned_ids.isdisjoint(set(batch)):
            raise RuntimeError(
                "Locality ID filter seems to have been ignored. "
                "Double-check that /v1/localities/ supports id_in for your key/tier."
            )

        for rec in page_results:
            lt_id = rec.get("locality_type")
            rec["locality_type_text"] = type_map.get(int(lt_id), "") if lt_id is not None else ""
            out[int(rec["id"])] = rec
    return out


def main(input_csv="minerals.csv"):
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

    # Step 2 - get mineral name (in case fuzzy search is used)
    id_to_name = fetch_geomaterial_names_by_ids(ids)

    # Step 3 - get revtxtd prefix for occurrence filtering
    rev, loc = get_revtxtd(LOC_ID)
    print(f"{LOC_NAME} locality: {loc.get('txt')} | revtxtd prefix = {rev}")

    # Step 4 - fetch occurrence
    occ_rows = []
    BATCH_MIN = 50
    min_batches = [ids[i:i + BATCH_MIN] for i in range(0, len(ids), BATCH_MIN)]
    print(f"Fetching {LOC_NAME} occurrences...")
    for b in tqdm(min_batches):
        for occ in iter_occurrences_for_minerals(b, rev):
            mid = occ.get("min")
            lid = occ.get("loc")
            if mid is None or lid is None:
                continue
            occ_rows.append({
                "occurrence_id": occ.get("id"),
                "mindat_id": int(mid),
                "mindat_name": id_to_name.get(int(mid), ""),
                "locality_id": int(lid),
                "rarity": occ.get("rarity"),
            })
    df_occ = pd.DataFrame(occ_rows)

    # If no occurrences at all, still write empty files with headers
    if df_occ.empty:
        pd.DataFrame(columns=[
            "mindat_id", "mindat_name", "locality_id", "locality_name", "latitude", "longitude",
            "rarity_min", "rarity_max"
        ]).to_csv(f"{LOC_NAME}_minerals_localities.csv", index=False, encoding="utf-8-sig")

        pd.DataFrame(columns=[
            "input_name", "mindat_id", "mindat_name", "match_type",
            "in_loc", "locality_count"
            "rarity_min_text", "rarity_max_text",
        ]).to_csv(f"{LOC_NAME}_minerals_rarity_summary.csv", index=False, encoding="utf-8-sig")

        print(f"No {LOC_NAME} occurrences found for any resolved minerals.")
        return

    # Step 5 - fetch locality details (txt + lat/lon) for unique localities
    all_lids = sorted(set(df_occ["locality_id"].unique().tolist()))
    loc_map = fetch_localities_by_ids(all_lids)

    # attach locality info
    df_occ["locality_name"] = df_occ["locality_id"].map(lambda x: loc_map.get(int(x), {}).get("txt", ""))
    df_occ["locality_type"] = df_occ["locality_id"].map(lambda x: loc_map.get(int(x), {}).get("locality_type_text", ""))
    df_occ["latitude"] = df_occ["locality_id"].map(lambda x: loc_map.get(int(x), {}).get("latitude", None))
    df_occ["longitude"] = df_occ["locality_id"].map(lambda x: loc_map.get(int(x), {}).get("longitude", None))

    # Step 6 - mineral-locality table (aggregate multiple occurrence rows if any)
    df_occ_num = df_occ.copy()
    df_occ_num["rarity"] = pd.to_numeric(df_occ_num["rarity"], errors="coerce")
    df_ml = (
        df_occ_num
        .groupby(["mindat_id", "mindat_name", "locality_id", "locality_name", "locality_type", "latitude", "longitude"], dropna=False)
        .agg(
            rarity_min=("rarity", "min"),
            rarity_max=("rarity", "max"),
            occurrence_records_count=("occurrence_id", "count"),
        )
        .reset_index()
        .sort_values(["mindat_name", "locality_name"])
    )
    df_ml["rarity_min_text"] = df_ml["rarity_min"].map(lambda x: RARITY_TEXT.get(int(x)) if pd.notna(x) else "")
    df_ml["rarity_max_text"] = df_ml["rarity_max"].map(lambda x: RARITY_TEXT.get(int(x)) if pd.notna(x) else "")
    df_ml = df_ml[[
        "mindat_id", "mindat_name",
        "locality_id", "locality_name", "locality_type",
        "latitude", "longitude",
        "rarity_min_text", "rarity_max_text",
    ]]
    df_ml.to_csv(f"{LOC_NAME}_minerals_localities.csv", index=False, encoding="utf-8-sig")

    # Step 7 - per-mineral rarity summary
    per_min = (
        df_occ_num
        .groupby(["mindat_id"], dropna=False)
        .agg(
            mindat_name=("mindat_name", "first"),
            occurrence_records_count=("occurrence_id", "count"),
            locality_count=("locality_id", pd.Series.nunique),
            rarity_min=("rarity", "min"),
            rarity_max=("rarity", "max"),
        )
        .reset_index()
    )
    per_min["rarity_min_text"] = per_min["rarity_min"].map(lambda x: RARITY_TEXT.get(int(x)) if pd.notna(x) else "")
    per_min["rarity_max_text"] = per_min["rarity_max"].map(lambda x: RARITY_TEXT.get(int(x)) if pd.notna(x) else "")
    per_min["in_loc"] = per_min["locality_count"] > 0

    # Merge back onto the resolved input list
    df_out = df_res.copy()
    df_out["mindat_id"] = pd.to_numeric(df_out["mindat_id"], errors="coerce")
    df_out = df_out.merge(per_min, how="left", left_on="mindat_id", right_on="mindat_id")

    # Fill blanks for unresolved or not-in-loc
    df_out["mindat_name"] = df_out.apply(
        lambda r: id_to_name.get(int(r["mindat_id"])) if pd.notna(r["mindat_id"]) else "",
        axis=1
    )
    df_out["in_loc"] = df_out["in_loc"].fillna(False)
    df_out["locality_count"] = df_out["locality_count"].fillna(0).astype(int)

    # keep just the columns you care about
    df_out = df_out[[
        "input_name", "mindat_id", "mindat_name", "match_type",
        "in_loc",
        "locality_count",
        "rarity_min_text",
        "rarity_max_text",
    ]]

    df_out.to_csv(f"{LOC_NAME}_minerals_rarity_summary.csv", index=False, encoding="utf-8-sig")

    print("Wrote:")
    print(f" - {LOC_NAME}_minerals_rarity_summary.csv")
    print(f" - {LOC_NAME}_minerals_localities.csv")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    _dir = Path(__file__).resolve().parent
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))
    from mindat_api import configure, load_api_key

    BASE = "https://api.mindat.org"
    LOC_NAME = "Scotland"
    LOC_ID = 14091
    API_KEY = load_api_key(_dir / "API_key.txt")
    configure(API_KEY, loc_name=LOC_NAME)

    headers = {'Authorization': 'Token ' + API_KEY}
    S = requests.Session()
    S.headers.update(headers)

    GM_BRIEF_CACHE = {}
    GM_BRIEF_FIELDS = "id,name,synid,varietyof,entrytype,ima_status,ima_notes"

    LOCALITY_TYPE_MAP = None

    RARITY_TEXT = {
        -3: "Extremely Rare",
        -2: "Very Rare",
        -1: "Rare",
        0: "Not specified / average",
        1: "Common",
        2: "Very Common",
        3: "Extremely Common",
    }

    main(input_csv=str(_dir / "minerals.csv"))
