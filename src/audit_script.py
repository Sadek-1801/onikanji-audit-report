import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import requests
import json
import time
from typing import Dict, List, Any

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_ENDPOINT = "https://api.sambanova.ai/v1"
MODEL_NAME = "DeepSeek-V3-0324"

CSV_FILE_PATH = "./data/raw/kunyomiKanjiListNew.csv" 
OUTPUT_REPORT = "audit_report.md"


# client = OpenAI(
#     api_key = os.getenv("API_KEY"),
#     base_url="https://api.sambanova.ai/v1",
# )

# response = client.chat.completions.create(
#     model="DeepSeek-V3-0324",
#     messages=[{"role":"system","content":"You are a helpful assistant"},{"role":"user","content":"Hello"}],
#     temperature=0.1,
#     top_p=0.1
# )

# print(response.choices[0].message.content)

# ================================
# PROMPT TEMPLATE
# ================================
# AUDIT_PROMPT_TEMPLATE = """
# I need your help auditing a Japanese flashcard entry for my app OniKanji.

# Here is the flashcard data in key-value format:
# {row_data_str}

# ### Audit Rules:
# 1. **Accuracy & Naturalness**:
#    - Japanese: Flag stiff, textbook-like, or unnatural phrasing (e.g., 「あなたの国」 → 「そちら」).
#    - English: Fix awkward translations (e.g., "join a class" → "enroll"), remove filler words ("very", "really"), avoid passive voice.
#    - Reject non-standard compounds (e.g., 「民朝」).

# 2. **Parenthetical Hygiene**:
#    - Remove ALL English notes in Japanese fields (e.g., 選ぶ (to choose)).
#    - Remove redundant clarifications in translations (e.g., "king (ruler)").

# 3. **Furigana Rules**:
#    - Sample sentences: All kanji must have furigana in format `漢字//よみ//`.
#    - Vocab words: Furigana should NOT be given on the target kanji being tested.
#    - Ensure syntax: `出//で//かける前//まえ//に`.

# 4. **Multiple Choice**:
#    - Must have exactly 4 options.
#    - First option must be correct and match the vocab word reading.
#    - Distractors must be plausible.

# 5. **Empty/None Fields**:
#    - If all readings are "None", skip the entry.

# 6. **Consistency**:
#    - Column suffixes must match (e.g., kunyomiVocabWordOne ↔ kunyomiMultipleChoiceReadingOne).
#    - All fields should follow naming and formatting standards.

# ### Output Format (Markdown):
# Return **only** the following structure:

# ### Row {kanjiID}: {kanji}
# **Issues:**
# - [Issue 1]
# - [Issue 2]

# **Fixes:**
# - [Fix suggestion 1]
# - [Fix suggestion 2]

# If no issues, return:
# ### Row {kanjiID}: {kanji}
# **Issues:** None  
# **Fixes:** None
# """

# ================================
# PROMPT TEMPLATE 2nd VERSION
# ================================

AUDIT_PROMPT_TEMPLATE = """
## **Flashcard Audit Prompt – Hybrid Final Version**

### **🎯 Objective**

Audit Japanese flashcard data for **accuracy, naturalness, and formatting compliance** according to the rules below.

---

### **📜 Core Rules to Enforce**

#### **1. Language Naturalness**

* **🇯🇵 Japanese**

  * Replace stiff/textbook phrasing with native-like expressions (例: 「あなたの国」→「そちら」).
  * Reject unnatural/non-standard compounds (例: 「民朝」).
  * Avoid overuse of pronouns (「あなた」, 「彼」) — prefer context-appropriate nouns or implied subjects.
* **🇺🇸 English**

  * Fix awkward or overly literal translations.
  * Remove filler words (“very,” “really”) unless crucial to nuance.
  * Avoid passive voice where active is clearer.

---

#### **2. 📝 Parenthetical Hygiene**

* **Delete all**:

  * English notes in Japanese fields (例: 選ぶ (to choose)).
  * Redundant clarifications in English translations (例: “king (ruler)”).
* **Keep only**:

  * Parentheses integral to meaning (例: “(whispering)” in stage direction).

---

#### **3. 🏗 Structural Rules**

* **Skip entry if**:

  * All three `kunyomiReading` fields = `"None"`.
* **Furigana**:

  * **Vocab Words**: Furigana only on kanji **not** being tested.
  * **Sample Sentences**: All kanji must have furigana.
  * **Format**: `Kanji//Reading//` (strict syntax).
* **Multiple Choice**:

  * Exactly 4 options.
  * First = correct answer (matches `kunyomiVocabWordReading`).
  * Distractors = plausible but incorrect.
* **Column Alignment**:

  * Numerical suffixes must match across related columns (例: `kunyomiVocabWordOne` ↔ `kunyomiMultipleChoiceReadingOne`).

---

#### **4. 🚩 Edge Cases to Flag**

* Malformed furigana (例: 今日/きょう/ or 今日//きょ//う//).
* Kanji present in multiple-choice reading (should be kana only).
* Reading mismatch (first MC option ≠ correct reading).
* Non-standard characters (emoji, foreign punctuation, full-width Latin).
* Missing meaning (word present but translation empty).
* Pronoun ambiguity in Japanese — suggest neutral/appropriate alternative.

---

### **🔍 Audit Workflow**

1. **Parentheses Check** → Remove disallowed ones.
2. **Naturalness Review** → Read aloud in Japanese & English; flag awkwardness.
3. **Structural Validation** → Furigana, multiple choice, column alignment.
4. **Edge Case Review** → Identify malformed data or non-standard text.
5. **Fix Suggestions** → Provide specific, rule-compliant corrections.

---

### **📤 Output Format**

Always return results in **markdown table** format:

```markdown
| ID | Issue | Fix | Severity |
|----|-------|-----|----------|
| 442 氏 | Unnatural Japanese: 「あなたの国」 | Replace with 「そちら」 | High |
| 442 氏 | Parenthetical in translation: "(citizens)" | Remove parentheses | Medium |
```

* **Severity Levels**:

  * **High**: Violates core structural/naturalness rule.
  * **Medium**: Style/naturalness improvement.
  * **Low**: Minor optional suggestion.

---

### **📌 Rule Summary for Retention**

* ✅ Natural Japanese & English — no stiffness, filler, or overuse of pronouns.
* 🚫 Delete disallowed parentheses; keep only meaningful ones.
* 🎯 Furigana rules — tested kanji = no furigana; others annotated; strict `//` syntax.
* 📊 MC rules — 4 options, correct first, plausible distractors, kana-only readings.
* 🔢 Columns must align via suffixes.
* 🚩 Flag malformed furigana, missing meaning, non-standard chars, pronoun ambiguity.
"""

