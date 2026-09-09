# fetch_mindat_mineral_info.py — Get Mineral Information from Mindat

## Table of Contents

- [What does this script do?](#what-does-this-script-do)
- [What do I need before I start?](#what-do-i-need-before-i-start)
- [What will I get?](#what-will-i-get)
- [Step-by-step instructions](#step-by-step-instructions)
- [Understanding the results](#understanding-the-results)
- [Common changes you might want to make](#common-changes-you-might-want-to-make)
- [Important notes](#important-notes)

---

## What does this script do?

This script takes a list of mineral names and looks them up on Mindat.org. It creates a clean reference table that includes:

- The standardized Mindat name for each mineral
- A unique Mindat ID number
- The chemical formula
- Classification information (Strunz and Dana systems)

**Why use this script?**

Mineral names can be spelled different ways or have synonyms. This script helps you match your mineral list to the official Mindat records, making sure you're working with the correct, standardized names.

It's smart enough to:

- Ignore capitalization (e.g., "Quartz" vs "quartz")
- Ignore accents (e.g., "Müllerite" vs "Mullerite")
- Ignore hyphens (e.g., "Rock Salt" vs "Rock-Salt")
- Follow synonyms to the correct official name
- Prefer official IMA-approved mineral names over informal varieties

---

## What do I need before I start?

### 1. A Mindat API key

- Get a free API key from [Mindat.org](https://www.mindat.org/api.php)
- Save it in a file called `API_key.txt` in the same folder as the scripts

### 2. A mineral list

Create a CSV file (like a simple Excel spreadsheet saved as `.csv`) with:

- Mineral names in the **first column**
- One mineral per row
- No special formatting needed

**Example:**

```
Quartz
Calcite
Pyrite
Galena
```

You can save this as `minerals.csv`.

---

## What will I get?

### Output file: `Scotland_minerals.csv`

This is a spreadsheet with the following columns:

| Column | What it means |
|--------|---------------|
| `input_name` | The mineral name you provided |
| `mindat_id` | Mindat's unique ID number for this mineral |
| `mindat_name` | The official Mindat name |
| `match` | How well your name matched (see below) |
| `ima_status` | Whether it's an officially approved mineral |
| `formula_unicode` | Chemical formula with proper subscripts |
| `formula_ascii` | Chemical formula in simple text |
| `strunz10` | Strunz classification code |
| `dana8` | Dana classification code |

---

## Step-by-step instructions

### Step 1: Prepare your files

1. Save your Mindat API key in `API_key.txt`
2. Save your mineral list as a CSV file (e.g., `minerals.csv`)

### Step 2: Open the script

1. Open `fetch_mindat_mineral_info.py` in a text editor (like Notepad)
2. Find the line that says:
   ```python
   main(input_csv="minerals.csv")
   ```
3. If your file has a different name, change it to match

### Step 3: Run the script

**On Windows:**
1. Open Command Prompt
2. Navigate to the folder with the scripts
3. Type: `python fetch_mindat_mineral_info.py`
4. Press Enter

**On Mac:**
1. Open Terminal
2. Navigate to the folder with the scripts
3. Type: `python3 fetch_mindat_mineral_info.py`
4. Press Enter

### Step 4: Check the results

Look for a new file called `Scotland_minerals.csv` in the same folder. Open it in Excel to review.

---

## Understanding the results

### Match types explained

The `match` column tells you how well each mineral name matched:

| Match Type | What it means |
|------------|---------------|
| `exact_name` | Perfect match — your spelling matches Mindat exactly |
| `diacritic_insensitive` | Match found after removing accents (e.g., é → e) |
| `hyphen_insensitive` | Match found after ignoring hyphens or spaces |
| `fallback` | A match was found, but it's not very close — review this one |
| `not_found` | No match found — this mineral may need manual checking |
| `blank` | Empty row in your input file |

### What should I do with `not_found` minerals?

Minerals that weren't found are still included in the output. You can:

1. Check the spelling
2. Try alternative names or synonyms
3. Accept that some names may not be in Mindat's database

---

## Common changes you might want to make

### 1. Use a different input file

Find this line in the script:
```python
main(input_csv="minerals.csv")
```
Change `"minerals.csv"` to your file name.

### 2. Change the output file name prefix

Find this line:
```python
LOC_NAME = "Scotland"
```
Change `"Scotland"` to your region or project name. This changes the output file name (e.g., `Wales_minerals.csv`).

---

## Important notes

- **You need an API key** — The script won't work without a valid Mindat API key
- **Synonyms are handled automatically** — If you use an old or alternative name, the script will try to find the current official name
- **Classification codes are only for approved minerals** — Strunz and Dana codes are only filled in for officially recognized minerals
- **Unmatched minerals are kept** — Even if a mineral isn't found, it stays in the output so you can review it later

---

## Need help?

Return to the [main README](../README.md) for the full workflow.
