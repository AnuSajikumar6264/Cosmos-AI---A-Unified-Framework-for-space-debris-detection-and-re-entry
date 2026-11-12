"""Read the official Scopus source title list (xlsx) using only the standard library.

Usage:  python -I read_scopus.py <ext_list.xlsx> [search term ...]

An xlsx is a zip of XML parts, so no third-party reader is needed and the analysis environment
is left untouched. Streams the first worksheet and prints the header plus any row whose title
cell matches a search term.
"""
from __future__ import annotations

import re
import sys
import zipfile
from xml.etree import ElementTree

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        raw = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    out = []
    for si in ElementTree.fromstring(raw).findall(f"{NS}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    return out


def col_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref or "A").group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def rows(zf: zipfile.ZipFile, sheet: str, strings: list[str]):
    with zf.open(sheet) as stream:
        row: dict[int, str] = {}
        for event, el in ElementTree.iterparse(stream, events=("end",)):
            if el.tag == f"{NS}c":
                value = el.find(f"{NS}v")
                text = value.text if value is not None else None
                if el.get("t") == "s" and text is not None:
                    text = strings[int(text)]
                elif el.get("t") == "inlineStr":
                    isel = el.find(f"{NS}is")
                    text = "".join(t.text or "" for t in isel.iter(f"{NS}t")) if isel is not None else None
                row[col_index(el.get("r", ""))] = text
                el.clear()
            elif el.tag == f"{NS}row":
                width = (max(row) + 1) if row else 0
                yield [row.get(i) for i in range(width)]
                row = {}
                el.clear()


def main() -> int:
    path = sys.argv[1]
    terms = [t.lower() for t in sys.argv[2:]]
    with zipfile.ZipFile(path) as zf:
        sheets = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet")]
        strings = shared_strings(zf)
        sheet = sorted(sheets)[0]
        print(f"# file: {path}\n# sheet: {sheet}\n# shared strings: {len(strings)}\n")

        header = None
        matched = 0
        for i, row in enumerate(rows(zf, sheet, strings)):
            if header is None and row and any(row):
                header = row
                print("COLUMNS:")
                for j, name in enumerate(header):
                    if name:
                        print(f"  [{j}] {name}")
                print()
                continue
            if not terms:
                continue
            joined = " ".join(str(c) for c in row[:4] if c).lower()
            if any(t in joined for t in terms):
                matched += 1
                print(f"--- match {matched} (row {i})")
                for j, cell in enumerate(row):
                    if cell not in (None, ""):
                        name = header[j] if header and j < len(header) and header[j] else f"col{j}"
                        print(f"    {name}: {cell}")
                print()
        print(f"# total matches: {matched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
