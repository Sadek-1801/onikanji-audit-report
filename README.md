# OniKanji Flashcard Auditor — README

A small Python utility that audits Japanese flashcard rows (CSV) using an LLM (DeepSeek / SambaNova via the OpenAI-style `OpenAI` client).
It sends each row to a structured audit prompt, collects the model’s response, and writes a Markdown audit report.

---

## Table of contents

* [What this does](#what-this-does)
* [Prerequisites](#prerequisites)
* [Quick start](#quick-start)
* [Install](#install)
* [Configuration (.env)](#configuration-env)
* [Usage](#usage)

  * [Audit single row](#audit-single-row)
  * [Audit entire CSV](#audit-entire-csv)
* [Output format](#output-format)
* [How it works — key functions](#how-it-works---key-functions)
* [Prompt templates](#prompt-templates)
* [Notes, gotchas & suggestions for improvement](#notes-gotchas--suggestions-for-improvement)
* [Troubleshooting](#troubleshooting)
* [Security & best practices](#security--best-practices)
* [Contributing / License](#contributing--license)

---

## What this does

* Loads a CSV of kanji flashcards (default: `./data/raw/onyomiKanjiListNew.csv`).
* For each row, builds a human-readable key\:value block and sends it to the model with an **audit prompt**.
* Collects the model response and writes it into a Markdown report (default: `./data/reports/audit_report.md`).
* Includes functions to audit a single row (useful for debugging) or the entire CSV.

---

## Prerequisites

* Python 3.9+
* An account / API key for the model endpoint used (SambaNova DeepSeek or other API compatible with the `OpenAI` SDK wrapper).
* Basic familiarity with the command line.

---

## Install

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate    # macOS / Linux
venv\Scripts\activate       # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

Example `requirements.txt` (create this file with the repo):

```
pandas
python-dotenv
openai           # provides OpenAI.OpenAI used in the code (SambaNova recommends OpenAI-compatible client)
requests         # optional (commented-out implementation present)
```

> If you prefer to use `requests` to call a raw REST endpoint (commented implementation exists), keep `requests` installed.

---

## Configuration (.env)

Create a `.env` file in the project root with your API key:

```
API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

**Important**: Do **not** commit `.env` to version control.

---

## Quick start

1. Put your CSV file in `./data/raw/onyomiKanjiListNew.csv` (or change `CSV_FILE_PATH`).
2. Confirm `OUTPUT_REPORT` path (default: `./data/reports/audit_report.md`).
3. Run the script:

```bash
python audit_script.py
```

(If your entrypoint file is named differently, run that file — the provided script entrypoint calls `audit_single_row(..., 10)` by default.)

---

## Usage

### Audit a single row

The code provides `audit_single_row(csv_path, output_report, row_index)`.

Example (from `if __name__ == "__main__":` in script):

```python
audit_single_row(CSV_FILE_PATH, OUTPUT_REPORT, 10)
```

This reads the CSV, picks `row_index` (0-based index), formats that row for the prompt, sends it to the model, and writes the response into `OUTPUT_REPORT`.

### Audit entire CSV

Use `audit_csv_file(csv_path, output_report)`:

```python
audit_csv_file(CSV_FILE_PATH, OUTPUT_REPORT)
```

This iterates every row and appends the model's response to the Markdown report. It currently sleeps `1` second between requests to be polite to the API.

---

## Output format

The script writes a Markdown file (`audit_report.md`) containing the model responses appended in the format returned by the model. The prompt requests this structure:

```markdown
### Row {kanjiID}: {kanji}
**Issues:**
- [Issue 1]
- [Issue 2]

**Fixes:**
- [Fix suggestion 1]
- [Fix suggestion 2]
```

There is also a commented alternate prompt which requests a markdown table format. The current active prompt yields the “Row … Issues / Fixes” block.

---

## How it works — key functions

* `clean_value(val)`
  Converts `NaN`/`None` to the string `"None"` and trims whitespace.

* `row_to_dict(row)`
  Converts a pandas `Series` row into a cleaned dictionary mapping column → value.

* `format_row_for_prompt(row_dict)`
  Produces a readable `key: value` string from that dictionary — this gets injected into the prompt.

* `call_deepseek(prompt)`
  Uses `OpenAI(api_key=..., base_url=...)` to call the model (SambaNova DeepSeek via the OpenAI-compatible client).
  Returns the model response text. Catches exceptions and returns an error string.

* `audit_single_row(csv_path, output_report, row_index)`
  Reads CSV, extracts one row, sends it to the model, writes that single-row response to the report.

* `audit_csv_file(csv_path, output_report)`
  Reads CSV, iterates rows, optionally skips rows (see next section), sends each row to the model, appends responses to report. Sleeps 1 second between calls.

---

## Prompt templates

The code contains `AUDIT_PROMPT_TEMPLATE` (active) — a detailed instruction set specifying:

* accuracy & naturalness checks,
* parenthetical hygiene,
* furigana and format rules (kanji//reading//),
* multiple-choice rules (4 options, first must be correct),
* skip logic (if all readings are `"None"`),
* output structure required (markdown block per row).

There’s also an alternate (commented) hybrid prompt that requests a markdown table per row with Severity tags and more edge-case rules.

---

## Notes, gotchas & suggestions for improvement

**1. Onyomi vs Kunyomi check mismatch**

* The CSV filename is `onyomiKanjiListNew.csv`. The code currently checks `onyomiReadingOne/Two/Three` for skipping rows. Your prompt and other conversations referenced *kunyomi* auditing. Confirm which set (onyomi or kunyomi) the audit is intended for — and make the skip-check and prompt consistent.

**2. API client & endpoint**

* The code uses `from openai import OpenAI` and creates a client with `base_url = API_ENDPOINT` (`https://api.sambanova.ai/v1`). This works only if the server is OpenAI-compatible and the OpenAI client is appropriate for SambaNova. Validate with your vendor docs.
* A commented `requests` implementation exists — useful if you prefer custom REST calls.

**3. Rate limits & retries**

* Current code uses `time.sleep(1)` between calls. Add robust retry/backoff for transient errors (HTTP 429 / timeouts). Use the `backoff` package or write a simple exponential backoff.

**4. Partial results & safety**

* For large CSVs, write incremental results to disk (append) so you don't lose progress on error. Right now the script assembles in memory and writes once at the end.

**5. Command-line interface & flexibility**

* Add `argparse` for CLI flags (`--input`, `--output`, `--row-index`, `--delay`, `--start`, `--end`).

**6. Logging & progress**

* Use `logging` module and `tqdm` for progress bars.

**7. Validation**

* Add local checks before calling the model (e.g., check that multiple choice fields are 4 options, ensure kana-only MCs) to reduce API calls.

**8. Security**

* Ensure `.env` is in `.gitignore`. Don’t log raw API keys.

**9. Cost & token control**

* If using a paid model, reduce prompt size by omitting `None` fields and only sending relevant fields.

---

## Troubleshooting

* **`FileNotFoundError`** — confirm `CSV_FILE_PATH` exists.
* **API errors** — check `.env` `API_KEY` and that the endpoint is reachable. Check vendor docs for correct `MODEL_NAME`.
* **Unexpected prompt responses** — ensure prompt template is not changed in ways that allow free-form output. Enforce stricter output by specifying exact output format at the end of prompt.

---

## Example commands

Run single row audit:

```bash
python audit_script.py
# (script is set to call audit_single_row(..., 10) in __main__)
```

Run full audit (after editing `__main__` or exposing CLI):

```python
# in __main__ or interactive shell
audit_csv_file("./data/raw/onyomiKanjiListNew.csv", "./data/reports/audit_report.md")
```

---

## Suggested development roadmap (for next 1–2 days)

1. Add `argparse` to set `--input`, `--output`, `--row-index`, `--mode` (single|all).
2. Add retry/backoff for API calls (handle 429/timeout).
3. Append results incrementally to the report file for resilience.
4. Add logging and `tqdm` progress bar.
5. Add a local pre-check that flags obvious structural errors before calling the model.
6. Fix the `onyomi` vs `kunyomi` skip-check mismatch.

---

## Security & best practices

* Never commit `API_KEY` or `.env`.
* Use role-based API keys where possible.
* Keep prompt templates as separate files if you need versioning.
* Sanitize any output if you will display or publish the report.

---

## Contributing / License

* Contributions welcome — create issues / PRs.
* Add a license file (MIT recommended if you want freedom to reuse).

---
