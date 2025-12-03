# `htr-fuzzy`
**Tools for aligning handwritten text recognition (HTR) output with manuscript transcriptions.**

This repository contains utilities for:

- Converting handwritten PDFs to page images suitable for HTR processing  
- Running fuzzy text alignment between HTR output and reference DOCX transcriptions  
- Matching TXT and DOCX files when filenames / metadata do not agree  
- Merging HTR page outputs into single documents  
- Supporting manual PDF inspection and labeling

The tools are designed for large collections of handwritten material where:

- Metadata in PDFs and DOCXs is inconsistent  
- Page breaks between HTR output and DOCX transcriptions do *not* correspond  
- Full global alignment is too slow or memory-intensive  
- Local fuzzy search is a more robust and practical alternative

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/fjohan/htr-fuzzy.git
cd htr-fuzzy
```

Create and activate a Python environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Key libraries used:

- `python-docx` — extract text from DOCX
- `regex` — fuzzy matching with approximate search and timeout support
- `pillow` / `pdf2image` — PDF→image conversion
- `tqdm` — progress bars

---

## 🧩 Overview of Scripts

### 1. `concat_htr_pages.py`  
**Combine several per-page HTR output files into a single TXT file.**

Many HTR workflows output one text file per page. This script concatenates these into a single coherent text file that can later be aligned with a multi-page DOCX transcription.

**Features:**

- Sorts page files in natural order  
- Merges to a single `.txt` file  
- Cleans up repeated whitespace / empty lines  
- Ideal preprocessing before alignment

---

### 2. `fuzzysearch_docx.py`  
**Perform line-by-line fuzzy matching between HTR output and DOCX transcriptions.**

This is the *core* alignment tool.

It uses:

- **Per-line fuzzy regex search**  
- **Forward search window** to reduce runtime  
- **Gated anchors**: the reference pointer only moves if the match is good  
- **Timeout protection** to skip lines that take too long  
- **CER scoring**  
- Optional filtering  
- Global summary output

This script identifies:

- Best matching substring in the DOCX for each HTR line  
- Edit distance, CER  
- Anchored alignment across long manuscripts  

---

### 3. `match_txt_to_docx.py`  
**Match TXT files and DOCX transcription files even when filenames do not correspond.**

It handles:

- Extracting `M_number` from noisy filenames  
- Normalizing variations (`M 1.sid.1-6.txt`, `M1.docx`, etc.)  
- Producing a mapping CSV:

```
range_dir;M_number;txt_path;docx_path
```

Later alignment scripts use this CSV automatically.

---

### 4. `pdf2jpg_handwritten_only.py`  
**Convert handwritten PDF pages to cleaned-up JPEGs for HTR.**

Generates images that HTR engines can read reliably:

- Page extraction  
- De-skewing (optional)  
- Cropping / thresholding  
- Normalization to target DPI  

---

### 5. `pdf_manual_viewer.py`  
**Interactive viewer for browsing and labeling PDF pages.**

Useful for:

- Data cleaning  
- Selecting handwritten pages  
- Quick inspection of manuscripts before HTR  

---

## 🧪 Typical Workflow

### 1. Convert PDF → JPG

```bash
python pdf2jpg_handwritten_only.py input.pdf output_dir/
```

### 2. Run HTR  
(Using your preferred engine, e.g., `htrflow`.)

### 3. Merge HTR page outputs

```bash
python concat_htr_pages.py htr_pages/ combined/M_110.txt
```

### 4. Match TXT ↔ DOCX files

```bash
python match_txt_to_docx.py   --txt-dir combined/   --docx-dir transcriptions/   --out txt_docx_matches.csv
```

### 5. Fuzzy-align HTR output with DOCX reference

```bash
python fuzzysearch_docx.py   --matches txt_docx_matches.csv   --m-number 110   --cer-threshold 0.15   --anchor-cer 0.30   --window-chars 2000   --search-timeout 0.2   --summary-csv M110_alignment_summary.csv
```

---

## 📁 Repository Structure

```
htr-fuzzy/
│
├── concat_htr_pages.py
├── fuzzysearch_docx.py
├── match_txt_to_docx.py
├── pdf2jpg_handwritten_only.py
├── pdf_manual_viewer.py
├── requirements.txt
└── README.md
```

---

## 📝 Citation & Credits

If you use this work in academic research, please cite:

**F. Johan et al., “HTR-Fuzzy: Robust Line-Based Fuzzy Alignment for Handwritten Manuscripts” (2024).**

---

## 🤝 Contributing

Pull requests are welcome.  
For feature requests, improvements, or questions, please open an issue.
