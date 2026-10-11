# Setup

## 1. Environment
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Prove it works
```bash
pip install playwright
python -m playwright install chromium
pytest                           # includes real-browser checks; no live data calls
python -m http.server 8000       # then open http://localhost:8000
```
(The site must be viewed over http://, not file:// — the page fetches
data/*.json.)

## 3. View or rebuild the presentation
The published `data/*.json` and `data/*.csv` files are committed, so you can
browse the site and run the tests without scraping anything. To regenerate
the presentation from those published files:
```bash
python -m pipeline.build_fallbacks
pytest
```

## 4. Routine ingest (requires the complete existing raw cache)
Read the latest ingestion entry in `DECISIONS.md` first. Back up `data/raw/`
outside the repository. Fetch the new meeting only, for example:
```bash
python -m pipeline.scrape.minutes 2026 november
python -m pipeline.scrape.backfill_pdf
python -m pipeline.build_index
```
The month scraper now preserves an existing text file without fetching it
again, including PDF-derived text. An HTML-only partial cache is rejected.
Do not delete files to force a refresh: reconstruct separately and compare.
The index builder refuses missing or changed historical document hashes or
source kinds. Review every diff before rebuilding downstream results. The
example month is not evidence that its announcement is available yet.

## 5. Full reconstruction is not an HTML scrape
`data/raw/` is gitignored and is not supplied in a fresh checkout. A full
reconstruction needs regular HTML pages, PDF backfill, the two emergency
March 2020 documents, the voting spreadsheet, and the manual text repairs
documented in the log. An era scrape alone is incomplete and must not be
used to replace the published index.

Work in a separate disposable copy of the repository. In that copy only:
```bash
python -m pipeline.scrape.era
python -m pipeline.scrape.backfill_pdf
python -m pipeline.scrape.votes
```
If the era run flags short extracts, stop downstream work and inspect them;
PDF backfill is the next recovery step, not permission to ignore the failure.
Emergency source URLs and filename conventions are recorded in
`pipeline/build_index.py` (`SPECIAL_SOURCE_URLS`). Follow the full-text repair
and emergency-meeting entries in `DECISIONS.md`, then reconcile documents,
dates, source kinds and SHA-256 hashes against the committed index before
promoting anything. Re-extracted PDFs may differ by parser version; exact
byte-for-byte reconstruction from public downloads alone is not guaranteed.

Market history additionally needs the OIS and SONIA caches. Its v1 dates
are valuation/reference dates, not verified publication timestamps. Do not
describe a rebuild from revised archives as a point-in-time reconstruction.
Numerical science outputs are not rebuilt by `build_fallbacks`.

Use a contact email in the scraper User-Agent. One request at a time and
the existing request delay are part of the collection protocol. Non-404
HTTP failures and unresolved PDF extracts stop the workflow.

## 6. House rules
- `DECISIONS.md` is the lab notebook: every methodological choice, dated,
  before use. Read it before changing anything.
- `pipeline/score`, `pipeline/market`, `pipeline/predict` and the lexicon
  are the frozen science layer. Changes need explicit author approval and
  a dated, forward-only methodology entry; never silently replace v1.
- Files under `data/predictions/lock-*` are never modified once written.
- New prediction names cannot overwrite existing files. Only the documented
  outcome-scoring workflow may add realised outcomes and scores.
- GitHub Pages publishes from `main`. Local changes are not live until an
  authorised push; do not mistake a local preview for a deployment.
