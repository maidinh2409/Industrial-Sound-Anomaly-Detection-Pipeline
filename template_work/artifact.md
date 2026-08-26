# Template execution contract

- Reference: `D:\Download here\Data Analyst Template.docx`
- SHA-256: `048afabb2bbdf17854ad0bc1a56b491cda4c82da26a1639b57d9eca621d3014f`
- Size: 10,679 bytes; one US Letter portrait section.
- Evidence: supplied `D:\Download here\IMG_5247.JPG`; structural inspection via `inspect_resume_docs.py`. Renderer unavailable because LibreOffice is not installed.

## Page system

- US Letter portrait: 12,240 x 15,840 twips.
- Margins: top 0, bottom 450, left/right 1,440 twips; header/footer distance 720 twips.
- Body paragraphs use negative left indents to extend the usable width: title/body -900 twips; entries -720 twips; bullets -270 twips with -270 first-line indent.

## Typography and components

- Times New Roman throughout, black.
- Name: centered, 12 pt, bold, Heading 1, single-spaced.
- Contact: centered, 10 pt.
- Section headings: 10 pt bold uppercase with a thin bottom rule, compact spacing.
- Entry heading: 10 pt, bold item/title on the left; regular date aligned to the right with a right tab.
- Organization/stack line: 10 pt italic.
- Bullets: 10 pt with real bullet numbering, compact single spacing and hanging indent.
- Content flow: name/contact, summary, skills, experience, selected projects, education.

## Slot map and fidelity gates

- Replace all reference body content with the complete text from `Demi_Le_Data_Analyst_Resume.docx`; preserve wording exactly.
- Reuse the reference page geometry, serif typography, section-rule treatment, compact spacing, entry hierarchy, right-aligned dates, italics, and bullet geometry.
- The reference file remains byte-for-byte unchanged.
- Output is a new DOCX in the workspace. No hyperlinks are invented because the current resume contains only visible link labels.
- Structural QA must confirm identical normalized text between the current resume and output, allowing only formatting-driven paragraph/table ordering representation.
