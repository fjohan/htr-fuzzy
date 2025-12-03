#!/usr/bin/env python3
import os
import sys
import csv
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image, ImageTk

# ---------- CONFIG ----------------------------------------------------

THUMB_DPI = 100          # low DPI is fine just for visual inspection
MAX_PAGES = 6            # show up to 6 pages
GRID_ROWS = 2
GRID_COLS = 3
THUMB_MAX_WIDTH = 400    # max size per thumbnail
THUMB_MAX_HEIGHT = 400
OUTPUT_CSV = "manual_classification.csv"

# If you need poppler_path on Windows, set it here, e.g.:
# POPPLER_PATH = r"C:\path\to\poppler\bin"
POPPLER_PATH = None

# ---------------------------------------------------------------------


class PDFManualClassifier:
    def __init__(self, root_dir, output_csv=OUTPUT_CSV):
        self.root_dir = Path(root_dir)
        self.output_csv = Path(output_csv)

        self.pdf_paths = self._collect_pdfs()
        self.classified = self._load_existing_classifications()
        self.current_index = self._find_first_unclassified_index()

        # keep current pages
        self.current_pages = []

        # Tkinter setup
        self.root = tk.Tk()
        self.root.title("PDF Manual Classifier")

        # ---------- Buttons on top ----------
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side="top", pady=10)

        handwritten_btn = tk.Button(
            btn_frame, text="Handwritten (H)",
            command=lambda: self._record_and_next("Handwritten"),
            width=15, height=2
        )
        first_btn = tk.Button(
            btn_frame, text="HWwSheet (F)",
            command=lambda: self._record_and_next("HandwrittenSheet"),
            width=15, height=2
        )
        firstrot_btn = tk.Button(
            btn_frame, text="RotHWwSheet (I)",
            command=lambda: self._record_and_next("HandwrittenRotatedSheet"),
            width=15, height=2
        )
        typed_btn = tk.Button(
            btn_frame, text="Typed (T)",
            command=lambda: self._record_and_next("Typed"),
            width=15, height=2
        )
        skip_btn = tk.Button(
            btn_frame, text="Skip (S / Space)",
            command=lambda: self._record_and_next("Skipped"),
            width=15, height=2
        )
        rotated_btn = tk.Button(
            btn_frame, text="Rotated (R)",
            # Rotated implies handwritten, so we store that explicitly
            command=lambda: self._record_and_next("HandwrittenRotated"),
            width=15, height=2
        )
        quit_btn = tk.Button(
            btn_frame, text="Quit (Q)",
            command=self.root.destroy,
            width=15, height=2
        )

        handwritten_btn.grid(row=0, column=0, padx=5)
        first_btn.grid(row=0, column=1, padx=5)
        firstrot_btn.grid(row=0, column=2, padx=5)
        typed_btn.grid(row=0, column=3, padx=5)
        skip_btn.grid(row=0, column=4, padx=5)
        rotated_btn.grid(row=0, column=5, padx=5)
        quit_btn.grid(row=0, column=6, padx=5)

        # ---------- Info label ----------
        self.info_label = tk.Label(self.root, text="", wraplength=800, justify="left")
        self.info_label.pack(pady=(0, 10))

        # ---------- Images below ----------
        img_frame = tk.Frame(self.root)
        img_frame.pack(padx=10, pady=10)

        self.image_labels = []
        self.image_refs = []  # keep references to PhotoImage to avoid GC

        for r in range(GRID_ROWS):
            row_labels = []
            for c in range(GRID_COLS):
                label = tk.Label(img_frame, text="", borderwidth=1, relief="solid")
                label.grid(row=r, column=c, padx=5, pady=5)
                row_labels.append(label)
            self.image_labels.append(row_labels)

        # ---------- Keyboard shortcuts ----------
        self.root.bind("h", lambda e: self._record_and_next("Handwritten"))
        self.root.bind("H", lambda e: self._record_and_next("Handwritten"))

        self.root.bind("f", lambda e: self._record_and_next("HandwrittenSheet"))
        self.root.bind("F", lambda e: self._record_and_next("HandwrittenSheet"))

        self.root.bind("i", lambda e: self._record_and_next("HandwrittenRotatedSheet"))
        self.root.bind("I", lambda e: self._record_and_next("HandwrittenRotatedSheet"))

        self.root.bind("t", lambda e: self._record_and_next("Typed"))
        self.root.bind("T", lambda e: self._record_and_next("Typed"))

        self.root.bind("s", lambda e: self._record_and_next("Skipped"))
        self.root.bind("S", lambda e: self._record_and_next("Skipped"))
        self.root.bind("<space>", lambda e: self._record_and_next("Skipped"))

        # Rotated = handwritten but rotated
        self.root.bind("r", lambda e: self._record_and_next("HandwrittenRotated"))
        self.root.bind("R", lambda e: self._record_and_next("HandwrittenRotated"))

        self.root.bind("q", lambda e: self.root.destroy())
        self.root.bind("Q", lambda e: self.root.destroy())

        # Load first PDF
        if self.current_index is None:
            messagebox.showinfo("Info", "No unclassified PDFs found.")
            self.root.after(100, self.root.destroy)
        else:
            self._show_current_pdf()

    # ---------- PDF collection & CSV handling -------------------------

    def _collect_pdfs(self):
        pdfs = []
        for dirpath, _, filenames in os.walk(self.root_dir):
            for f in filenames:
                if f.lower().endswith(".pdf"):
                    pdfs.append(Path(dirpath) / f)
        pdfs.sort()
        return pdfs

    def _load_existing_classifications(self):
        classified = {}
        if self.output_csv.exists():
            with self.output_csv.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    pdf_path = row.get("pdf_path")
                    classification = row.get("classification")
                    if pdf_path is not None:
                        classified[pdf_path] = classification
        return classified

    def _find_first_unclassified_index(self):
        for i, p in enumerate(self.pdf_paths):
            if str(p) not in self.classified:
                return i
        return None

    def _append_classification(self, pdf_path, classification):
        file_exists = self.output_csv.exists()
        with self.output_csv.open("a", encoding="utf-8", newline="") as f:
            fieldnames = ["pdf_path", "classification"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "pdf_path": str(pdf_path),
                "classification": classification
            })

    # ---------- UI helpers --------------------------------------------

    def _clear_images(self):
        # Clear labels and references
        self.image_refs = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                self.image_labels[r][c].configure(image="", text="")
                self.image_labels[r][c].image = None

    def _resize_image_for_thumb(self, pil_image):
        w, h = pil_image.size
        scale = min(THUMB_MAX_WIDTH / float(w), THUMB_MAX_HEIGHT / float(h), 1.0)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return pil_image.resize((new_w, new_h), Image.LANCZOS)

    def _render_thumbs_from_pages(self):
        """Render self.current_pages into grid."""
        self._clear_images()
        self.image_refs = []

        idx = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if idx < len(self.current_pages):
                    pil_img = self.current_pages[idx]
                    pil_img = self._resize_image_for_thumb(pil_img)
                    photo = ImageTk.PhotoImage(pil_img)
                    self.image_labels[r][c].configure(image=photo, text="")
                    self.image_labels[r][c].image = photo
                    self.image_refs.append(photo)
                    idx += 1
                else:
                    self.image_labels[r][c].configure(image="", text="")
                    self.image_labels[r][c].image = None

    # ---------- Core logic --------------------------------------------

    def _show_current_pdf(self):
        if self.current_index is None or self.current_index >= len(self.pdf_paths):
            messagebox.showinfo("Done", "No more PDFs to classify.")
            self.root.after(100, self.root.destroy)
            return

        pdf_path = self.pdf_paths[self.current_index]
        self.info_label.config(
            text=f"{self.current_index + 1}/{len(self.pdf_paths)}: {pdf_path}"
        )

        # Auto-skip single-page PDFs
        try:
            info = pdfinfo_from_path(
                str(pdf_path),
                poppler_path=POPPLER_PATH
            )
            num_pages = int(info.get("Pages", 0))
        except Exception:
            num_pages = 0  # if pdfinfo fails, just try rendering

        if num_pages == 1:
            # record auto-skip and move on
            self._append_classification(pdf_path, "AutoSkippedSinglePage")
            self.classified[str(pdf_path)] = "AutoSkippedSinglePage"
            self._move_to_next_unclassified()
            return

        self._clear_images()
        self.current_pages = []

        # Render first pages (we may drop page 1 later if landscape-only cover)
        try:
            if num_pages > 0:
                last_page = min(MAX_PAGES + 1, num_pages)  # +1 so we can still have up to 6 after dropping page 1
            else:
                last_page = MAX_PAGES + 1

            pages = convert_from_path(
                str(pdf_path),
                dpi=THUMB_DPI,
                grayscale=True,
                first_page=1,
                last_page=last_page,
                poppler_path=POPPLER_PATH
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to render PDF:\n{pdf_path}\n\n{e}"
            )
            # Mark as error/skip and move on
            self._append_classification(pdf_path, "Error")
            self.classified[str(pdf_path)] = "Error"
            self._move_to_next_unclassified()
            return

        # Decide whether to skip first page (landscape-only cover)
        # Condition: first page landscape, second page portrait
        if len(pages) >= 2:
            p1, p2 = pages[0], pages[1]
            if p1.width > p1.height and p2.height >= p2.width:
                # Skip first page, keep next up to MAX_PAGES
                pages = pages[1:1 + MAX_PAGES]
            else:
                pages = pages[:MAX_PAGES]
        else:
            pages = pages[:MAX_PAGES]

        self.current_pages = pages
        self._render_thumbs_from_pages()

    def _record_and_next(self, classification):
        if self.current_index is None or self.current_index >= len(self.pdf_paths):
            return
        pdf_path = self.pdf_paths[self.current_index]

        # Save classification
        self._append_classification(pdf_path, classification)
        self.classified[str(pdf_path)] = classification

        # Move to next unclassified pdf
        self._move_to_next_unclassified()

    def _move_to_next_unclassified(self):
        next_index = None
        for i in range(self.current_index + 1, len(self.pdf_paths)):
            if str(self.pdf_paths[i]) not in self.classified:
                next_index = i
                break

        self.current_index = next_index
        if self.current_index is None:
            messagebox.showinfo("Done", "No more PDFs to classify.")
            self.root.after(100, self.root.destroy)
        else:
            self._show_current_pdf()

    # ---------- Public entrypoint -------------------------------------

    def run(self):
        self.root.mainloop()


def main():
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = "."

    app = PDFManualClassifier(root_dir)
    app.run()


if __name__ == "__main__":
    main()


