# LOCKDAY 2026-11 — November runbook

Prepared 2 November 2026, following `LOCKDAY-2026-09.md` and `LOCKDAY.md`.
Lock **3 November 2026**; announcement **5 November 2026, 12:00 GMT**.
Read CLAUDE.md and DECISIONS.md first. Use `.venv/bin/python`. Stop on failed
checks; no force, overwrite, freshness bypass or retagging. Science is frozen.
Never change the July or September lock files.

## Differences from September

- Announcement-minus-two returns (3 November); September's minus-one CPI
  exception and 07:00 BST constraint do not carry forward. Times are GMT/UTC.
- September minutes are ingested: today's rehearsal reads 1.3333, trailing
  four-document mean 1.1786 including September. Recheck tomorrow; do not
  reuse September's July reading or rationale.
- Risk-management series deferred to February 2027; retain v1. No new series
  or draft DM analysis is authorised by this runbook.
- PREDICTION_FILE is now derived from a generated card attribute, not a
  hardcoded path. The stamp now includes episodes.html, too.
- October guards require safe names, exclusive creation, a future meeting
  and no future-dated curve. Use non-lock names for rehearsals from the outset.
- Pages empty-trigger fallback below includes its own stamp to keep CI green.

## 1. Pre-flight on 3 November

Inspect local work and synchronise without rewriting history:

```bash
git status --short
git pull --ff-only
git log --oneline origin/main..HEAD
```

Preparation records and their stamp must be committed and pushed before the
lock commit. Run the full suite and stop on failure:

```bash
.venv/bin/python -m pytest -q
```

## 2. Fresh curve check

Fetch inputs and report curve/SONIA dates, first four maturity nodes, the
meeting-plus-three maturity and m0 cut/hold/hike before choosing the call:

```bash
.venv/bin/python - <<'PY'
import datetime as dt
from pipeline.market.ois import latest_forward_curve, latest_sonia
from pipeline.predict.lock import assert_curve_is_fresh, index_stats
from pipeline.predict.market_probs import months_between, market_probs_for_meeting
c = latest_forward_curve(); s = latest_sonia()
assert_curve_is_fresh(c['as_of_date'])
a = dt.date.fromisoformat(c['as_of_date'])
print('curve', a, '| sonia', s)
for m, r in list(zip(c['maturities_months'], c['forward_rates_pct']))[:4]:
    print(m, 'months ->', a + dt.timedelta(days=round(m*30.436875)), r)
print('meeting+3 months:', months_between(a, dt.date(2026, 11, 8)))
print(market_probs_for_meeting(c, s, dt.date(2026, 11, 5)))
print(index_stats())
PY
```

Confirm whether the read clips below the first node. This is an OIS-based
proxy, not a meeting-specific distribution; reference dates do not establish
publication availability. Wait for Jake's point call, exact rationale,
shaded decision probabilities and vote-split distribution. Do not choose them
or copy September's distribution. Record any prospective distributions in a
dated records commit, stamp and push it before the lock, as in September.

## 3. Write the lock once

Create the actual November file with the exact positional command:

```bash
.venv/bin/python -m pipeline.predict.lock 2026-11-05 lock-2026-11
```

Check the JSON against the fresh inputs. Fill only Jake's `point_call` and
`rationale`, exactly as supplied; preserve m0, hashes, timestamp, outcome and
scores. Validate and show the complete file, then **wait for Jake's go**:

```bash
.venv/bin/python -m json.tool data/predictions/lock-2026-11.json
```

## 4. PREDICTION_FILE edit and generated surfaces

Regenerate the card and record rather than hand-editing generated markup:

```bash
.venv/bin/python -m pipeline.build_track_record
.venv/bin/python -m pipeline.build_fallbacks
```

The required PREDICTION_FILE edit is generated: verify the card now carries
`data-prediction-file="data/predictions/lock-2026-11.json"`. JavaScript remains
`const PREDICTION_FILE = document.getElementById('call-card').dataset.predictionFile;`.
The newest-lock rule ignores rehearsals. Check locked styling, exact rationale,
probabilities and pending outcome in both the static and scripted card.

Check tests and review the diff; the two old lock diffs must be empty:

```bash
.venv/bin/python -m pytest -q
git diff --check
git diff -- data/predictions/lock-2026-07.json data/predictions/lock-2026-09.json
git status --short
git diff
```

## 5. Commit, tag, stamp, push

Stage only reviewed changes and tag the lock content commit before stamping:

```bash
git add data/predictions/lock-2026-11.json data/track_record.json index.html methodology.html episodes.html README.md
git commit -m "Lock call for 5 November 2026"
git tag -a lock-2026-11 -m "Pre-registered call: 5 November 2026 MPC"
```

Every content commit needs a separate stamp commit. Include all three HTML
pages; push both commits and the annotated tag together:

```bash
.venv/bin/python -m pipeline.build_build_info
git add data/build_info.json index.html methodology.html episodes.html
git commit -m "Last-updated stamp for the November lock"
.venv/bin/python -m pytest -q
git push origin main --follow-tags
```

Never push a bare content commit. Finish on 3 November; the tag must be
public before 5 November 12:00 GMT. Never move it onto the stamp commit.

## 6. Verify and Pages fallback

Check timestamp, tagged JSON and both tests and Pages runs:

```bash
git log -1 --format=%cI lock-2026-11
git show lock-2026-11:data/predictions/lock-2026-11.json
gh run list --limit 10
```

Hard-refresh https://jakefoulkes1.github.io/mpc-communication-index/ and
verify November's locked card, exact approved rationale, probabilities,
track-record row and stamp. Compare the public JSON with the tag. The old
root https://jakefoulkes1.github.io/mpc-index/ should meta-refresh to the new
site; deep paths are not promised.

If after about five minutes tests ran but **no Pages deployment** was created,
use July's empty-commit fallback, then stamp it too. Do not move the lock tag:

```bash
git commit --allow-empty -m "Trigger Pages rebuild"
.venv/bin/python -m pipeline.build_build_info
git add data/build_info.json index.html methodology.html episodes.html
git commit -m "Last-updated stamp for Pages trigger"
.venv/bin/python -m pytest -q
git push origin main
gh run list --limit 10
```

Report the tag timestamp, m0, Jake's distributions, live checks and deviations.
Outcome scoring is a separate post-announcement task.
