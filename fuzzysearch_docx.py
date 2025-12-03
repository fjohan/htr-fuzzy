import argparse
import csv
import os
import re
import sys
from docx import Document
from fuzzysearch import find_near_matches
import Levenshtein

# --- Helper Functions ---

def read_docx_text(path):
    """Extracts all text from a docx file into a single string."""
    try:
        doc = Document(path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return " ".join(full_text)
    except Exception as e:
        print(f"Error reading DOCX {path}: {e}")
        return ""

def read_htr_lines(path):
    """Reads HTR text file line by line."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        print(f"Error reading TXT {path}: {e}")
        return []

def normalize_text(text):
    """Normalizes text: lower, remove hyphens, collapse spaces."""
    text = text.lower()
    text = text.replace('-\n', '').replace('- ', '').replace('¬', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Alignment Logic ---

def align_lines(htr_lines, ref_full_text, window_buffer):
    """
    Runs the alignment for a specific window buffer size.
    Returns a list of dictionaries containing match details for every HTR line.
    """
    norm_ref = normalize_text(ref_full_text)
    cursor = 0
    results = []

    for line_idx, raw_htr_line in enumerate(htr_lines):
        norm_htr = normalize_text(raw_htr_line)
        
        # Skip noise
        if len(norm_htr) < 4:
            continue

        # Dynamic Window calculation
        window_size = len(norm_htr) + window_buffer
        end_search = min(cursor + window_size, len(norm_ref))
        search_window = norm_ref[cursor : end_search]

        # Allow approx 20% error rate - 35% is too slow
        #max_dist = int(len(norm_htr) * 0.35)
        max_dist = int(len(norm_htr) * 0.2)

        matches = find_near_matches(norm_htr, search_window, max_l_dist=max_dist)

        if matches:
            # Best match logic
            best_match = sorted(matches, key=lambda m: (m.dist, m.start))[0]
            
            abs_start = cursor + best_match.start
            abs_end = cursor + best_match.end
            
            matched_ref_str = norm_ref[abs_start:abs_end]
            
            # Calculate Local CER for this line
            edits = best_match.dist
            ref_len = len(matched_ref_str)
            local_cer = edits / ref_len if ref_len > 0 else 1.0

            results.append({
                "line_idx": line_idx + 1,
                "status": "MATCH",
                "htr_raw": raw_htr_line,
                "ref_match": matched_ref_str,
                "edits": edits,
                "ref_chars": ref_len,
                "local_cer": local_cer,
                "window_used": window_buffer
            })

            cursor = abs_end
        else:
            results.append({
                "line_idx": line_idx + 1,
                "status": "NO_MATCH",
                "htr_raw": raw_htr_line,
                "ref_match": "",
                "edits": 0,
                "ref_chars": 0,
                "local_cer": 1.0,
                "window_used": window_buffer
            })

    return results

def calculate_stats(match_results, total_htr_lines):
    """Calculates summary stats from a list of match results."""
    matches = [r for r in match_results if r['status'] == "MATCH"]
    
    lines_used = len(matches)
    total_edits = sum(r['edits'] for r in matches)
    total_ref_chars = sum(r['ref_chars'] for r in matches)
    
    global_cer = (total_edits / total_ref_chars) if total_ref_chars > 0 else 0.0

    return {
        "lines_used": lines_used,
        "total_lines": total_htr_lines,
        "global_cer": global_cer,
        "total_edits": total_edits,
        "total_ref_chars": total_ref_chars
    }

# --- Main Controller ---

def main():
    parser = argparse.ArgumentParser(description="Optimize HTR alignment with variable window sizes.")
    parser.add_argument("--index", required=True, help="Path to index CSV.")
    parser.add_argument("--m-number", help="Specific M-number to process.")
    parser.add_argument("--window-lengths", default="400", help="Comma separated list of buffer sizes (e.g. '400,2000').")
    parser.add_argument("--output", help="Path to summary CSV.")
    parser.add_argument("--match-output", help="Path to detailed matches CSV (optional).")
    parser.add_argument("--verbose", action="store_true", help="Print progress.")

    args = parser.parse_args()

    # Parse window lengths
    try:
        window_options = [int(x.strip()) for x in args.window_lengths.split(',')]
    except ValueError:
        print("Error: --window-lengths must be a comma-separated list of integers.")
        sys.exit(1)

    all_summaries = []
    all_detailed_matches = []

    print(f"Reading index: {args.index}")
    print(f"Testing window buffers: {window_options}")

    with open(args.index, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        
        for row in reader:
            m_num = row['M_number'].strip()
            if args.m_number and m_num != args.m_number:
                continue

            txt_path = row['txt_path'].strip()
            docx_path = row['docx_path'].strip()

            if not os.path.exists(txt_path) or not os.path.exists(docx_path):
                if args.verbose: print(f"[M{m_num}] Files missing. Skipping.")
                continue
            
            if args.verbose: print(f"Processing M{m_num}...")

            htr_lines = read_htr_lines(txt_path)
            ref_text = read_docx_text(docx_path)

            if not htr_lines or not ref_text:
                continue

            # --- The Tournament ---
            best_stats = None
            best_results = None
            best_win_len = 0
            
            # We want to maximize matches, then minimize CER
            max_lines_used = -1
            min_cer = 100.0

            for win_len in window_options:
                # Run alignment
                results = align_lines(htr_lines, ref_text, win_len)
                stats = calculate_stats(results, len(htr_lines))
                
                # Check if this is the best result so far
                is_better = False
                if stats['lines_used'] > max_lines_used:
                    is_better = True
                elif stats['lines_used'] == max_lines_used:
                    if stats['global_cer'] < min_cer:
                        is_better = True
                
                if is_better:
                    max_lines_used = stats['lines_used']
                    min_cer = stats['global_cer']
                    best_stats = stats
                    best_results = results
                    best_win_len = win_len

            # --- Store Winner ---
            summary_entry = {
                "m_number": m_num,
                "txt_file": txt_path,
                "docx_file": docx_path,
                "lines_used": best_stats['lines_used'],
                "total_lines": best_stats['total_lines'],
                "global_cer": round(best_stats['global_cer'], 4),
                "total_edits": best_stats['total_edits'],
                "total_ref_chars": best_stats['total_ref_chars'],
                "best_window_len": best_win_len
            }
            all_summaries.append(summary_entry)

            # Store detailed matches if requested
            if args.match_output and best_results:
                for res in best_results:
                    # Add file context to the row
                    res['m_number'] = m_num
                    res['local_cer'] = round(res['local_cer'], 4)
                    all_detailed_matches.append(res)
            
            if args.verbose:
                print(f"  -> Best Window: {best_win_len} | Matches: {max_lines_used}/{len(htr_lines)} | CER: {min_cer:.2%}")

    # --- Write Summary Output ---
    if args.output:
        print(f"Writing summary to {args.output}...")
        summ_cols = ["m_number", "txt_file", "docx_file", "lines_used", "total_lines", 
                     "global_cer", "total_edits", "total_ref_chars", "best_window_len"]
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=summ_cols, delimiter=";")
            w.writeheader()
            w.writerows(all_summaries)

    # --- Write Detailed Match Output ---
    if args.match_output:
        print(f"Writing detailed matches to {args.match_output}...")
        # Columns for detailed view
        detail_cols = ["m_number", "line_idx", "status", "local_cer", "edits", 
                       "ref_chars", "window_used", "htr_raw", "ref_match"]
        with open(args.match_output, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=detail_cols, delimiter=";")
            w.writeheader()
            w.writerows(all_detailed_matches)

    print("Done.")

if __name__ == "__main__":
    main()

