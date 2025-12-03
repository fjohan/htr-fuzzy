#!/usr/bin/env python3
import csv
from pathlib import Path

from pdf2image import convert_from_path

# ---------- CONFIG ----------------------------------------------------

ROOT_DIR = "."  # base directory where your 00001-00500, 02001-02500, ... live
CLASS_CSV = "manual_classification.csv"
OUTPUT_SUBDIR = "jpg_handwritten"   # created next to each PDF

DPI = 300
JPEG_QUALITY = 95
# ---------------------------------------------------------------------


def load_handwritten_pdfs(csv_path):
    """
    Read manual_classification.csv and return a set of pdf paths (relative)
    whose classification is exactly 'Handwritten'.
    """
    csv_path = Path(csv_path)
    handwritten = set()

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")

        for row in reader:
            if not row or len(row) < 2:
                continue

            pdf_path = row[0].strip()
            classification = row[1].strip()

            # Only process EXACT Handwritten
            if classification == "Handwritten":
                handwritten.add(pdf_path)

    return handwritten


def convert_pdf_to_jpgs(pdf_path, output_dir):
    """
    Convert a PDF to JPEG pages in output_dir.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = convert_from_path(str(pdf_path), dpi=DPI, fmt="jpeg", grayscale=True)

    for i, page in enumerate(pages, start=1):
        out_file = output_dir / f"{pdf_path.stem}_page_{i:03d}.jpg"
        page.save(out_file, "JPEG", quality=JPEG_QUALITY)
        print("Saved:", out_file)


def main():
    root = Path(ROOT_DIR)
    csv_file = root / CLASS_CSV

    if not csv_file.exists():
        print("Classification file not found:", csv_file)
        return

    handwritten_rel_paths = load_handwritten_pdfs(csv_file)
    print(f"Found {len(handwritten_rel_paths)} handwritten PDFs in CSV")

    for rel in sorted(handwritten_rel_paths):
        pdf_path = root / rel
        if not pdf_path.exists():
            print("WARNING: PDF from CSV not found on disk:", pdf_path)
            continue

        print("Processing:", pdf_path)
        outdir = pdf_path.parent / OUTPUT_SUBDIR
        try:
            convert_pdf_to_jpgs(pdf_path, outdir)
        except Exception as e:
            print("ERROR converting", pdf_path, "->", e)


if __name__ == "__main__":
    main()
