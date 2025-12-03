#!/usr/bin/env python3
import os
import re
import csv
from pathlib import Path
from collections import defaultdict

# ---------------- CONFIG ----------------
ROOT_DIR = "."                  # where your 00001-00500, 02001-02500, etc live
TXT_DIR = "combined_txt"        # directory with concatenated txt files
OUTPUT_CSV = "txt_docx_matches.csv"

# Regex for M 1, M10, M 100, M2004b ("b" ignored)
M_PATTERN = re.compile(r'\bM\s*(\d{1,4})([A-Za-z]?)\b', re.IGNORECASE)
# ----------------------------------------


def extract_m_number_from_name(name_no_ext):
    """
    Find the M# or M ### pattern inside a filename (without extension).
    Returns numeric part (string) or None.
    """
    m = M_PATTERN.search(name_no_ext)
    if not m:
        return None
    return m.group(1)  # numeric part only


def collect_txts(txt_dir):
    """
    Return dict: M_number -> list of txt relative paths (from ROOT_DIR).
    Assumes txt_dir is relative to ROOT_DIR.
    """
    txt_map = defaultdict(list)
    base = Path(ROOT_DIR)
    txt_base = base / txt_dir

    if not txt_base.exists():
        print("TXT directory not found:", txt_base)
        return txt_map

    for f in txt_base.iterdir():
        if not f.is_file():
            continue
        if not f.name.lower().endswith(".txt"):
            continue

        name_no_ext = f.stem
        m_num = extract_m_number_from_name(name_no_ext)
        if not m_num:
            continue

        rel_path = f.relative_to(base)
        txt_map[m_num].append(str(rel_path))

    return txt_map


def collect_docxs(root_dir):
    """
    Return dict: M_number -> list of (range_dir, docx_rel_path) tuples.
    """
    docx_map = defaultdict(list)
    base = Path(root_dir)

    for dirpath, _, filenames in os.walk(base):
        for fname in filenames:
            if not fname.lower().endswith(".docx"):
                continue

            abs_path = Path(dirpath) / fname
            rel_path = abs_path.relative_to(base)

            parts = rel_path.parts
            if not parts:
                continue
            range_dir = parts[0]

            name_no_ext = abs_path.stem
            m_num = extract_m_number_from_name(name_no_ext)
            if not m_num:
                continue

            docx_map[m_num].append((range_dir, str(rel_path)))

    return docx_map


def main():
    base = Path(ROOT_DIR)

    # 1) Collect txts by M-number
    txt_map = collect_txts(TXT_DIR)
    print("Found txts for M-numbers:", sorted(txt_map.keys()))

    # 2) Collect docxs by M-number
    docx_map = collect_docxs(base)
    print("Found docxs for M-numbers:", sorted(docx_map.keys()))

    # 3) Match by M-number and write CSV
    out_csv = base / OUTPUT_CSV
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["range_dir", "M_number", "txt_path", "docx_path"])

        for m_num in sorted(txt_map.keys(), key=lambda x: int(x)):
            if m_num not in docx_map:
                continue

            txt_paths = txt_map[m_num]
            docx_infos = docx_map[m_num]

            for txt in txt_paths:
                for range_dir, docx in docx_infos:
                    writer.writerow([range_dir, m_num, txt, docx])

    print("Done. Wrote:", out_csv)


if __name__ == "__main__":
    main()


