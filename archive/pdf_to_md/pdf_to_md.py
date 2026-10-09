#!/usr/bin/env python3
"""Convert `docs/Google C++ Style Guide.pdf` into per-chapter Markdown.

Why a custom script instead of pdftotext / pandoc / pymupdf4llm
--------------------------------------------------------------
Every heading in this PDF is set in SimHei, and that font's ToUnicode CMap is
broken for four of its five subsets. Extractors therefore either emit garbage
(`3.11. ᆎ<0a0c><19dd><086c>` for `3.11. 存取控制`) or drop the character
outright (pymupdf loses ~19 of them, e.g. the 保 of `1.3. #define 保护`).
pdfplumber keeps unmapped characters as `(cid:N)`, and N is the glyph id, so the
real character is recovered as `N + 0x49CA` (see FIX_OFFSET / fix_cid).

The document is a LaTeX build, so the remaining structure is recovered from the
layout: font sizes give the heading level, full-width horizontal rules bracket
the `Tip:` boxes, and horizontal offsets give code indentation.
"""
from __future__ import annotations

import argparse
import os
import re

import pdfplumber
import pymupdf

# --------------------------------------------------------------------------- #
# SimHei repair
# --------------------------------------------------------------------------- #
FIX_OFFSET = 0x49CA

# Glyph ids whose `+ FIX_OFFSET` result is wrong; resolved by reading the PDF.
SPECIAL_CIDS = {
    0x023D: "\u3001",  # 、
    0x03B4: "\uff08",  # （
    0x03B5: "\uff09",  # ）
    0x5357: "\u5357",  # 南 -- +FIX_OFFSET would give 鴡
}

CID_RE = re.compile(r"^\(cid:(\d+)\)$")

# LaTeX emits typographic ligatures; expand them so the text can be searched.
LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl",
    "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st",
}


def fix_cid(cid: int) -> str:
    """Map a SimHei glyph id to the character it actually draws."""
    if cid in SPECIAL_CIDS:
        return SPECIAL_CIDS[cid]
    cand = cid + FIX_OFFSET
    if 0x4E00 <= cand <= 0x9FFF:
        return chr(cand)
    return chr(cid) if cid < 0x110000 else "\ufffd"


# --------------------------------------------------------------------------- #
# geometry constants
# --------------------------------------------------------------------------- #
MONO_ADVANCE = 4.7072  # pt per character in LMMono9/10
BASELINE_TOL = 2.5  # pt: chars sharing a baseline form one visual row
CELL_GAP = 45.0  # pt: wider than this and the row holds separate table cells
PARA_GAP = 17.0  # pt: a larger baseline step starts a new paragraph
SPACE_RATIO = 0.15  # pt of gap per pt of font size that counts as a word space

SIZE_CODE = 9.0
SIZE_CHAPTER = 14.3

BULLET_RE = re.compile(r"^[•·]\s*")
OLIST_RE = re.compile(r"^(\d+)[.、]\s+")
LABEL_RE = re.compile(r"^([\u4e00-\u9fff]{1,4}|Tip|Note|Warning|译者注)\s*[:：]\s*")

ADMONITION_LABELS = {"Tip", "Note", "Warning", "注意", "警告", "译者注", "参考"}
PARA_LABELS = {"定义", "优点", "缺点", "结论", "参考", "说明", "举例"}

CHAPTER_FILES = {
    "0": "00-front",
    "1": "01-headers",
    "2": "02-scoping",
    "3": "03-classes",
    "4": "04-magic",
    "5": "05-others",
    "6": "06-naming",
    "7": "07-comments",
    "8": "08-formatting",
    "9": "09-exceptions",
    "10": "10-end",
}


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #
class Row:
    __slots__ = ("page", "y", "x", "x1", "text", "size", "fonts", "cells", "chars")

    def __init__(self, page, y, x, x1, text, size, fonts, cells=None, chars=None):
        self.page, self.y, self.x, self.x1 = page, y, x, x1
        self.text, self.size, self.fonts = text, size, fonts
        self.cells = cells or [(x, text)]
        self.chars = chars or []

    def __repr__(self):
        return f"Row(p{self.page} y={self.y:.1f} x={self.x:.1f} {self.text[:40]!r})"


def _char_text(ch: dict) -> str:
    m = CID_RE.match(ch["text"])
    if m:
        return fix_cid(int(m.group(1))) if "SimHei" in ch["fontname"] else ""
    return LIGATURES.get(ch["text"], ch["text"])


