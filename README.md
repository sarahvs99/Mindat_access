# Mindat API access scripts

By Sarah Stewart, University of Edinburgh, April-June 2026.

Contact: s.v.stewart@ed.ac.uk 

---

Scripts used to automate the querying and retrieval of information from Mindat.org via the API.
The scripts were originally created to search for Scottish localities, but can be easily modified for other localities. See the individual help pages for information on this.

The main aims of these scripts are to:
- match a mineral list to standardised Mindat mineral records
- retrieve general mineral information such as formula and classification
- retrieve occurrence and locality information
- reorganise Mindat locality strings into more structured location fields
- produce a deduplicated list of localities for later matching and manual review

These scripts are intended to be run in sequence.

---


## Table of Contents
- [Quick Start](#quick-start)
- [Scripts included](#scripts-included)
- [Recommended workflow](#recommended-workflow)
- [Script outputs](#script-outputs)
- [Software requirements](#requirements)
- [Getting an API key](#getting-a-mindat-api-key)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)


## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a file called `API_key.txt` in the same directory as the scripts, containing your Mindat API key

3. Prepare your mineral list as a CSV file with mineral names in the first column

4. Run the scripts in order:
   ```bash
   python fetch_mindat_mineral_info.py
   python fetch_mindat_localities.py
   python parse_mindat_localities.py
   ```

---

## Scripts included

### [mindat_api.py](how-to/mindat-api-helper.md)
Shared helper used by other scripts to retrieve info from Mindat.

### [fetch_mindat_mineral_info.py](how-to/fetch-mindat-mineral-info.md)
Fetches general mineral information from Mindat for a list of mineral names.

### [fetch_mindat_localities.py](how-to/fetch-mindat-localities.md)
Retrieves occurrence and locality information from Mindat for the input minerals.

### [parse_mindat_localities.py](how-to/parse-mindat-localities.md)
Splits Mindat free-text locality strings into structured fields and creates a deduplicated locality list.

---

## Recommended workflow

1. **Prepare mineral list**: Create a CSV with mineral names in the first column
2. **Fetch mineral info**: Run `fetch_mindat_mineral_info.py` to get standardized mineral records
3. **Fetch localities**: Run `fetch_mindat_localities.py` to get occurrence data
4. **Parse localities**: Run `parse_mindat_localities.py` to structure the locality data
5. **Review outputs**: Check the generated CSV files in Excel or similar

---

## Script outputs

The output names are based on a Scottish locality search.

| File                                         | Description                                                                   |
|:---------------------------------------------|:------------------------------------------------------------------------------|
| `Scotland_minerals.csv`                      | Clean Mindat mineral reference table with IDs, formulae, and classifications. |
| `Scotland_minerals_rarity_summary.csv`       | Scottish occurrence summary for the input minerals.                           |
| `Scotland_minerals_localities.csv`           | Scottish mineral-locality output from Mindat.                                 |
| `Scotland_minerals_localities_separated.csv` | Parsed version of the Mindat locality table with structured place fields.     |
| `mindat_unique_locations.csv`                | Deduplicated list of Mindat localities for later review and matching.         |

---

## Requirements

- Python 3.8 or higher
- Mindat API key (free, request from https://www.mindat.org/api.php)
- Dependencies listed in `requirements.txt`

---

## Getting a Mindat API key

1. Create a free account on [Mindat.org](https://www.mindat.org)
2. Visit the [API page](https://www.mindat.org/api.php)
3. Request an API key
4. Save the key in a file called `API_key.txt` in the scripts directory

---

## Customization

### Change the target locality

To search for localities in a different region:

1. Find the Mindat ID for your target locality (e.g., Scotland = 14091)
2. In `fetch_mindat_localities.py`, update:
   ```python
   LOC_NAME = "Your Region Name"
   LOC_ID = 12345  # Your locality ID
   ```

### Modify mineral matching behavior

The matching logic in `fetch_mindat_mineral_info.py` can be adjusted to:
- Change the order of matching preferences
- Add custom synonym handling
- Adjust scoring for different match types

### Extend downloaded fields

To fetch additional data from Mindat, modify the `GEOMATERIAL_FIELDS` or `LOCALITY_FIELDS` constants in the respective scripts.

---

## Troubleshooting

### API key errors
- Ensure `API_key.txt` is in the same directory as the scripts
- Check that the key is valid and not expired
- Verify the key has no extra whitespace

### Rate limiting
- The scripts include built-in rate limiting (0.05s between requests)
- If you encounter rate limit errors, increase the `polite_sleep` value

### Missing minerals
- Check the `match_type` column in the output
- Minerals with `not_found` may need manual review or alternative naming

### Locality parsing issues
- Mindat locality strings are not always consistent
- Review `mindat_unique_locations.csv` for anomalies
- Add new county aliases to `COUNTY_ALIASES` in `parse_mindat_localities.py`

---

## License

These materials are made freely available, and are licensed under a [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) license.
