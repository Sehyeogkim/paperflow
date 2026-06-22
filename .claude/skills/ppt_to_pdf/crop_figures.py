"""
crop_figures.py
---------------
Crop top/bottom whitespace from each page of a PDF, saving each page as a
separate PDF file.

The horizontal width of each page is preserved exactly — only the vertical
whitespace is trimmed. Vector content is preserved (no rasterization of the
output) by using PyMuPDF's `show_pdf_page` with a clip rectangle.

Usage:
    python crop_figures.py <input.pdf> <output_dir>

If run without arguments, defaults are:
    input  = /mnt/user-data/uploads/figures_master_thesis.pdf
    output = /mnt/user-data/outputs/

Dependencies:
    pip install pymupdf pillow numpy
"""

import io
import os
import sys

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

# --- Tunable parameters --------------------------------------------------
# Pixel grayscale value (0=black, 255=white) below which a pixel counts as
# "content". Lower → stricter (ignores light backgrounds).
WHITE_THRESHOLD = 245

# Minimum number of non-white pixels in a row for the row to count as
# containing content. Raise to ignore stray dots / scanning noise.
MIN_CONTENT_PIXELS = 3

# Padding (in PDF points; 1 pt = 1/72 inch) kept around detected content.
PADDING = 12

# DPI at which to rasterize for content detection. Higher = more accurate
# bounds but slower. 150 is a good balance.
DETECT_DPI = 150
# -------------------------------------------------------------------------


def crop_pdf_pages(src_path: str, out_dir: str) -> list[str]:
    """Crop top/bottom whitespace from each page of src_path.

    Returns the list of output PDF paths in page order.
    """
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(src_path)
    output_paths: list[str] = []

    print(f"Opened: {src_path}  ({len(doc)} pages)")

    for i, page in enumerate(doc):
        page_num = i + 1
        rect = page.rect  # PDF points
        page_w, page_h = rect.width, rect.height

        # 1. Render page at DETECT_DPI and convert to grayscale array
        zoom = DETECT_DPI / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        arr = np.array(img)  # shape (H, W), 0=black, 255=white

        # 2. For each row, count non-white pixels; find first/last content row
        non_white_per_row = (arr < WHITE_THRESHOLD).sum(axis=1)
        content_rows = np.where(non_white_per_row >= MIN_CONTENT_PIXELS)[0]

        if len(content_rows) == 0:
            print(f"  page {page_num:02d}: no content detected, skipping")
            continue

        top_px, bottom_px = content_rows[0], content_rows[-1]

        # 3. Convert pixel rows back to PDF points and apply padding
        px_to_pt = 72 / DETECT_DPI
        new_y0 = max(0, top_px * px_to_pt - PADDING)
        new_y1 = min(page_h, bottom_px * px_to_pt + PADDING)

        # 4. Build crop rect (full width, cropped top/bottom)
        crop_rect = fitz.Rect(rect.x0, new_y0, rect.x1, new_y1)

        # 5. Place clipped page content into a new single-page PDF
        new_doc = fitz.open()
        new_page = new_doc.new_page(width=crop_rect.width, height=crop_rect.height)
        new_page.show_pdf_page(new_page.rect, doc, i, clip=crop_rect)

        out_path = os.path.join(out_dir, f"figure_page_{page_num:02d}.pdf")
        new_doc.save(out_path)
        new_doc.close()
        output_paths.append(out_path)

        print(
            f"  page {page_num:02d}: y={new_y0:6.1f}-{new_y1:6.1f} "
            f"(of 0-{page_h:.1f})  -> {out_path}"
        )

    doc.close()
    print(f"\nDone. {len(output_paths)} PDF(s) written to {out_dir}")
    return output_paths


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        src = sys.argv[1]
        out = sys.argv[2]
    else:
        # Defaults — convenient when running inside the Claude sandbox
        src = "/mnt/user-data/uploads/figures_master_thesis.pdf"
        out = "/mnt/user-data/outputs"
        print("(no args given, using defaults)")

    crop_pdf_pages(src, out)
