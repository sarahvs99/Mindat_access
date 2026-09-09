# parse_mindat_localities.py — Organize Locality Names

## Table of Contents

- [What does this script do?](#what-does-this-script-do)
- [What do I need before I start?](#what-do-i-need-before-i-start)
- [What will I get?](#what-will-i-get)
- [Step-by-step instructions](#step-by-step-instructions)
- [How locality names are organized](#how-locality-names-are-organized)
- [County names and alternatives](#county-names-and-alternatives)
- [Common changes you might want to make](#common-changes-you-might-want-to-make)
- [Important notes](#important-notes)

---

## What does this script do?

This script takes the locality names from Mindat and **organizes them into neat, separate columns**.

**The problem:** Mindat stores locality names as one long text string, like:
> "Ben More, Crianlarich, Stirling, Scotland, UK"

**The solution:** This script splits that into separate columns:

| Country  | County   | Place       | Area     | Mine/Quarry |
|----------|----------|-------------|----------|-------------|
| Scotland | Stirling | Crianlarich | Ben More |             |

It also creates a **deduplicated list** — if the same location appears multiple times, it's only listed once (with a count of how many times it appeared).

**Why use this script?**

This makes it much easier to:
- Search and filter by county or region
- Compare localities with museum records
- Create maps or charts
- Spot duplicates or errors

---

## What do I need before I start?

### Required file

You need the output from `fetch_mindat_localities.py`:
- `Scotland_minerals_localities.csv`

**Important:** Run `fetch_mindat_localities.py` first — this script won't work without it.

---

## What will I get?

### File 1: `Scotland_minerals_localities_separated.csv`

This is the original locality table with **new columns added**:

| New Column | What it contains |
|------------|------------------|
| `country` | Country name (e.g., "Scotland") |
| `county` | County or council area (e.g., "Stirling") |
| `place_city_island` | Town, city, or island name |
| `place_area_small` | Smaller area (e.g., glen, valley, estate) |
| `mine_quarry_spot` | Specific site (e.g., mine name, quarry name) |

### File 2: `mindat_unique_locations.csv`

A **cleaned-up list of unique locations** with:

- All the location fields (country, county, place, etc.)
- Coordinates (latitude and longitude)
- Locality type (e.g., mountain, quarry)
- `record_count` — How many times this location appeared in the original data

**Example:**

| locality_id | country | county | place_city_island | record_count |
|-------------|---------|--------|-------------------|--------------|
| 12345 | Scotland | Stirling | Crianlarich | 15 |

This means this location appeared 15 times in the original data (probably for 15 different minerals).

---

## Step-by-step instructions

### Step 1: Check your files

Make sure you have:
- `Scotland_minerals_localities.csv` (from the previous script)

### Step 2: Run the script

**On Windows:**
1. Open Command Prompt
2. Navigate to the folder with the scripts
3. Type: `python parse_mindat_localities.py`
4. Press Enter

**On Mac:**
1. Open Terminal
2. Navigate to the folder with the scripts
3. Type: `python3 parse_mindat_localities.py`
4. Press Enter

### Step 3: Check the results

You should see two new files:
- `Scotland_minerals_localities_separated.csv`
- `mindat_unique_locations.csv`

Open them in Excel to review.

---

## How locality names are organized

The script reads locality names from **right to left** (most general to most specific):

**Example:** "Quarry Name, Village, County, Scotland"

1. **Country** — Identified as "Scotland" (last part)
2. **County** — Identified by matching against a list of Scottish counties
3. **Place/City/Island** — The town or city name
4. **Area** — Intermediate areas (valley, glen, estate)
5. **Mine/Quarry/Spot** — The specific site name (first part)

---

## County names and alternatives

The script knows about all Scottish council areas and some common alternatives:

| If Mindat says... | Script converts to... |
|-------------------|----------------------|
| "Orkney Islands" | "Orkney" |
| "Shetland Islands" | "Shetland" |
| "Outer Hebrides" | "Eilean Siar (Western Isles)" |
| "Western Isles" | "Eilean Siar (Western Isles)" |
| "Eilean Siar" | "Eilean Siar (Western Isles)" |

This helps ensure consistency even when Mindat uses different names for the same place.

---

## Common changes you might want to make

### 1. Add new county alternatives

If you notice a county name isn't being recognized, you can add it. Find this section in the script:

```python
COUNTY_ALIASES = {
    "orkney islands": "Orkney",
    "shetland islands": "Shetland",
    # Add your own here
}
```

Add new alternatives in the same format.

### 2. Change the output file names

Find these lines near the bottom of the script:

```python
separated = _dir / "Scotland_minerals_localities_separated.csv"
unique_out = _dir / "mindat_unique_locations.csv"
```

Change the file names as needed.

### 3. Keep blank locations

By default, completely blank location rows are removed. To keep them, find this line:

```python
drop_fully_blank_locations=True
```

Change to:
```python
drop_fully_blank_locations=False
```

### 4. Remove the record count

If you don't want the `record_count` column in the unique locations file, find:

```python
add_counts=True
```

Change to:
```python
add_counts=False
```

---

## Important notes

- **This is an automatic process** — It works well for most cases, but some unusual locality names may not split perfectly
- **Manual review is recommended** — Check the output in Excel to spot any odd results
- **Duplicates are based on exact matches** — Locations are considered the same if all the fields match exactly after cleaning up extra spaces

---

## What's next?

After running this script, you should open `mindat_unique_locations.csv` in Excel and check for any issues.

---

## Need help?

Return to the [main README](../README.md) for the full workflow.
