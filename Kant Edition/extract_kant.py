#!/usr/bin/env python3
"""
Extract Kant text from 'Kant im Kontext III' PDF (Komplettausgabe 2017).
Uses get_text('dict') to preserve bold (Sperrsatz) and italic formatting.
Produces per-page JSON files organized by AA volume.

Usage:
    python3 extract_kant.py [--volume aa-III] [--all]
"""

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
AA_VOLUMES = {
    "aa-I": {
        "title": "Vorkritische Schriften I (1747–1756)",
        "pdf_start": 214, "pdf_end": 588, "aa_band": "I",
    },
    "aa-II": {
        "title": "Vorkritische Schriften II (1757–1777)",
        "pdf_start": 589, "pdf_end": 998, "aa_band": "II",
    },
    "aa-III": {
        "title": "Kritik der reinen Vernunft (B 1787)",
        "pdf_start": 1000, "pdf_end": 1384, "aa_band": "III",
    },
    "aa-III-A": {
        "title": "Kritik der reinen Vernunft — Anhang (A 1781)",
        "pdf_start": 1385, "pdf_end": 1443, "aa_band": "III",
    },
    "aa-IV-prolegomena": {
        "title": "Prolegomena zu einer jeden künftigen Metaphysik (1783)",
        "pdf_start": 1444, "pdf_end": 1533, "aa_band": "IV",
    },
    "aa-IV-grundlegung": {
        "title": "Grundlegung zur Metaphysik der Sitten (1785)",
        "pdf_start": 1534, "pdf_end": 1586, "aa_band": "IV",
    },
    "aa-IV-man": {
        "title": "Metaphysische Anfangsgründe der Naturwissenschaft (1786)",
        "pdf_start": 1587, "pdf_end": 1652, "aa_band": "IV",
    },
    "aa-V-kpv": {
        "title": "Kritik der praktischen Vernunft (1788)",
        "pdf_start": 1653, "pdf_end": 1765, "aa_band": "V",
    },
    "aa-V-kdu": {
        "title": "Kritik der Urtheilskraft (1790)",
        "pdf_start": 1766, "pdf_end": 2003, "aa_band": "V",
    },
    "aa-VI-religion": {
        "title": "Die Religion innerhalb der Grenzen der bloßen Vernunft (1793)",
        "pdf_start": 2048, "pdf_end": 2185, "aa_band": "VI",
    },
    "aa-VI-mds": {
        "title": "Die Metaphysik der Sitten (1797)",
        "pdf_start": 2219, "pdf_end": 2483, "aa_band": "VI",
    },
    "aa-VII-streit": {
        "title": "Der Streit der Facultäten (1798)",
        "pdf_start": 2484, "pdf_end": 2567, "aa_band": "VII",
    },
    "aa-VII-anthropologie": {
        "title": "Anthropologie in pragmatischer Hinsicht (1798)",
        "pdf_start": 2568, "pdf_end": 2725, "aa_band": "VII",
    },
    "aa-VIII-entdeckung": {
        "title": "Über eine Entdeckung (1790)",
        "pdf_start": 2004, "pdf_end": 2047, "aa_band": "VIII",
    },
    "aa-VIII-frieden": {
        "title": "Zum ewigen Frieden (1795)",
        "pdf_start": 2186, "pdf_end": 2218, "aa_band": "VIII",
    },
    "aa-IX-logik": {
        "title": "Logik (1800)",
        "pdf_start": 2726, "pdf_end": 2820, "aa_band": "IX",
    },
    "aa-IX-geographie": {
        "title": "Physische Geographie (1802)",
        "pdf_start": 2821, "pdf_end": 2996, "aa_band": "IX",
    },
    "aa-IX-paedagogik": {
        "title": "Pädagogik (1803)",
        "pdf_start": 2997, "pdf_end": 3033, "aa_band": "IX",
    },
    "aa-VIII-kleine-schriften": {
        "title": "Kleine Schriften (1782–1800)",
        "pdf_start": 3093, "pdf_end": 3263, "aa_band": "VIII",
    },
}

