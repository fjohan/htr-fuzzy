# `htr-fuzzy`
**Tools for aligning handwritten text recognition (HTR) output with manuscript transcriptions.**

This repository contains utilities for:

- Manual PDF inspection and labeling
- Converting handwritten PDFs to page images suitable for HTR processing  
- Merging HTR page outputs into single documents  
- Matching TXT and DOCX files when filenames / metadata do not agree  
- Running fuzzy text alignment between HTR output and reference DOCX transcriptions  

The tools are designed for large collections of handwritten material where:

- Metadata in PDFs and DOCXs is inconsistent  
- Page breaks between HTR output and DOCX transcriptions do *not* correspond  
- Full global alignment is too slow or memory-intensive  
- Local fuzzy search is a more robust and practical alternative

These tools make it possible to align handwritten PDF material with their DOCX transcriptions, even when structure and metadata do not match. This enables the creation of high-quality paired text regions that can be used as training data for continued refinement of HTR systems.

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
**Levenshtein-based approximate string matching**

The script aligns fragmented HTR lines against a continuous DOCX stream without loading the entire text into memory for every search.
To handle varying text densities or large skipped sections, the script runs the alignment multiple times with different **search window sizes** (defined by the user). It automatically selects the "winner" based on the highest number of aligned lines and lowest Global CER.

- **Anchored Sliding Window:** Matches fragmented HTR lines against a continuous DOCX stream using a moving "cursor" to maintain position.
- **Levenshtein-based Fuzzy Search:** Finds the best matching substring within a specific "edit distance" (insertions, deletions, substitutions).
- **Window Optimization:** Runs a "tournament" of different window sizes to maximize the match count.
- **CER Scoring:** Calculates Character Error Rate based on the Levenshtein distance between the HTR line and the matched Reference text.
- **Global Summary:** Aggregates statistics to score the quality of the HTR output.

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

The typical workflow for processing handwritten manuscripts with HTR is:

---

### **1. Determine document type (manual inspection)**  
Inspect the PDF to understand its structure and whether it contains handwritten pages:

```bash
python pdf_manual_viewer.py manuscript.pdf
```

Use this step to identify:

- Whether pages contain handwriting  
- Rotation or orientation issues  
- Pages that should be skipped or flagged before HTR  

---

### **2. Convert PDF → JPEG pages**  
Prepare clean, well-oriented images for the HTR engine:

```bash
python pdf2jpg_handwritten_only.py manuscript.pdf output_images/
```

This step:

- Extracts each page as a JPEG  
- Ensures consistent resolution & formatting for HTR models  

---

### **3. Run HTR (external step)**  
Use your preferred HTR engine (e.g., *htrflow*) on the generated images.  
This produces **one TXT file per page**.

---

### **4. Join HTR page outputs into a single TXT file**

```bash
python concat_htr_pages.py output_images/ combined/M_110.txt
```

This merges page-level TXT files into a continuous transcription suitable for alignment.

---

### **5. Match TXT files to DOCX transcriptions**

```bash
python match_txt_to_docx.py   --txt-dir combined/   --docx-dir transcriptions/   --out txt_docx_matches.csv
```

Since filenames often don’t match perfectly across datasets, this tool:

- Extracts `M_number` identifiers  
- Resolves mismatches  
- Produces a mapping CSV used by the alignment scripts  

Example row:

```
range_dir;M_number;txt_path;docx_path
00001-00500;110;combined/M 110 s 1-9.txt;00001-00500/Transkriberade/wordformat/M110.docx
```

---

### **6. Fuzzy-align HTR output with DOCX text**

```bash
python fuzzysearch_docx.py --index txt_docx_matches.csv --window-lengths '400,1000,5000' --output test.csv --match-output match.csv --verbose
```

This script performs:

- **Fuzzy line-by-line matching** of HTR lines against the DOCX text  
- **CER scoring**, per-line statistics, and global evaluation summary  

Outputs include:

- Best matching substring for each HTR line  
- Edit distance and CER  
- Global CER for the whole document  
- Optional CSV summary  

---

