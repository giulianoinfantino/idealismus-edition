#!/usr/bin/env python3
"""
Build the Digitale Kant-Edition site from per-page JSON files.
Produces: edition-data.js, work-*.js, search-data.js in the site assets/ folder.

Usage:
    python3 build_site.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
OCR_DIR = BASE / "ocr"
SITE_DIR = BASE / "digitalekantedition" / "assets"

# Volume definitions: (vol_id, ocr_subdir, aa_band, title, siglum, citation_systems)
VOLUMES = [
    # AA Bd. I–II: Vorkritische Schriften
    {"work_id": "aa-I", "ocr_dir": "aa-I", "aa_band": "I",
     "title": "Vorkritische Schriften I (1747–1756)", "short_title": "Vorkrit. Schriften I",
     "siglum": "AA I", "series": "AA", "band": "I",
     "citation_systems": ["AA"], "citation_prefix": "AA I"},
    {"work_id": "aa-II", "ocr_dir": "aa-II", "aa_band": "II",
     "title": "Vorkritische Schriften II (1757–1777)", "short_title": "Vorkrit. Schriften II",
     "siglum": "AA II", "series": "AA", "band": "II",
     "citation_systems": ["AA"], "citation_prefix": "AA II"},
    # AA Bd. III: KrV
    {"work_id": "aa-III", "ocr_dir": "aa-III", "aa_band": "III",
     "title": "Kritik der reinen Vernunft (B 1787)", "short_title": "Kritik der reinen Vernunft (B)",
     "siglum": "KrV", "series": "AA", "band": "III",
     "citation_systems": ["B", "A"], "citation_prefix": "KrV"},
    {"work_id": "aa-III-A", "ocr_dir": "aa-III-A", "aa_band": "III",
     "title": "Kritik der reinen Vernunft — Anhang (A 1781)", "short_title": "KrV Anhang (A)",
     "siglum": "KrV", "series": "AA", "band": "III-A",
     "citation_systems": ["A"], "citation_prefix": "KrV"},
    # AA Bd. IV: Prolegomena, Grundlegung, MAN
    {"work_id": "aa-IV-prolegomena", "ocr_dir": "aa-IV-prolegomena", "aa_band": "IV",
     "title": "Prolegomena zu einer jeden künftigen Metaphysik (1783)", "short_title": "Prolegomena",
     "siglum": "AA IV", "series": "AA", "band": "IV",
     "citation_systems": ["AA"], "citation_prefix": "AA IV"},
    {"work_id": "aa-IV-grundlegung", "ocr_dir": "aa-IV-grundlegung", "aa_band": "IV",
     "title": "Grundlegung zur Metaphysik der Sitten (1785)", "short_title": "Grundlegung (GMS)",
     "siglum": "AA IV", "series": "AA", "band": "IV",
     "citation_systems": ["AA"], "citation_prefix": "AA IV"},
    {"work_id": "aa-IV-man", "ocr_dir": "aa-IV-man", "aa_band": "IV",
     "title": "Metaphysische Anfangsgründe der Naturwissenschaft (1786)", "short_title": "Met. Anfangsgr. (MAN)",
     "siglum": "AA IV", "series": "AA", "band": "IV",
     "citation_systems": ["AA"], "citation_prefix": "AA IV"},
    # AA Bd. V: KpV, KdU
    {"work_id": "aa-V-kpv", "ocr_dir": "aa-V-kpv", "aa_band": "V",
     "title": "Kritik der praktischen Vernunft (1788)", "short_title": "Kritik der prakt. Vernunft",
     "siglum": "AA V", "series": "AA", "band": "V",
     "citation_systems": ["AA"], "citation_prefix": "AA V"},
    {"work_id": "aa-V-kdu", "ocr_dir": "aa-V-kdu", "aa_band": "V",
     "title": "Kritik der Urtheilskraft (1790)", "short_title": "Kritik der Urtheilskraft",
     "siglum": "AA V", "series": "AA", "band": "V",
     "citation_systems": ["AA"], "citation_prefix": "AA V"},
    # AA Bd. VI: Religion, Metaphysik der Sitten
    {"work_id": "aa-VI-religion", "ocr_dir": "aa-VI-religion", "aa_band": "VI",
     "title": "Die Religion innerhalb der Grenzen der bloßen Vernunft (1793)", "short_title": "Religion",
     "siglum": "AA VI", "series": "AA", "band": "VI",
     "citation_systems": ["AA"], "citation_prefix": "AA VI"},
    {"work_id": "aa-VI-mds", "ocr_dir": "aa-VI-mds", "aa_band": "VI",
     "title": "Die Metaphysik der Sitten (1797)", "short_title": "Metaphysik der Sitten",
     "siglum": "AA VI", "series": "AA", "band": "VI",
     "citation_systems": ["AA"], "citation_prefix": "AA VI"},
    # AA Bd. VII: Streit, Anthropologie
    {"work_id": "aa-VII-streit", "ocr_dir": "aa-VII-streit", "aa_band": "VII",
     "title": "Der Streit der Facultäten (1798)", "short_title": "Streit der Facultäten",
     "siglum": "AA VII", "series": "AA", "band": "VII",
     "citation_systems": ["AA"], "citation_prefix": "AA VII"},
    {"work_id": "aa-VII-anthropologie", "ocr_dir": "aa-VII-anthropologie", "aa_band": "VII",
     "title": "Anthropologie in pragmatischer Hinsicht (1798)", "short_title": "Anthropologie",
     "siglum": "AA VII", "series": "AA", "band": "VII",
     "citation_systems": ["AA"], "citation_prefix": "AA VII"},
    # AA Bd. VIII: Kleine Schriften
    {"work_id": "aa-VIII-entdeckung", "ocr_dir": "aa-VIII-entdeckung", "aa_band": "VIII",
     "title": "Über eine Entdeckung (1790)", "short_title": "Über eine Entdeckung",
     "siglum": "AA VIII", "series": "AA", "band": "VIII",
     "citation_systems": ["AA"], "citation_prefix": "AA VIII"},
    {"work_id": "aa-VIII-frieden", "ocr_dir": "aa-VIII-frieden", "aa_band": "VIII",
     "title": "Zum ewigen Frieden (1795)", "short_title": "Zum ewigen Frieden",
     "siglum": "AA VIII", "series": "AA", "band": "VIII",
     "citation_systems": ["AA"], "citation_prefix": "AA VIII"},
    {"work_id": "aa-VIII-kleine-schriften", "ocr_dir": "aa-VIII-kleine-schriften", "aa_band": "VIII",
     "title": "Kleine Schriften (1782–1800)", "short_title": "Kleine Schriften",
     "siglum": "AA VIII", "series": "AA", "band": "VIII",
     "citation_systems": ["AA"], "citation_prefix": "AA VIII"},
    # AA Bd. IX: Logik, Geographie, Pädagogik
    {"work_id": "aa-IX-logik", "ocr_dir": "aa-IX-logik", "aa_band": "IX",
     "title": "Logik (1800)", "short_title": "Logik",
     "siglum": "AA IX", "series": "AA", "band": "IX",
     "citation_systems": ["AA"], "citation_prefix": "AA IX"},
    {"work_id": "aa-IX-geographie", "ocr_dir": "aa-IX-geographie", "aa_band": "IX",
     "title": "Physische Geographie (1802)", "short_title": "Physische Geographie",
     "siglum": "AA IX", "series": "AA", "band": "IX",
     "citation_systems": ["AA"], "citation_prefix": "AA IX"},
    {"work_id": "aa-IX-paedagogik", "ocr_dir": "aa-IX-paedagogik", "aa_band": "IX",
     "title": "Pädagogik (1803)", "short_title": "Pädagogik",
     "siglum": "AA IX", "series": "AA", "band": "IX",
     "citation_systems": ["AA"], "citation_prefix": "AA IX"},
]


def load_pages(ocr_subdir: str) -> list[dict]:
    d = OCR_DIR / ocr_subdir
    if not d.exists():
        print(f"Warning: {d} does not exist, skipping")
        return []
    files = sorted(d.glob("page_*.json"))
    pages = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            pages.append(json.load(fh))
    return pages


RE_YEAR_END = re.compile(r"\(\d{4}\)\s*$")
RE_BARE_NUMERAL = re.compile(r"^(I{1,3}V?|IV|VI{0,3}|IX|X{0,3}|[A-Z]|\d+)\.?\s*$")
RE_DECORATIVE = re.compile(r"^[—–\-_=\s]+$")
RE_FOOTNOTE_REF = re.compile(r"\*\[\d+\]\s*")
RE_SENTENCE_END = re.compile(r"[.!?)\]]\s*$")


def merge_headings(paragraphs: list[dict]) -> list[dict]:
    """Merge consecutive heading paragraphs that are continuations of multi-line titles."""
    merged = []
    for para in paragraphs:
        if para["kind"] in ("heading", "subheading"):
            if RE_DECORATIVE.match(para["text"]):
                continue
            para = dict(para)
            para["text"] = RE_FOOTNOTE_REF.sub("", para["text"]).strip()
        prev_text = merged[-1]["text"] if merged else ""
        should_merge = (para["kind"] in ("heading", "subheading")
                        and merged
                        and merged[-1]["kind"] in ("heading", "subheading")
                        and (not RE_SENTENCE_END.search(prev_text)
                             or RE_BARE_NUMERAL.match(prev_text)))
        if should_merge:
            merged[-1]["text"] += " " + para["text"]
            merged[-1]["level"] = min(merged[-1].get("level", 2), para.get("level", 2))
        else:
            merged.append(dict(para))
    return merged


def build_toc(pages: list[dict]) -> list[dict]:
    toc = []
    for i, p in enumerate(pages):
        paras = merge_headings(p.get("paragraphs", []))
        for para in paras:
            if para["kind"] in ("heading", "subheading"):
                title = para["text"]
                if RE_BARE_NUMERAL.match(title):
                    continue
                level = para.get("level", 2)
                if RE_YEAR_END.search(title):
                    level = 2
                toc.append({
                    "title": title,
                    "page_kik": p.get("page_kik"),
                    "page_pdf": p.get("page_pdf"),
                    "level": level,
                })
    return toc


def build_search_entries(pages: list[dict], work_id: str) -> list[dict]:
    entries = []
    for i, p in enumerate(pages):
        if p.get("page_kind") in ("title_page", "blank", "toc"):
            continue
        text_parts = []
        for para in p.get("paragraphs", []):
            text_parts.append(para["text"])
        if not text_parts:
            continue
        full_text = " ".join(text_parts)
        # Split into chunks of ~300 chars for search granularity
        words = full_text.split()
        chunk = []
        chunk_len = 0
        for w in words:
            chunk.append(w)
            chunk_len += len(w) + 1
            if chunk_len > 300:
                entries.append({
                    "work_id": work_id,
                    "page_index": i,
                    "page_kik": p.get("page_kik"),
                    "text": " ".join(chunk),
                })
                chunk = []
                chunk_len = 0
        if chunk:
            entries.append({
                "work_id": work_id,
                "page_index": i,
                "page_kik": p.get("page_kik"),
                "text": " ".join(chunk),
            })
    return entries


def convert_page(p: dict, citation_prefix: str, citation_systems: list[str]) -> dict:
    units = []
    for para in merge_headings(p.get("paragraphs", [])):
        kind = para["kind"]
        t = "paragraph"
        if kind == "heading":
            t = "heading"
        elif kind == "subheading":
            t = "subheading"
        unit = {"type": t, "text": para["text"]}
        if "level" in para:
            unit["level"] = para["level"]
        units.append(unit)

    markers = p.get("page_markers", [])

    # Derive page_book from AA markers (the first AA page on this page)
    aa_markers = [m for m in markers if m.get("system") == "AA"]
    b_markers = [m for m in markers if m.get("system") == "B"]
    a_markers = [m for m in markers if m.get("system") == "A"]

    page_book = None
    if aa_markers:
        page_book = aa_markers[0]["page"]

    # Build sigel: "AA IV, 393" for AA works, "B 75" for KrV
    sigel = ""
    if "B" in citation_systems and b_markers:
        sigel = " · ".join(m["ref"] for m in b_markers)
    elif "A" in citation_systems and a_markers:
        sigel = " · ".join(m["ref"] for m in a_markers)
    elif "AA" in citation_systems and page_book is not None:
        sigel = f"{citation_prefix}, {page_book}"

    page_out = {
        "page_pdf": p["page_pdf"],
        "page_book": page_book,
        "page_kind": p["page_kind"],
        "sigel": sigel,
        "units": units,
    }

    if markers:
        page_out["markers"] = markers

    if p.get("running_header"):
        page_out["running_header"] = p["running_header"]

    return page_out


def assign_page_books(pages: list[dict], citation_prefix: str,
                      citation_systems: list[str]) -> list[dict]:
    """Fill in page_book and sigel for pages that lack markers."""
    last_aa = None
    for p in pages:
        if p["page_book"] is not None:
            last_aa = p["page_book"]
        elif last_aa is not None:
            p["page_book"] = last_aa
        if "AA" in citation_systems and p["page_book"] is not None and not p["sigel"]:
            p["sigel"] = f"{citation_prefix}, {p['page_book']}"
    return pages


def build_work_data(vol: dict, pages: list[dict]) -> dict:
    toc = build_toc(pages)
    citation_prefix = vol.get("citation_prefix", vol["siglum"])
    citation_systems = vol.get("citation_systems", [])
    converted = [convert_page(p, citation_prefix, citation_systems) for p in pages]
    converted = assign_page_books(converted, citation_prefix, citation_systems)

    stats = {
        "pages_total": len(pages),
        "pages_body": sum(1 for p in pages if p["page_kind"] == "body"),
        "headings": sum(1 for p in pages for pa in p.get("paragraphs", []) if pa["kind"] in ("heading", "subheading")),
        "paragraphs": sum(1 for p in pages for pa in p.get("paragraphs", []) if pa["kind"] == "paragraph"),
    }

    total_markers = sum(len(p.get("page_markers", [])) for p in pages)
    stats["page_markers"] = total_markers

    return {
        "metadata": {
            "work_id": vol["work_id"],
            "series": vol["series"],
            "band": vol["band"],
            "title": vol["title"],
            "short_title": vol["short_title"],
            "siglum": vol["siglum"],
            "edition": "Akademie-Ausgabe (1900–1923) via Kant im Kontext III (2017)",
            "collection_title": "Digitale Kant-Edition",
            "citation_systems": citation_systems,
            "citation_prefix": citation_prefix,
        },
        "toc_printed": toc,
        "pages": converted,
    }


def main():
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    all_works_meta = []
    all_search = []

    for vol in VOLUMES:
        pages = load_pages(vol["ocr_dir"])
        if not pages:
            continue

        print(f"Building {vol['work_id']}: {len(pages)} pages")

        work_data = build_work_data(vol, pages)
        search_entries = build_search_entries(pages, vol["work_id"])
        all_search.extend(search_entries)

        # Write work-*.js
        work_file = SITE_DIR / f"work-{vol['work_id']}.js"
        with open(work_file, "w", encoding="utf-8") as f:
            f.write(f"window.KANT_WORK_DATA = {json.dumps(work_data, ensure_ascii=False)};\n")
        print(f"  -> {work_file.name} ({work_file.stat().st_size / 1024:.0f} KB)")

        # Collect stats for edition-data
        stats = work_data["metadata"].copy()
        stats["stats"] = {
            "pages_total": len(pages),
            "pages_body": sum(1 for p in pages if p["page_kind"] == "body"),
            "headings": sum(1 for p in pages for pa in p.get("paragraphs", []) if pa["kind"] in ("heading", "subheading")),
            "paragraphs": sum(1 for p in pages for pa in p.get("paragraphs", []) if pa["kind"] == "paragraph"),
            "search_entries": len(search_entries),
        }
        all_works_meta.append(stats)

    # Build edition-data.js
    total_pages = sum(w["stats"]["pages_total"] for w in all_works_meta)
    total_search = len(all_search)
    total_headings = sum(w["stats"]["headings"] for w in all_works_meta)

    edition = {
        "metadata": {
            "title": "Digitale Kant-Edition",
            "collection_title": "Immanuel Kant · Gesammelte Schriften (Akademie-Ausgabe)",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "works_count": len(all_works_meta),
            "default_work_id": all_works_meta[0]["work_id"] if all_works_meta else "aa-III",
            "stats": {
                "pages_total": total_pages,
                "search_entries": total_search,
                "headings": total_headings,
            },
        },
        "works": [
            {
                "work_id": w["work_id"],
                "series": w["series"],
                "band": w["band"],
                "title": w["title"],
                "short_title": w["short_title"],
                "siglum": w["siglum"],
                "stats": w["stats"],
            }
            for w in all_works_meta
        ],
    }

    ed_file = SITE_DIR / "edition-data.js"
    with open(ed_file, "w", encoding="utf-8") as f:
        f.write(f"window.KANT_EDITION = {json.dumps(edition, ensure_ascii=False, indent=2)};\n")
    print(f"  -> {ed_file.name}")

    # Write search-data.js
    search_file = SITE_DIR / "search-data.js"
    with open(search_file, "w", encoding="utf-8") as f:
        f.write(f"window.KANT_SEARCH_DATA = {json.dumps(all_search, ensure_ascii=False)};\n")
    print(f"  -> {search_file.name} ({search_file.stat().st_size / 1024:.0f} KB, {len(all_search)} entries)")

    print(f"\nDone. {len(all_works_meta)} volumes, {total_pages} pages, {total_search} search entries.")


if __name__ == "__main__":
    main()