# Regex
RE_SEITE = re.compile(r"Seite:\s*(\d+)")
RE_B_PAGE = re.compile(r"^(B\s*(?:III|II|IV|IX|VIII|VII|VI|V|X{0,3}(?:IX|IV|V?I{0,3})|[XLCDM]*|\d+))\s*R?\s*$")
RE_A_PAGE = re.compile(r"^(A\s*(?:III|II|IV|IX|VIII|VII|VI|V|X{0,3}(?:IX|IV|V?I{0,3})|[XLCDM]*|\d+))\s*R?\s*$")
RE_AA_PAGE = re.compile(r"^(VIII|VII|VI|IV|IX|V|III|II|I)(\d+)\s*R?\s*$")
RE_B_MARKER_INLINE = re.compile(r"//B(\d+[A-Z]?)//?")
RE_WORM_NOTE = re.compile(r"^°+\s")
RE_EDITORIAL = re.compile(r"°+")

HEADER_FONT = "Arial"
BODY_SIZE_NORMAL = 11.0
BODY_SIZE_SMALL = 10.0
TITLE_SIZE_LARGE = 14.0


def extract_formatted_text(page: fitz.Page) -> list[dict]:
    """Extract text with formatting from a page using dict mode.
    Returns list of lines, each with text and formatting info."""
    blocks = page.get_text("dict")["blocks"]
    lines_out = []

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            parts = []
            line_is_header = False
            for span in line["spans"]:
                font = span["font"]
                flags = span["flags"]
                size = round(span["size"], 1)
                text = span["text"]

                if not text.strip():
                    parts.append({"text": text, "fmt": "plain"})
                    continue

                # Skip KiK metadata header (Arial font)
                if HEADER_FONT in font:
                    line_is_header = True
                    break

                is_bold = bool(flags & 16)
                is_italic = bool(flags & 2)
                is_large = size >= TITLE_SIZE_LARGE
                is_heading_size = size >= BODY_SIZE_NORMAL and is_bold

                if is_large:
                    fmt = "title"
                elif is_heading_size:
                    fmt = "bold"
                elif is_bold and size <= BODY_SIZE_SMALL:
                    fmt = "sperrsatz"
                elif is_italic:
                    fmt = "italic"
                elif size <= 8.0:
                    fmt = "small"
                else:
                    fmt = "plain"

                parts.append({"text": text, "fmt": fmt})

            if line_is_header:
                continue
            if parts:
                lines_out.append(parts)

    return lines_out


def format_line_text(parts: list[dict]) -> tuple[str, set]:
    """Convert parts to formatted text string with *Sperrsatz* and _italic_ markers.
    Returns (text, set_of_formats_used)."""
    result = []
    formats_used = set()
    in_sperr = False
    in_italic = False

    for p in parts:
        text = p["text"]
        fmt = p["fmt"]

        if fmt == "sperrsatz":
            formats_used.add("sperrsatz")
            if not in_sperr:
                result.append("*")
                in_sperr = True
            if in_italic:
                result.append("_")
                in_italic = False
        elif fmt == "italic":
            formats_used.add("italic")
            if not in_italic:
                if in_sperr:
                    result.append("*")
                    in_sperr = False
                result.append("_")
                in_italic = True
        else:
            if in_sperr:
                result.append("*")
                in_sperr = False
            if in_italic:
                result.append("_")
                in_italic = False

        formats_used.add(fmt)
        result.append(text)

    if in_sperr:
        result.append("*")
    if in_italic:
        result.append("_")

    return "".join(result), formats_used


