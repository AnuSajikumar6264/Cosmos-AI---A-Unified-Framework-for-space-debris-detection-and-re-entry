"""Count active Scopus journals per ASJC subject code, from the official source title list.

Usage:  python -I count_asjc.py <ext_list.xlsx> <asjc> [<asjc> ...]

The category size determines what a "top 100" position actually means: top 100 of 150 is a
different claim from top 100 of 400.
"""
from __future__ import annotations

import sys
import zipfile

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from read_scopus import rows, shared_strings  # noqa: E402

ASJC_NAMES = {
    "2202": "Aerospace Engineering",
    "2213": "Safety, Risk, Reliability and Quality",
    "1912": "Space and Planetary Science",
    "3103": "Astronomy and Astrophysics",
    "1902": "Atmospheric Science",
    "1908": "Geophysics",
    "1710": "Information Systems",
    "1706": "Computer Science Applications",
    "3309": "Library and Information Sciences",
    "2613": "Statistics and Probability",
    "1804": "Statistics, Probability and Uncertainty",
    "1702": "Artificial Intelligence",
}


def main() -> int:
    path = sys.argv[1]
    wanted = sys.argv[2:] or list(ASJC_NAMES)
    counts = {code: {"all": 0, "active": 0, "journal_active": 0} for code in wanted}

    with zipfile.ZipFile(path) as zf:
        strings = shared_strings(zf)
        sheet = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        header = None
        for row in rows(zf, sheet, strings):
            if header is None and row and any(row):
                header = row
                continue
            if not row or len(row) <= 20:
                continue
            codes = {c.strip() for c in str(row[20] or "").split(";") if c.strip()}
            status = str(row[4] or "").strip().lower()
            stype = str(row[12] or "").strip().lower()
            for code in wanted:
                if code in codes:
                    counts[code]["all"] += 1
                    if status == "active":
                        counts[code]["active"] += 1
                        if stype == "journal":
                            counts[code]["journal_active"] += 1

    print(f"{'ASJC':6s} {'category':42s} {'all':>7s} {'active':>7s} {'active journals':>16s}")
    for code in wanted:
        c = counts[code]
        print(f"{code:6s} {ASJC_NAMES.get(code, '?'):42s} {c['all']:7d} {c['active']:7d} "
              f"{c['journal_active']:16d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