# ================================
# HELPER FUNCTIONS
# ================================
def clean_value(val: Any) -> str:
    """Convert NaN/None to 'None' string for consistent handling."""
    if pd.isna(val) or val is None:
        return "None"
    return str(val).strip()


def row_to_dict(row: pd.Series) -> Dict[str, str]:
    """Convert a pandas row to a clean dictionary."""
    return {col: clean_value(val) for col, val in row.items()}


def format_row_for_prompt(row_dict: Dict[str, str]) -> str:
    """Format the row data as a readable string for the prompt."""
    return "\n".join([f"{k}: {v}" for k, v in row_dict.items()])


# def call_deepseek(prompt: str) -> str:
#     """Call DeepSeek API and return the response text."""
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "model": MODEL_NAME,
#         "messages": [
#             {"role": "user", "content": prompt}
#         ],
#         "temperature": 0.2,
#         "max_tokens": 1024
#     }

#     try:
#         response = requests.post(API_ENDPOINT, headers=headers, json=payload)
#         response.raise_for_status()
#         result = response.json()
#         return result["choices"][0]["message"]["content"].strip()
#     except requests.exceptions.RequestException as e:
#         return f"[ERROR: API call failed - {e}]"
#     except Exception as e:
#         return f"[ERROR: Parsing failed - {e}]"

def call_deepseek(prompt: str) -> str:
	client = OpenAI(
		api_key = API_KEY,
		base_url = API_ENDPOINT
	)

	try:
		response = client.chat.completions.create(
      	model = MODEL_NAME,
      	messages = [{"role": "user", "content": prompt}],
      	temperature=0.2,
      	max_tokens=1024 
			)

		return response.choices[0].message.content.strip()
	except Exception as e:
		return f"[ERROR: API call failed - {e}]"

def audit_single_row(csv_path: str, row_index: int):
    """Audits a single row from the CSV and prints the report."""
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
        return

    # Check if the row index is valid
    if row_index not in df.index:
        print(f"❌ Row index {row_index} is not in the DataFrame.")
        return

    print(f"🔍 Auditing a single row ({row_index})...")

    # Get the specific row by its index
    row = df.loc[row_index]
    row_dict = row_to_dict(row)
    kanji_id = row_dict.get("kanjiID", "Unknown")
    kanji_char = row_dict.get("kanji", "N/A")

    # Format row data for prompt
    row_data_str = format_row_for_prompt(row_dict)
    prompt = AUDIT_PROMPT_TEMPLATE.format(
        row_data_str=row_data_str,
        kanjiID=kanji_id,
        kanji=kanji_char
    )

    # Call AI and print the response directly
    ai_response = call_deepseek(prompt)
    print("\n" + ai_response + "\n")

    print(f"✅ Audit for row {row_index} complete.")


def audit_csv_file(csv_path: str, output_report: str):
    """Main function to audit the CSV and generate a report."""
    print("🚀 Loading CSV file...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"✅ Loaded {len(df)} rows. Starting audit...")

    report_lines = []
    report_lines.append("# OniKanji Flashcard Audit Report\n")
    report_lines.append("This report audits each row for formatting, naturalness, furigana, multiple choice, and consistency.\n")

    for idx, row in df.iterrows():
        row_dict = row_to_dict(row)
        kanji_id = row_dict.get("kanjiID", "Unknown")
        kanji_char = row_dict.get("kanji", "N/A")

        print(f"🔍 Auditing Row {kanji_id} ({kanji_char})...")

        # Skip if all onyomi readings are None
        onyomi_readings = [
            row_dict.get("onyomiReadingOne", "None"),
            row_dict.get("onyomiReadingTwo", "None"),
            row_dict.get("onyomiReadingThree", "None")
        ]
        if all(r == "None" for r in onyomi_readings):
            print(f"⏩ Skipping Row {kanji_id}: All onyomi readings are None.")
            continue

        # Format row data for prompt
        row_data_str = format_row_for_prompt(row_dict)
        prompt = AUDIT_PROMPT_TEMPLATE.format(
            row_data_str=row_data_str,
            kanjiID=kanji_id,
            kanji=kanji_char
        )

        # Call AI
        ai_response = call_deepseek(prompt)
        report_lines.append(ai_response)
        report_lines.append("")  # Add spacing

        # Be respectful to API rate limits
        time.sleep(1)

    # Save full report
    with open(output_report, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n✅ Audit complete! Report saved to: {output_report}")


# ================================
# MAIN EXECUTION
# ================================
if __name__ == "__main__":
    # audit_csv_file(CSV_FILE_PATH, OUTPUT_REPORT)
    audit_single_row(CSV_FILE_PATH, 10)