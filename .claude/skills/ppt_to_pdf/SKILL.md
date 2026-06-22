---
name: pdf-figure-crop
description: Crop the top and bottom whitespace from each page of a PDF and save each page as its own separate PDF file. Use this skill whenever the user uploads a multi-page PDF of figures (thesis figures, paper figures, slide exports) and asks to "trim the top and bottom", "remove the whitespace", "split into individual figures", "save each page separately", "fit to figure", or anything equivalent in Korean (e.g. "위아래 잘라줘", "페이지별로 따로 저장", "그림에 맞춰서 잘라줘"). The skill auto-detects the content bounds on each page so the user does NOT need to supply crop coordinates — the horizontal width is preserved and only the vertical whitespace is removed.
---

# PDF Figure Crop

A skill for trimming the top/bottom whitespace from each page of a PDF and exporting each page as a separate PDF.

This is useful when someone has a multi-page PDF where each page is a single figure sitting on a large white canvas (e.g. a thesis figure dump exported from PowerPoint), and they want each figure as its own tightly-cropped PDF — for inserting into LaTeX, sharing individual figures with collaborators, or building a figure repository.

## When to trigger

Trigger this skill whenever **all** of the following are true:
1. The user has uploaded (or referenced) a PDF file.
2. They want per-page output (one PDF per page, not a single merged file).
3. They want the whitespace removed — phrased as "crop", "trim", "fit", "tight crop", "remove blank space", "위아래 잘라줘", "여백 제거", or similar.

Do NOT use this skill if the user wants to:
- Extract text or tables (use the `pdf` skill)
- Merge multiple PDFs into one
- Crop sides (left/right) as well — this skill preserves horizontal width by design. If they need full bounding-box crop, modify `crop_left_right=True` in the script.

## How it works

1. Open the PDF with PyMuPDF (`fitz`).
2. For each page, render to a 150 DPI grayscale image and find which rows contain non-white pixels (threshold: pixel value < 245, at least 3 non-white pixels per row).
3. The first and last "content rows" define the vertical content bounds. Add a small padding (default 12 pt).
4. Use `show_pdf_page(..., clip=crop_rect)` to copy that vertical slice into a new single-page PDF. This preserves vector content perfectly — no rasterization.
5. Save each page as `figure_page_NN.pdf` in the output directory.

## Usage

The full working script is at `scripts/crop_figures.py`. To run it:

```bash
pip install pymupdf pillow numpy --break-system-packages -q
python scripts/crop_figures.py <input.pdf> <output_dir>
```

If invoked without arguments, defaults are:
- input: `/mnt/user-data/uploads/figures_master_thesis.pdf`
- output: `/mnt/user-data/outputs/`

After running, present the resulting PDFs to the user with the `present_files` tool, in page order.

## Tunable parameters

Inside `scripts/crop_figures.py` there are three knobs to tweak based on user feedback:

| Parameter | Default | What it does |
|---|---|---|
| `WHITE_THRESHOLD` | 245 | Pixel grayscale value below which a pixel is considered "content". Lower → only darker pixels count (ignores very light backgrounds). Raise to 250 if the figure has off-white backgrounds being treated as content. |
| `MIN_CONTENT_PIXELS` | 3 | A row needs at least this many non-white pixels to count as content. Raise (e.g. to 10) to ignore stray dots or scanning noise. |
| `PADDING` | 12 (pt) | Whitespace kept around the detected content, in PDF points (1 pt = 1/72 inch). Increase if crops feel too tight, decrease for tighter crops. |

If the user says "조금 더 여유있게" / "more padding", increase `PADDING` to 20–30. If they say "더 타이트하게" / "tighter", drop it to 4–6.

## Edge cases

- **Multi-figure pages** (two figures with whitespace between them): the script keeps everything from the topmost content row to the bottom-most one, so both figures are retained in one PDF. This is usually what users want. To split them into separate PDFs, you'd need to detect interior gaps — not implemented here.
- **Blank pages**: the script prints a "no content detected, skipping" message and produces no output for that page.
- **Pages where content extends edge-to-edge vertically**: no cropping happens (the bounds are already at 0 and page_h). The output PDF will be the full page.
- **Already-cropped pages**: harmless; just produces a near-identical PDF.

## After running

Always call `present_files` with the output PDFs in page order so the user can preview/download them. Mention the page-by-page crop dimensions only if they ask — by default keep the message short.
