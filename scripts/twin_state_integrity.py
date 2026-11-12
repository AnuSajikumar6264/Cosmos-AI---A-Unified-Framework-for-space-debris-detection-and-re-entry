"""Twin-state evidence root: selection, provenance, integrity and chain equivalence, offline (P3-B).

    python scripts/twin_state_integrity.py [--policy prefer_reemitted|reemitted_only|archived_only] [--run-id RUN] [--label L]

Runs the same code path as GET /api/twin-state (``ArtifactStore.twin_state_integration``) and writes
``outputs/audit/twin_state_integration_<label>_<UTC>.json``. Read-only; nothing regenerated. Exit 0 when
the selected source is the verified re-emitted archive with complete provenance, valid records and no value
difference against the catalogue chain; 1 otherwise (the record names every reason).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    from cosmos.product.store import DEFAULT_AS_OF, TWIN_SOURCE_POLICIES, ArtifactStore
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--policy", default="prefer_reemitted", choices=list(TWIN_SOURCE_POLICIES))
    ap.add_argument("--as-of", default=DEFAULT_AS_OF)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--label", default="check")
    a = ap.parse_args(argv)
    result = ArtifactStore(ROOT).twin_state_integration(a.as_of, a.policy, a.run_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%z")
    out = ROOT / f"outputs/audit/twin_state_integration_{a.label}_{stamp}.json"
    out.write_text(json.dumps(result, indent=1, default=str) + "\n")
    eq = result.get("equivalence") or {}
    print(json.dumps({"overall": result["overall"], "selected": result["selected_source"], "selection_status": result["selection_status"],
                      "integrity": (result.get("integrity") or {}).get("status"),
                      "equivalence": {k: eq.get(k) for k in ("status", "records_compared", "records_equal", "records_different",
                                                             "records_not_comparable", "records_missing_in_chain", "records_missing_in_twin", "equivalent")},
                      "computed_in_s": result.get("computed_in_s")}, indent=1))
    print("written", out.relative_to(ROOT))
    return 0 if result["overall"]["status"] == "primary_verified" else 1


if __name__ == "__main__":
    sys.exit(main())
