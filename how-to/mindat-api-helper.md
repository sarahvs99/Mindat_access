# mindat_api.py — Helper Script

## What is this script for?

This is a **support script** that helps other scripts connect to and retrieve data from Mindat.org. You do not need to run this script directly — it works in the background when you use the other scripts.

**Think of it like:** A translator that helps the other scripts "speak" to the Mindat website.

---

## What does it do?

This script handles the technical details of:

- Connecting to Mindat using your API key
- Sending requests to Mindat's database
- Receiving and organizing the data that comes back
- Managing the connection so it doesn't overwhelm Mindat's servers

---

## Do I need to use this directly?

**No.** This script is automatically used by:

- `fetch_mindat_mineral_info.py` — for getting mineral details
- `fetch_mindat_localities.py` — for getting locality information

You only need to make sure:

1. Your Mindat API key is saved in a file called `API_key.txt`
2. The `API_key.txt` file is in the same folder as the scripts

---

## For technical users

If you are familiar with programming, this module provides:

- `configure()` — Sets up the API connection with your key
- `get()` — Makes safe web requests with built-in delays
- `iter_pages()` — Handles multi-page results from Mindat
- `fold_text()` — Normalizes text for comparison (handles accents, special characters)
- `is_ima_species()` — Checks if a mineral is an officially approved species

---

## Troubleshooting

If you see errors related to this script:

1. **Check your API key** — Make sure `API_key.txt` exists and contains your key
2. **Check the file location** — `API_key.txt` should be in the same folder as the scripts
3. **Check your internet connection** — This script needs to connect to mindat.org

---

## Back to main guide

Return to the [README](../README.md) for the full workflow.
