# fetch_mindat_localities.py — Get Locality Information from Mindat

## Table of Contents

- [What does this script do?](#what-does-this-script-do)
- [What do I need before I start?](#what-do-i-need-before-i-start)
- [What will I get?](#what-will-i-get)
- [Step-by-step instructions](#step-by-step-instructions)
- [Understanding rarity](#understanding-rarity)
- [Common changes you might want to make](#common-changes-you-might-want-to-make)
- [Important notes](#important-notes)

---

## What does this script do?

This script finds out **where** minerals occur in a specific region (for example, Scotland) by searching Mindat.org. It creates two files:

1. **A summary** — Shows how many localities each mineral is found in, and how rare or common it is
2. **A detailed table** — Lists every mineral-locality combination with location details

**Why use this script?**

This helps you understand the distribution of minerals in your region of interest. You can see which minerals are found where, and whether they are rare or common.

---

## What do I need before I start?

### 1. A Mindat API key

- Get a free API key from [Mindat.org](https://www.mindat.org/api.php)
- Save it in a file called `API_key.txt` in the same folder as the scripts

### 2. A mineral list

You should have already run `fetch_mindat_mineral_info.py` to create your mineral reference file.

**OR** create a simple CSV file with mineral names in the first column:

```
Quartz
Calcite
Pyrite
```

---

## What will I get?

### File 1: `Scotland_minerals_rarity_summary.csv`

A summary table showing:

| Column | What it means |
|--------|---------------|
| `input_name` | The mineral name you provided |
| `mindat_id` | Mindat's unique ID for this mineral |
| `mindat_name` | The official Mindat name |
| `match_type` | How well the name matched (see the other guide) |
| `in_loc` | Whether this mineral is found in your target region (Yes/No) |
| `locality_count` | How many different localities it's found in |
| `rarity_min_text` | The rarest it's reported as (e.g., "Rare") |
| `rarity_max_text` | The most common it's reported as (e.g., "Common") |

### File 2: `Scotland_minerals_localities.csv`

A detailed list of every mineral at every locality:

| Column | What it means |
|--------|---------------|
| `mindat_id` | Mineral ID number |
| `mindat_name` | Mineral name |
| `locality_id` | Locality ID number |
| `locality_name` | Name of the location (as written in Mindat) |
| `locality_type` | Type of place (e.g., quarry, mine, mountain) |
| `latitude` | North-south coordinate |
| `longitude` | East-west coordinate |
| `rarity_min_text` | Rarity at this locality (minimum) |
| `rarity_max_text` | Rarity at this locality (maximum) |

---

## Step-by-step instructions

### Step 1: Check your files

1. Make sure `API_key.txt` exists with your API key
2. Make sure you have a mineral list CSV file

### Step 2: (Optional) Change the target region

By default, the script searches for **Scotland**. To change this:

1. Open `fetch_mindat_localities.py` in a text editor
2. Find these lines:
   ```python
   LOC_NAME = "Scotland"
   LOC_ID = 14091
   ```
3. Change both values to your region (you'll need to find the Mindat ID for your region)

### Step 3: Run the script

**On Windows:**
1. Open Command Prompt
2. Navigate to the folder with the scripts
3. Type: `python fetch_mindat_localities.py`
4. Press Enter

**On Mac:**
1. Open Terminal
2. Navigate to the folder with the scripts
3. Type: `python3 fetch_mindat_localities.py`
4. Press Enter

### Step 4: Check the results

You should see two new files:
- `Scotland_minerals_rarity_summary.csv`
- `Scotland_minerals_localities.csv`

Open them in Excel to review.

---

## Understanding rarity

Mindat users can indicate how rare or common a mineral is at a locality. The script converts these to easy-to-read labels:

| Value | Meaning |
|-------|---------|
| -3 | Extremely Rare |
| -2 | Very Rare |
| -1 | Rare |
| 0 | Not specified / average |
| 1 | Common |
| 2 | Very Common |
| 3 | Extremely Common |

**Note:** Not all Mindat entries include rarity information.

---

## Common changes you might want to make

### 1. Use a different input file

Find this line:
```python
main(input_csv="minerals.csv")
```
Change to your file name.

### 2. Search a different region

Change these lines:
```python
LOC_NAME = "Scotland"
LOC_ID = 14091
```

You'll need to find the Mindat ID for your region. For example:
- Scotland = 14091
- Edinburgh = 24457

---

## Important notes

- **You need an API key** — The script won't work without one
- **Empty files are normal if nothing is found** — If no localities are found in your region, the script still creates empty output files
- **Locality names need cleaning** — The locality names come directly from Mindat and may be inconsistent. Run `parse_mindat_localities.py` next to clean them up

---

## What's next?

After running this script, you should run `parse_mindat_localities.py` to organize the locality names into structured fields (like separating city, county, and mine names).

---

## Need help?

Return to the [main README](../README.md) for the full workflow.