def classify_line(parts: list[dict]) -> str:
    """Classify a line based on its formatting."""
    if not parts:
        return "empty"
    non_empty = [p for p in parts if p["text"].strip()]
    if not non_empty:
        return "empty"

    # All bold at heading size → heading
    all_bold = all(p["fmt"] in ("bold", "title", "small", "plain")
                   and (p["fmt"] == "bold" or p["fmt"] == "title" or not p["text"].strip())
                   for p in non_empty)
    if all_bold and any(p["fmt"] in ("bold", "title") for p in non_empty):
        return "heading"

    # Mostly bold (title + trailing year/annotation) → heading
    bold_len = sum(len(p["text"]) for p in non_empty if p["fmt"] in ("bold", "title"))
    total_len = sum(len(p["text"]) for p in non_empty)
    if bold_len > 0 and non_empty[0]["fmt"] in ("bold", "title") and bold_len >= total_len * 0.5:
        return "heading"

    # Check for page markers
    full_text = "".join(p["text"] for p in parts).strip()
    if RE_B_PAGE.match(full_text) or RE_A_PAGE.match(full_text) or RE_AA_PAGE.match(full_text):
        return "marker"

    # Small text only → could be a page number or footnote marker
    if all(p["fmt"] == "small" for p in non_empty):
        return "small"

    return "body"


