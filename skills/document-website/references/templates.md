# Templates and reference documents

Ask the user at the start: is there a template or a reference document to follow? They are different things.

- **Template:** a `.docx` or `.dotx` the tutorial is built inside. Pass it as `--template <file>`; styles, page setup, headers, and footers carry over. Use it when the user wants the result to open in their own Word styles.
- **Reference:** an existing document (`.docx` or `.pdf`) whose look and wording the tutorial should resemble. Nothing is copied automatically. You read it, then reproduce its look with a style file and its structure with `steps.json`.

When the user hands over a `.docx` and the output is `.docx` or `.pdf`, prefer `--template`: it matches exactly. Use a reference when the output is `.html`, when the file is a PDF, or when the user wants "something like this".

## Read the reference

- **`.pdf`:** read it with your own PDF reading (open the pages and look). Note the fonts, heading sizes and colors, page size, margins, and how each section is worded.
- **`.docx` or `.dotx`:** run
  ```bash
  python3 <skill-dir>/scripts/describe_docx.py <file>
  ```
  It prints the page size and margins, header and footer text, each paragraph style in use with its font, size, color, bold, and italic (`-` means unset), an outline of the title and headings, and image and table counts. Exit `2` means the file is missing or not a Word document.

## Turn it into a style file

Write a style file (see `style-file.md`) whose `document` section matches what you saw:

- `Normal` font, size, and color become `document.font`, `font_size`, and `color`.
- `Title` becomes `document.title` (`font`, `size`, `color`, `bold`, `align`).
- `Heading 2` becomes `document.heading`; captions become `document.caption`.
- Page size (`letter` or `a4`) becomes `document.page.size`, and the margins in inches become `document.page.margins_in`.

Pass it with `--style`. When the build uses `--template` instead, page settings come from the template, and `document.page` is ignored with a `[warn]`. The same file styles `.html` output, and `.pdf` output made by Chrome.

## Mirror the structure and voice

Copy the reference's shape into `steps.json`:

- An introduction step with a heading and body but no `image`, when the reference opens with an overview.
- A prerequisites step (accounts, permissions, links) when the reference has one.
- One step per task, worded in the reference's voice: person, tense, and length of sentences.
- A troubleshooting or help step at the end when the reference closes that way.

Keep the reference's heading pattern (`Step 1: ...` or plain names).

## PDF output notes

Word and LibreOffice convert the `.docx` build, so `--template` and `--style` apply. Chrome prints the HTML build, so `--style` and `--css` apply but `--template` does not. If the user wants a PDF that matches a Word template, use Word or LibreOffice (`--pdf-engine word` or `libreoffice`). Never make a PDF unless the user asks for one.
