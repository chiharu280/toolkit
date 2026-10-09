#!/usr/bin/env python3
"""Convert the upstream `zh-google-styleguide` reStructuredText sources to Markdown.

The PDF in this repo is a 2017 LaTeX build of the same translation; that one has
to be recovered from the rendered layout (see pdf_to_md.py). Here the source is
plain RST, so pandoc does the work -- this script only fixes up the two
Sphinx-specific constructs the project relies on:

  * ``:ref:`label``` / ``:ref:`text <label>``` cross references
  * ``.. tip::`` admonitions
"""
from __future__ import annotations

import argparse
import os
import re

import pypandoc

FILES = [
    ("index", "00-front"),
    ("headers", "01-headers"),
    ("scoping", "02-scoping"),
    ("classes", "03-classes"),
    ("functions", "04-functions"),
    ("magic", "05-magic"),
    ("others", "06-others"),
    ("naming", "07-naming"),
    ("comments", "08-comments"),
    ("formatting", "09-formatting"),
    ("exceptions", "10-exceptions"),
    ("end", "11-end"),
]

TITLE_CHARS = "=-~^+*#\""
LABEL_RE = re.compile(r"^\.\. _([\w.-]+):\s*$")
TITLE_UNDER_RE = re.compile(r"^([" + re.escape(TITLE_CHARS) + r"])\1{2,}\s*$")
REF_RE = re.compile(
    r":ref:`([^`<]+?)\s*<([\w.-]+)>`"
    r"|:ref:`([^`<>\s]+)`"
)


def gfm_slug(text: str) -> str:
    """Approximate GitHub's heading anchor algorithm."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)
    return re.sub(r"[\s]+", "-", text).strip("-")


def collect_labels(sources: dict[str, str]) -> dict[str, tuple[str, str]]:
    """label -> (file stem, section title) for every `.. _label:` before a heading."""
    labels: dict[str, tuple[str, str]] = {}
    for stem, text in sources.items():
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = LABEL_RE.match(line)
            if not m:
                continue
            for j in range(i + 1, min(i + 6, len(lines))):
                if TITLE_UNDER_RE.match(lines[j]) and j > 0:
                    labels[m.group(1)] = (stem, lines[j - 1].strip())
                    break
    return labels


def replace_refs(text: str, labels: dict[str, tuple[str, str]]) -> str:
    """Rewrite ``:ref:`` roles as RST external links so pandoc emits real Markdown links.

    Pandoc's RST reader does not know the Sphinx ``:ref:`` role and would just
    print the label, which is meaningless to a reader.
    """
    out_names = dict(FILES)

    def sub(m: re.Match) -> str:
        label = m.group(2) or m.group(3)
        shown = (m.group(1) or "").strip()
        target = labels.get(label)
        if not target:
            return f"``{shown or label}``"
        stem, title = target
        fname = out_names.get(stem)
        if fname is None:
            return f"``{shown or title}``"
        url = f"{fname}.md#{gfm_slug(title)}"
        return f"`{shown or title} <{url}>`_"

    return REF_RE.sub(sub, text)


def convert_file(text: str) -> str:
    md = pypandoc.convert_text(text, "gfm", format="rst", extra_args=["--wrap=none"])
    md = md.replace("\\#", "#").replace("\\+", "+")
    md = re.sub(
        r"^> \[!(TIP|NOTE|WARNING)\]\n> ?",
        lambda m: f"> **{m.group(1).capitalize()}：** ",
        md,
        flags=re.MULTILINE,
    )
    return md


def main(src_dir: str, out_dir: str):
    sources = {}
    for stem, _ in FILES:
        with open(os.path.join(src_dir, stem + ".rst")) as fh:
            sources[stem] = fh.read()

    labels = collect_labels(sources)
    os.makedirs(out_dir, exist_ok=True)

    index = [
        "# Google C++ Style Guide (中文版, 上游最新)",
        "",
        "> 由 [zh-google-styleguide](https://github.com/zh-google-styleguide/zh-google-styleguide)",
        "> 的 reStructuredText 源转换而来，非本仓库 PDF 的版本。",
        "",
        "## 目录",
        "",
    ]

    for stem, out_name in FILES:
        md = convert_file(replace_refs(sources[stem], labels))
        md = md.strip() + "\n"
        with open(os.path.join(out_dir, out_name + ".md"), "w") as fh:
            fh.write(md)
        index.append(f"- [{out_name}]({out_name}.md)")

    with open(os.path.join(out_dir, "index.md"), "w") as fh:
        fh.write("\n".join(index) + "\n")

    print(f"converted {len(FILES)} files, {len(labels)} ref labels resolved")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir")
    ap.add_argument("out_dir")
    args = ap.parse_args()
    main(args.src_dir, args.out_dir)