def _is_space_gap(prev: dict, cur: dict) -> bool:
    gap = cur["x0"] - prev["x1"]
    return gap > SPACE_RATIO * max(prev["size"], cur["size"], 1.0)


def rows_from_page(page_chars: list[dict], page_no: int) -> list[Row]:
    """Group pdfplumber characters into visual rows and rebuild their text."""
    cluster: list[dict] = []  # current baseline bucket: list of char dicts
    buckets: list[list[dict]] = []
    for ch in sorted(page_chars, key=lambda c: c["bottom"]):
        if cluster and ch["bottom"] - cluster[-1]["bottom"] > BASELINE_TOL:
            buckets.append(cluster)
            cluster = []
        cluster.append(ch)
    if cluster:
        buckets.append(cluster)

    rows: list[Row] = []
    for bucket in buckets:
        # a bucket may hold several columns; split on a wide horizontal gap
        bucket = sorted(bucket, key=lambda c: c["x0"])
        groups: list[list[dict]] = [[]]
        for ch in bucket:
            if groups[-1] and ch["x0"] - max(c["x1"] for c in groups[-1]) > CELL_GAP:
                groups.append([])
            groups[-1].append(ch)

        cells: list[tuple[float, str]] = []
        char_pairs: list[tuple[float, float, float, str]] = []
        parts: list[str] = []
        for group in groups:
            cell = ""
            prev = None
            for ch in group:
                piece = _char_text(ch)
                if not piece:
                    continue
                spaced = prev is not None and _is_space_gap(prev, ch)
                char_pairs.append((round(ch["x0"], 1), round(ch["x1"], 1), round(ch["size"], 1), piece))
                if spaced:
                    cell += " "
                    char_pairs.insert(len(char_pairs) - 1,
                                      (round(ch["x0"], 1), round(ch["x0"], 1), round(ch["size"], 1), " "))
                cell += piece
                prev = ch
            if cell.strip():
                cells.append((round(group[0]["x0"], 1), cell.strip()))
                parts.append(cell.strip())

        text = "  ".join(parts)
        if not text:
            continue
        rows.append(
            Row(
                page=page_no,
                y=round(min(c["top"] for c in bucket), 1),
                x=round(min(c["x0"] for c in bucket), 1),
                x1=round(max(c["x1"] for c in bucket), 1),
                text=text,
                size=round(max(c["size"] for c in bucket), 1),
                fonts={c["fontname"].split("+")[-1] for c in bucket},
                cells=cells,
                chars=char_pairs,
            )
        )
    rows.sort(key=lambda r: (r.y, r.x))
    return rows


def admonition_boxes(doc: pymupdf.Document) -> dict[int, list[tuple[float, float]]]:
    """page -> [(y_top, y_bottom)] for the full-width bordered `Tip:` boxes.

    Only rules spanning the whole text column count; the narrower rules belong to
    code blocks and tables.
    """
    boxes: dict[int, list[tuple[float, float]]] = {}
    for pno in range(len(doc)):
        ys = set()
        for drawing in doc[pno].get_drawings():
            for item in drawing["items"]:
                if item[0] != "l":
                    continue
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) > 0.5:
                    continue
                if abs(min(p1.x, p2.x) - 43.7) < 3 and abs(max(p1.x, p2.x) - 551.6) < 3:
                    ys.add(round(p1.y, 1))
        ordered = sorted(ys)
        pairs = [(ordered[i], ordered[i + 1]) for i in range(0, len(ordered) - 1, 2)]
        if pairs:
            boxes[pno + 1] = pairs
    return boxes


# --------------------------------------------------------------------------- #
# classification
# --------------------------------------------------------------------------- #
def kind_of(row: Row) -> str:
    if row.size >= 17:
        return "title"
    if row.size >= SIZE_CHAPTER - 0.6:
        return "chapter"
    if "LMSans10-Bold" in row.fonts:
        return "section" if row.size > 10.5 else "subsection"
    if abs(row.size - SIZE_CODE) < 0.6:
        return "code"
    return "body"


def chapter_key(row: Row) -> str:
    m = re.match(r"^(\d+)\.", row.text.strip())
    return m.group(1) if m else "0"


