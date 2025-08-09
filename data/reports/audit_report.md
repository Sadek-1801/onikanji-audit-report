# OniKanji Flashcard Audit Report

This report audits each row for formatting, naturalness, furigana, multiple choice, and consistency.

### Row 11: 学
**Issues:**
- In `onyomiVocabWordTwo` and `onyomiVocabWordThree`, the furigana syntax is incorrect (should be `//` delimiters, not `//こう//`).
- `onyomiMultipleChoiceReadingFour` to `onyomiMultipleChoiceReadingSix` should be removed or filled to maintain consistency with the 4-option rule.
- The furigana for sample sentences is provided in a dictionary format, but the audit rules specify it should be in `漢字//よみ//` format.

**Fixes:**
- Correct `onyomiVocabWordTwo` to `学校//がっこう//` and `onyomiVocabWordThree` to `中学校//ちゅうがっこう//`.
- Remove `onyomiMultipleChoiceReadingFour` to `onyomiMultipleChoiceReadingSix` or fill them with plausible distractors to ensure exactly 4 options.
- Convert furigana in sample sentences to the correct format (e.g., `学生//がくせい//は大変//たいへん//だな。`).

**Note:** The rest of the entry is accurate and follows the rules. The fixes are minor and primarily involve formatting and consistency.
