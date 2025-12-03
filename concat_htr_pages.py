#!/usr/bin/env python3
import os
import re
from pathlib import Path
from collections import defaultdict

# -------- CONFIG --------
INPUT_DIR = "jpg_handwritten"     # directory containing your *_page_XXX.txt files
OUTPUT_DIR = "combined_txt"
# -----------------------


# match "M 110 s 1-9_page_007.txt" → base="M 110 s 1-9", page="007"
PAGE_RE = re.compile(r"^(.*)_page_(\d{3})\.txt$", re.IGNORECASE)


def main():
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    groups = defaultdict(list)

    # Collect and group pages
    for f in input_dir.iterdir():
        if not f.name.lower().endswith(".txt"):
            continue

        m = PAGE_RE.match(f.name)
        if not m:
            continue

        base = m.group(1)
        page = int(m.group(2))
        groups[base].append((page, f))

    # Combine each group
    for base, items in groups.items():
        # Sort by page number
        items.sort(key=lambda x: x[0])

        out_path = output_dir / f"{base}.txt"
        print(f"Writing {out_path}")

        with out_path.open("w", encoding="utf-8") as out:
            for page_num, path in items:
                text = path.read_text(encoding="utf-8", errors="replace")
                out.write(text.rstrip("\n") + "\n\n")   # keep spacing

    print("Done. Combined files are in:", output_dir)


if __name__ == "__main__":
    main()