def gfm_slug(text: str) -> str:
    """Approximate GitHub's heading anchor algorithm, used for the index links."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)
    return re.sub(r"[\s]+", "-", text).strip("-")


def bullet_depth(x: float) -> int:
    """Bullets in this PDF sit at three offsets; the middle one is cosmetic."""
    if x >= 90:
        return 1
    return 0


def table_regions(doc: pymupdf.Document) -> dict[int, list[tuple[float, float]]]:
    """page -> [(y_top, y_bottom)] of the ruled tables.

    A table shows up as three or more closely stacked horizontal rules that share
    the same span; the `Tip:` boxes only ever have two, and they span the whole
    text column.
    """
    regions: dict[int, list[tuple[float, float]]] = {}
    for pno in range(len(doc)):
        rules = []
        for drawing in doc[pno].get_drawings():
            for item in drawing["items"]:
                if item[0] != "l":
                    continue
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) > 0.5:
                    continue
                x0, x1 = min(p1.x, p2.x), max(p1.x, p2.x)
                if x1 - x0 < 100 or abs(x0 - 43.7) < 3:
                    continue  # page-wide rules belong to `Tip:` boxes
                rules.append((round(p1.y, 1), round(x0, 1), round(x1, 1)))
        rules.sort()
        run: list[tuple[float, float, float]] = []
        found: list[tuple[float, float]] = []
        for rule in rules:
            if run and (rule[0] - run[-1][0] < 25
                        and abs(rule[1] - run[0][1]) < 1.5
                        and abs(rule[2] - run[0][2]) < 1.5):
                run.append(rule)
            else:
                if len(run) >= 4:
                    found.append((run[0][0] - 10, run[-1][0] + 2))
                run = [rule]
        if len(run) >= 4:
            found.append((run[0][0] - 10, run[-1][0] + 2))
        if found:
            regions[pno + 1] = found
    return regions


def in_table(regions: dict[int, list[tuple[float, float]]], page: int, y: float) -> bool:
    return any(top <= y <= bottom for top, bottom in regions.get(page, []))


def horizontal_rules(doc: pymupdf.Document) -> dict[int, list[float]]:
    """page -> sorted y of every horizontal rule, used to split stacked code boxes."""
    out: dict[int, list[float]] = {}
    for pno in range(len(doc)):
        ys = set()
        for drawing in doc[pno].get_drawings():
            for item in drawing["items"]:
                if item[0] != "l":
                    continue
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 0.5 and abs(p2.x - p1.x) > 100:
                    ys.add(round(p1.y, 1))
        if ys:
            out[pno + 1] = sorted(ys)
    return out


def _confirmed_tables(
    regions: dict[int, list[tuple[float, float]]], rows: list[Row]
) -> dict[int, list[tuple[float, float]]]:
    """Drop ruled regions that do not actually contain a grid of cells."""
    out: dict[int, list[tuple[float, float]]] = {}
    for page, spans in regions.items():
        keep = []
        for top, bottom in spans:
            cell_rows = [
                r for r in rows
                if r.page == page and top <= r.y <= bottom and len(r.cells) >= 3
            ]
            if len(cell_rows) >= 2:
                keep.append((top, bottom))
        if keep:
            out[page] = keep
    return out


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
class Renderer:
    def __init__(self, rows, boxes, tables=None, rules=None):
        self.rows, self.boxes = rows, boxes
        self.tables = tables or {}
        self.rules = rules or {}
        self.out: list[str] = []
        self.para: list[str] = []
        self.code: list[tuple[float, str]] | None = None
        self.code_page: int | None = None
        self.code_y: float | None = None
        self.quote: list[str] | None = None
        self.list_open = False

    # -- paragraph / block flushing ---------------------------------------- #
    def flush_para(self):
        if self.para:
            text = "".join(self.para).strip()
            text = re.sub(r"\s{2,}", " ", text)
            self.out.append(text)
            self.out.append("")
        self.para = []

    def close_list(self):
        """Markdown needs a blank line between a list and the block after it."""
        if self.list_open:
            if not (self.out and not self.out[-1].strip()):
                self.out.append("")
            self.list_open = False

    def flush_code(self):
        if not self.code:
            self.code = None
            return
        base = min(x for x, _ in self.code)
        lines = []
        for x, text in self.code:
            indent = max(0, round((x - base) / MONO_ADVANCE))
            lines.append(" " * indent + text.rstrip())
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            self.out.append("```cpp")
            self.out.extend(lines)
            self.out.append("```")
            self.out.append("")
        self.code = None
        self.code_page = None
        self.code_y = None

    def flush_quote(self):
        if self.quote:
            text = ""
            for part in self.quote:
                if not part.strip():
                    continue
                text = part if not text else text + ("" if _cjk_join(text, part) else " ") + part
            text = re.sub(r"\s+", " ", text).strip()
            m = LABEL_RE.match(text)
            if m:
                self.out.append(f"> **{text[:m.end()].strip()}** {text[m.end():].strip()}")
            else:
                self.out.append(f"> {text}")
            self.out.append("")
            self.quote = None

    def flush_all(self):
        self.close_list()
        self.flush_code()
        self.flush_quote()
        self.flush_para()

    # -- helpers ------------------------------------------------------------ #
    def _break_blocks(self):
        self.close_list()
        self.flush_code()
        self.flush_quote()
        self.flush_para()

    def in_box(self, row: Row) -> bool:
        return any(
            top - 2 <= row.y <= bottom + 2 for top, bottom in self.boxes.get(row.page, [])
        )

    def in_table(self, row: Row) -> bool:
        return in_table(self.tables, row.page, row.y)

    def emit_table(self, region: list[Row]):
        header = max(region, key=lambda r: len(r.cells))
        columns = [x for x, _ in header.cells]
        if len(columns) < 2:
            return
        grid = []
        for row in region:
            cells = [""] * len(columns)
            prev = None
            for x0, x1, size, piece in row.chars:
                matches = [i for i, cx in enumerate(columns) if x0 >= cx - 3]
                col = matches[-1] if matches else 0
                if piece == " ":
                    if cells[col] and not cells[col].endswith(" "):
                        cells[col] += " "
                else:
                    if prev is not None and _is_space_gap(
                        {"x0": prev[0], "x1": prev[1], "size": prev[2]},
                        {"x0": x0, "x1": x1, "size": size},
                    ) and cells[col] and not cells[col].endswith(" "):
                        cells[col] += " "
                    cells[col] += piece
                prev = (x0, x1, size)
            grid.append([c.strip() for c in cells])
        self._break_blocks()
        self.out.append("| " + " | ".join(grid[0]) + " |")
        self.out.append("| " + " | ".join("---" for _ in columns) + " |")
        for cells in grid[1:]:
            self.out.append("| " + " | ".join(cells) + " |")
        self.out.append("")

    def run(self) -> list[str]:
        prev: Row | None = None
        label_open = False
        i = 0
        while i < len(self.rows):
            row = self.rows[i]
            if self.in_table(row):
                region = [row]
                j = i + 1
                while j < len(self.rows) and self.in_table(self.rows[j]):
                    region.append(self.rows[j])
                    j += 1
                self.emit_table(region)
                prev = region[-1]
                label_open = False
                i = j
                continue
            i += 1
            text = row.text.strip()
            if not text:
                continue
            kind = kind_of(row)
            gap = row.y - prev.y if prev and prev.page == row.page else 10_000.0

            if kind in ("title", "chapter", "section", "subsection"):
                self._break_blocks()
                if kind != "title":
                    level = {"chapter": 1, "section": 2, "subsection": 3}[kind]
                    self.out.append("#" * level + " " + text)
                    self.out.append("")
                label_open = False
                prev = row
                continue

            if kind == "code":
                # a rule between two code rows means they sit in different boxes
                if self.code is not None and self.code_page == row.page:
                    between = [
                        y for y in self.rules.get(row.page, [])
                        if self.code_y is not None and self.code_y < y < row.y
                    ]
                    if between:
                        self.flush_code()
                self.close_list()
                self.flush_quote()
                self.flush_para()
                if self.code is None:
                    self.code = []
                    self.code_page = row.page
                self.code.append((row.x, row.text))
                self.code_y = row.y
                label_open = False
                prev = row
                continue

            if self.in_box(row):
                self.close_list()
                self.flush_code()
                self.flush_para()
                if self.quote is None:
                    self.quote = []
                self.quote.append(text)
                label_open = False
                prev = row
                continue
            self.flush_code()
            self.flush_quote()

            bullet = BULLET_RE.match(text)
            if bullet:
                self.flush_code()
                self.flush_para()
                self.out.append("  " * bullet_depth(row.x) + "- " + text[bullet.end():].strip())
                self.list_open = True
                label_open = False
                prev = row
                continue

            olist = OLIST_RE.match(text)
            if olist:
                self.flush_code()
                self.flush_para()
                self.out.append(f"{olist.group(1)}. " + text[olist.end():].strip())
                self.list_open = True
                label_open = False
                prev = row
                continue

            label = LABEL_RE.match(text)
            if label and (label.group(1) in PARA_LABELS or label.group(1) in ADMONITION_LABELS):
                self.close_list()
                self.flush_code()
                self.flush_para()
                head = text[:label.end()].strip()
                rest = text[label.end():].strip()
                self.para = [f"**{head}**" + (" " + rest if rest else "")]
                label_open = not rest
                prev = row
                continue

            # a label paragraph that was split onto its own line absorbs what follows
            if label_open:
                self.para.append(("" if _cjk_join(self.para[-1], text) else " ") + text)
                label_open = False
                self.list_open = False
                prev = row
                continue

            # continuation of the previous list item
            if self.list_open and self.out and gap < PARA_GAP:
                last = self.out[-1]
                joiner = "" if _cjk_join(last, text) else " "
                self.out[-1] = last + joiner + text
                prev = row
                continue

            new_para = not self.para or gap > PARA_GAP or prev is None or prev.page != row.page
            if new_para:
                self.close_list()
                self.flush_para()
                self.para = [text]
            else:
                self.para.append(("" if _cjk_join(self.para[-1], text) else " ") + text)
            prev = row

        self.close_list()
        self.flush_all()
        return self.out


def _cjk_join(left: str, right: str) -> bool:
    """True when the two fragments should be concatenated with no space."""
    if not left or not right:
        return True
    a, b = left[-1], right[0]
    if a in "([/-\u2013\u2014" or b in ",.;:)]}%\u3001\u3002\uff0c\uff1b\uff1a":
        return True
    return _is_cjk(a) and _is_cjk(b)


def _is_cjk(ch: str) -> bool:
    return 0x2E80 <= ord(ch) <= 0x9FFF or 0xF900 <= ord(ch) <= 0xFAFF or ord(ch) > 0xFF00


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def convert(pdf_path: str, out_dir: str) -> list[tuple[str, str]]:
    all_rows: list[Row] = []
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            all_rows.extend(rows_from_page(page.chars, pno))
    all_rows = [r for r in all_rows if r.page > 1]  # drop the LaTeX title page

    doc = pymupdf.open(pdf_path)
    boxes = admonition_boxes(doc)
    tables = _confirmed_tables(table_regions(doc), all_rows)
    rules = horizontal_rules(doc)

    chapters: list[tuple[str, list[Row]]] = []
    current: list[Row] = []
    for row in all_rows:
        if kind_of(row) == "chapter":
            if current:
                chapters.append((chapter_key(current[0]), current))
            current = [row]
        else:
            current.append(row)
    if current:
        chapters.append((chapter_key(current[0]), current))

    os.makedirs(out_dir, exist_ok=True)
    written: list[tuple[str, str]] = []
    for key, group in chapters:
        name = CHAPTER_FILES.get(key, f"chapter-{key}")
        lines = Renderer(group, boxes, tables, rules).run()
        cleaned: list[str] = []
        for line in lines:
            if not line.strip() and cleaned and not cleaned[-1].strip():
                continue
            cleaned.append(line)
        body = "\n".join(cleaned).strip() + "\n"
        with open(os.path.join(out_dir, name + ".md"), "w") as fh:
            fh.write(body)
        written.append((name, body))

    index = write_index(out_dir, written)
    return written + [("index", index)]


def write_index(out_dir: str, written: list[tuple[str, str]]) -> str:
    """Build index.md: chapter links plus a flat table of contents."""
    lines = [
        "# Google C++ Style Guide 中文版 (v4.45, 2017) — 目录",
        "",
        "从 `../Google C++ Style Guide.pdf` 转换而来，章节编号与内容与 PDF 一致。"
        "正文按章节拆分，本文件是索引。",
        "",
        "## 章节",
        "",
    ]
    for name, body in written:
        first = body.lstrip().splitlines()[0]
        title = re.sub(r"^#+\s*", "", first)
        lines.append(f"- [{title}]({name}.md)")
    lines += ["", "## 全部小节", ""]
    for name, body in written:
        in_code = False
        for line in body.splitlines():
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            m = re.match(r"^(#{1,3})\s+(.*)$", line)
            if not m:
                continue
            level, text = len(m.group(1)), m.group(2).strip()
            if not text or (not text[0].isdigit() and "译者" not in text):
                continue
            label = f"[{text}]({name}.md#{gfm_slug(text)})"
            lines.append(f"- **{label}**" if level == 1 else "    " * (level - 2) + f"- {label}")
    index = "\n".join(lines) + "\n"
    with open(os.path.join(out_dir, "index.md"), "w") as fh:
        fh.write(index)
    return index


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    args = ap.parse_args()
    for name, body in convert(args.pdf, args.out_dir):
        print(f"{name}.md  {len(body):7d} chars  {body.count(chr(10)):4d} lines")
