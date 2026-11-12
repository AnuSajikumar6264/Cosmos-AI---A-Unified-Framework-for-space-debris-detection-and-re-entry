# Schema versioning policy (P1.3, 2026-11-08)

Code: `cosmos/ai/schema.py`. Every record family COSMOS-AI writes or serves carries a dotted version
string in a `schema_version` field of the form `<family>/<MAJOR>.<MINOR>`.

## Families and current versions

| Family | Current | Accepted on read | Where stamped | What changed at the current version |
|---|---|---|---|---|
| `forecast_table` | 1.0 | 1.0 | not stamped (archived CSV); identified by its column set `REQUIRED_FORECAST_COLUMNS` and SHA-256 | — |
| `twin_state` | 1.1 | 1.0 (archived `twins.jsonl`, no `schema_version`, `provenance: null`), 1.1 | `cosmos.ai.twin.reemit` | per-output provenance, `source_record`, `reemitted_from_archive`, `reemission_method`. Read, since P3-B (2026-11-08), only through `cosmos.ai.twin.reader`: explicit source policy (`prefer_reemitted` / `reemitted_only` / `archived_only`), candidate verdicts with reasons, streaming record validation, equivalence with the catalogue chain |
| `run_manifest` | 1.2 | 1.0 (no `lineage`), 1.1 (lineage; dict outputs serialised verbatim), 1.2 | `scripts/run_pipeline.py` | outputs serialised under an allow-list: only `MANIFEST_VERBATIM_OUTPUTS` (`priority_rule`) is kept verbatim; every other dict output is `{count}`, a table summary `{rows, columns}` or an evidence record `{module, status, reason}`; the validator enforces this for 1.2 (P3-A1, 2026-11-08) |
| `object_record` | 1.1 | 1.1 | `ArtifactStore.object_record` → `/api/objects/{norad}` | `subgroup_coverage`, `horizon_relation`, `freshness`, `provenance.model_version`, source labels |
| `report` | 1.1 | 1.0, 1.1 | `cosmos.product.reports.object_report` | model version, lineage note, subgroup cue, horizon relation, freshness |
| `api` | 1.2 | 1.1, 1.2 | `/api/overview`, `/api/datasets`, `/api/runs/{id}` (`view_schema_version`), `/api/runs/{id}/ranking`, `/api/ready`, `/api/twin-state`, `/api/objects/{norad}/twin` | 1.2 (2026-11-08, additive — MINOR): readiness endpoint, `redaction` block on exported reports, `/api/twin-state`, `selection` and `equivalence` blocks on twin records, `policy` parameter. No field removed or renamed |
| `freshness` | 1.0 | 1.0 | inside `object_record.freshness` | — |

### Run-manifest modules added by P3-B (2026-11-08)

`twin_state` (a root module: selected archive, digest state, schema, record count, transformation digest,
integrity counts — all scalars; `record_index` is counted) and `twin_equivalence` (records compared / equal /
different / not comparable / missing on either side, field totals, `equivalent`; `comparison` is counted and
written as `twin_equivalence.csv`). Both stay within `run_manifest/1.2`: no allow-list change, no new verbatim
dictionary. Manifests without these modules (every run before 2026-11-08 09:00 UTC) remain valid 1.0–1.2 records;
the console reports the capability "versioned twin state" as `archived_only` for them.

## Rules

1. **MAJOR** changes remove or rename a field or change its meaning; readers written for the old
   major must refuse the new one. **MINOR** changes only add fields; old readers ignore them.
2. **Archived records are never rewritten.** A record without `schema_version` is read as its
   family's `1.0`. The archived twin state (`outputs/twin/as_of_2026-10-27/twins.jsonl`, sha
   `19a1fede…`) and the 85+ run manifests under `outputs/pipeline/` stay as they are; readers derive
   missing newer fields at read time (e.g. `lineage_for_module`) and label them as derived or
   unavailable — they never write them back.
3. **Writers stamp the current version** (`schema.stamp(family)`).
4. **Validation names the field.** `validate_twin_record`, `validate_run_manifest` and
   `validate_forecast_columns` raise `SchemaError` with the offending key; the console turns a
   malformed run manifest into a `DataUnavailable` ("run … manifest is malformed: …") so the page
   reports it instead of failing. Nothing is repaired silently.
5. **Migration expectation.** New versions must come with: the row above, a validator branch, a
   reader that accepts the previous version, and a test that an archived record still validates as
   its old version. Re-emission (not rewriting) is the way to produce a newer version of an archived
   artifact, into a separate versioned directory.

## Known legacy forms

* `run_manifest` 1.0: manifests written before 2026-11-08 — no `schema_version`, no `lineage`.
* `run_manifest` 1.1: manifests written on 2026-11-08 by the P2 code — `lineage` present, but every
  dict output whose values were scalars was copied verbatim, so per-object maps (names, regimes,
  abstention reasons) inflated the demonstration manifest `outputs/pipeline/run_20261108T072802Z` to
  5.2 MB. It is read as-is (never rewritten); 1.2 closes the rule.
* `twin_state` 1.0: the archived twin state — `provenance: null` on every output.
* Reports fetched before 2026-11-08 carried `schema_version: "1.0"` without the `report/` prefix;
  readers should treat a bare `"1.0"` as `report/1.0`.
