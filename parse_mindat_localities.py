import sys
from pathlib import Path

for _r in Path(__file__).resolve().parents:
    if (_r / "project_paths.py").is_file():
        sys.path.insert(0, str(_r))
        break

import pandas as pd
import re
import unicodedata

SCOTTISH_COUNTIES = [
    "Aberdeen City", "Aberdeenshire", "Moray",
    "Argyll and Bute", "Eilean Siar (Western Isles)", "Highland", "Orkney", "Shetland",
    "Angus", "Clackmannanshire", "Dundee City", "Falkirk", "Fife", "Perth and Kinross", "Stirling",
    "City of Edinburgh", "East Lothian", "Midlothian", "West Lothian",
    "East Ayrshire", "East Dunbartonshire", "East Renfrewshire", "Glasgow City", "Inverclyde",
    "North Ayrshire", "North Lanarkshire", "Renfrewshire", "South Ayrshire", "South Lanarkshire",
    "West Dunbartonshire", "Dumfries and Galloway", "Scottish Borders"
]


def fold(s: str) -> str:
    """Lowercase, remove accents/diacritics, normalise spaces."""
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s


COUNTY_LOOKUP = {fold(c): c for c in SCOTTISH_COUNTIES}
# Useful aliases seen in Mindat locality strings
COUNTY_ALIASES = {
    fold("Orkney Islands"): "Orkney",
    fold("Shetland Islands"): "Shetland",
    fold("Outer Hebrides"): "Eilean Siar (Western Isles)",
    fold("Western Isles"): "Eilean Siar (Western Isles)",
    fold("Eilean Siar"): "Eilean Siar (Western Isles)",
}
COUNTY_LOOKUP.update({k: v for k, v in COUNTY_ALIASES.items()})


def parse_locality(full: str):
    """
    Returns dict for country, county, place_city_island, place_area_small, mine_quarry_spot
    """
    if full is None or str(full).strip() == "":
        return {
            "country": "",
            "county": "",
            "place_city_island": "",
            "place_area_small": "",
            "mine_quarry_spot": "",
        }

    s = str(full).strip()

    # normalise odd commas in your data (fullwidth comma etc.)
    s = s.replace("，", ",").replace("‚", ",").replace("、", ",")

    parts = [p.strip() for p in s.split(",") if p.strip()]

    # country (usually last)
    country = ""
    if parts and fold(parts[-1]) in {fold("uk"), fold("united kingdom")}:
        parts = parts[:-1]

    # remove Scotland if present (you can keep this in a separate column if you want)
    if parts and fold(parts[-1]) == fold("scotland"):
        country = "Scotland"
        parts = parts[:-1]

    # find county by scanning from the right
    county = ""
    county_idx = None
    for i in range(len(parts) - 1, -1, -1):
        f = fold(parts[i])
        if f in COUNTY_LOOKUP:
            county = COUNTY_LOOKUP[f]
            county_idx = i
            break

    below = parts[:county_idx] if county_idx is not None else parts[:]

    # Convert below-county from [specific -> general] to [general -> specific]
    levels = list(reversed(below))

    place_city_island = ""
    place_area_small = ""
    mine_quarry_spot = ""

    if len(levels) == 1:
        place_city_island = levels[0]
    elif len(levels) == 2:
        place_city_island = levels[0]
        place_area_small = levels[1]
    elif len(levels) >= 3:
        place_city_island = levels[0]
        mine_quarry_spot = levels[-1]
        place_area_small = ", ".join(levels[1:-1]).strip()

        # safety: if join produced empty somehow, shift-left again
        if not place_area_small:
            place_area_small = mine_quarry_spot
            mine_quarry_spot = ""

    return {
        "country": country,
        "county": county,
        "place_city_island": place_city_island,
        "place_area_small": place_area_small,
        "mine_quarry_spot": mine_quarry_spot,
    }


def normalise_text(s: pd.Series):
    s = s.astype("string")
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s.fillna("")


def dedupe_location_rows(input_csv, output_csv="unique_locations.csv",
                      drop_fully_blank_locations=True, add_counts=True):
    LOCATION_COLS = [
        "locality_id",
        "country",
        "county",
        "place_city_island",
        "place_area_small",
        "mine_quarry_spot",
        "latitude", "longitude",
        "locality_type"
    ]
    df = pd.read_csv(input_csv)

    missing = [c for c in LOCATION_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing location columns: {missing}. Found: {list(df.columns)}")

    for c in LOCATION_COLS:
        df[c] = normalise_text(df[c])

    if drop_fully_blank_locations:
        df = df.loc[~(df[LOCATION_COLS].eq("").all(axis=1))].copy()

    loc_df = df[LOCATION_COLS].copy()
    unique_locs = loc_df.drop_duplicates(subset=LOCATION_COLS, keep="first")
    if add_counts:
        counts = (
            loc_df.groupby(LOCATION_COLS, dropna=False)
            .size()
            .reset_index(name="record_count")
        )
        unique_locs = counts
    unique_locs.to_csv(output_csv, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    import project_paths

    _dir = project_paths.script_dir(__file__)
    input_csv = _dir / "Scotland_minerals_localities.csv"
    separated = _dir / "Scotland_minerals_localities_separated.csv"
    unique_out = _dir / "mindat_unique_locations.csv"
    project_paths.require_file(input_csv)

    df = pd.read_csv(input_csv)
    df["locality_name"] = df["locality_name"].fillna("")
    parsed = df["locality_name"].apply(parse_locality).apply(pd.Series)
    df = pd.concat([df, parsed], axis=1)
    df.to_csv(separated, index=False, encoding="utf-8-sig")

    dedupe_location_rows(str(separated), str(unique_out))
    project_paths.print_done(
        unique_out,
        next_step="Review mindat_unique_locations in Excel, then match_localities_to_mindat.py",
    )