def clean_text(text: str) -> str:
    text = RE_B_MARKER_INLINE.sub("", text)
    text = text.replace("||", "|")
    text = text.replace("|", "")
    text = RE_EDITORIAL.sub("", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def extract_page(doc: fitz.Document, pdf_page: int) -> dict:
    page = doc[pdf_page]

    # Get the plain text for metadata parsing (header lines)
    raw_text = page.get_text()
    raw_lines = raw_text.split("\n")

    # Parse KiK metadata from first 3 lines
    title_line = raw_lines[0].strip() if len(raw_lines) > 0 else ""
    viewlit_line = raw_lines[2].strip() if len(raw_lines) > 2 else ""
    seite_m = RE_SEITE.search(viewlit_line)
    seite = int(seite_m.group(1)) if seite_m else None

    # Get formatted lines (with KiK headers already filtered)
    fmt_lines = extract_formatted_text(page)

    # Classify page
    tl = title_line.lower()
    if "titelseite" in tl:
        page_kind = "title_page"
    elif not fmt_lines or all(classify_line(l) == "empty" for l in fmt_lines):
        page_kind = "blank"
    elif "vorwort" in tl or "vorrede" in tl:
        page_kind = "body"
    elif "leitwort" in tl or "widmung" in tl or "zueignung" in tl:
        page_kind = "frontmatter"
    else:
        page_kind = "body"

    # Process lines into paragraphs
    paragraphs = []
    page_markers = []
    has_editorial = False
    current_para_lines = []
    current_para_kind = "paragraph"

    def flush():
        nonlocal current_para_lines, current_para_kind
        if not current_para_lines:
            return
        joined = " ".join(current_para_lines)
        cleaned = clean_text(joined)
        if not cleaned:
            current_para_lines = []
            return

        para = {"kind": current_para_kind, "text": cleaned}
        if current_para_kind == "heading":
            # Determine level
            low = cleaned.lower()
            if any(w in low for w in ["hauptstück", "abtheilung", "theil", "buch"]):
                para["level"] = 1
            elif any(w in low for w in ["abschnitt", "kapitel"]):
                para["level"] = 2
            elif cleaned.startswith("§"):
                para["level"] = 3
            else:
                para["level"] = 2
        paragraphs.append(para)
        current_para_lines = []
        current_para_kind = "paragraph"

    for fmt_line in fmt_lines:
        line_type = classify_line(fmt_line)
        full_text = "".join(p["text"] for p in fmt_line).strip()

        if line_type == "empty":
            flush()
            continue

        if line_type == "marker":
            bm = RE_B_PAGE.match(full_text)
            if bm:
                page_markers.append({"system": "B", "ref": bm.group(1).replace(" ", "")})
                continue
            am = RE_A_PAGE.match(full_text)
            if am:
                page_markers.append({"system": "A", "ref": am.group(1).replace(" ", "")})
                continue
            aam = RE_AA_PAGE.match(full_text)
            if aam:
                band = aam.group(1)
                page_num = int(aam.group(2))
                page_markers.append({"system": "AA", "band": band, "page": page_num, "ref": f"{band}{page_num}"})
                continue

        # Check for Worm editorial notes
        if RE_WORM_NOTE.match(full_text):
            has_editorial = True
            continue

        # Check for inline B-markers
        for inline_m in RE_B_MARKER_INLINE.finditer(full_text):
            page_markers.append({"system": "B", "ref": f"B{inline_m.group(1)}"})

        # Format text with markers
        formatted_text, fmts_used = format_line_text(fmt_line)
        formatted_text = formatted_text.strip()

        if not formatted_text:
            continue

        if line_type == "heading":
            flush()
            current_para_kind = "heading"
            current_para_lines.append(formatted_text)
            flush()
            continue

        if line_type == "small":
            # Footnote markers, page numbers — skip standalone small text
            if len(full_text) < 5:
                continue

        current_para_lines.append(formatted_text)

    flush()

    return {
        "page_pdf": pdf_page,
        "page_kik": seite,
        "page_book": None,
        "page_kind": page_kind,
        "running_header": title_line if page_kind == "body" else None,
        "paragraphs": paragraphs,
        "page_markers": page_markers,
        "has_editorial_notes": has_editorial,
        "notes": None,
    }


def extract_volume(pdf_path: str, volume_id: str, out_dir: Path,
                   start: int | None = None, end: int | None = None):
    vol = AA_VOLUMES.get(volume_id)
    if not vol:
        print(f"Unknown volume: {volume_id}")
        sys.exit(1)

    pdf_start = start if start is not None else vol["pdf_start"]
    pdf_end = end if end is not None else vol["pdf_end"]

    doc = fitz.open(pdf_path)
    if pdf_end is None:
        pdf_end = doc.page_count - 1

    out_dir.mkdir(parents=True, exist_ok=True)

    total = pdf_end - pdf_start + 1
    print(f"Extracting {volume_id}: PDF pages {pdf_start}–{pdf_end} ({total} pages)")

    for pdf_page in range(pdf_start, pdf_end + 1):
        page_data = extract_page(doc, pdf_page)
        page_num = pdf_page - pdf_start + 1
        out_file = out_dir / f"page_{page_num:04d}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)

        if (pdf_page - pdf_start) % 50 == 0:
            markers = [m["ref"] for m in page_data["page_markers"]]
            sperr_count = sum(1 for p in page_data["paragraphs"] if "*" in p.get("text", ""))
            ital_count = sum(1 for p in page_data["paragraphs"] if "_" in p.get("text", ""))
            heads = sum(1 for p in page_data["paragraphs"] if p["kind"] == "heading")
            marker_str = f" markers={markers}" if markers else ""
            fmt_str = f" sperr={sperr_count} ital={ital_count} heads={heads}"
            print(f"  page {page_num:4d} (PDF {pdf_page}) — "
                  f"KiK {page_data['page_kik']}, {page_data['page_kind']}"
                  f"{marker_str}{fmt_str}")

    doc.close()
    print(f"Done. {total} pages written to {out_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Extract Kant text from KiK PDF")
    parser.add_argument("--pdf", default="/Users/giulianoinfantino/Downloads/Kant im Kontext.pdf")
    parser.add_argument("--volume", default=None)
    parser.add_argument("--all", action="store_true", help="Extract all volumes")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    base = Path(__file__).parent

    if args.all:
        for vol_id in AA_VOLUMES:
            out_dir = base / "ocr" / vol_id
            extract_volume(args.pdf, vol_id, out_dir)
        return

    vol_id = args.volume or "aa-III"
    out_dir = Path(args.out) if args.out else base / "ocr" / vol_id
    extract_volume(args.pdf, vol_id, out_dir, args.start, args.end)


if __name__ == "__main__":
    main()
