"""Runs the full headline inference (Spec 3 OLS + Spec 2 ordered-logit LR
test, full sample and a Sep 2023-present fragility check) and writes
data/inference_v1.json. See pipeline/inference.py and DECISIONS.md
(2026-07-11) for every modelling choice.

Published v1 results. Re-running fits is a research update, not a site build.

Run:  python -m pipeline.build_inference
"""
import json
from pathlib import Path

from pipeline.inference import (
    NEWEY_WEST_MAXLAGS,
    load_surprises_with_lags,
    spec2_ordered_logit_lr_test,
    spec3_surprise_on_lagged_index,
    spec3_surprise_on_lagged_index_and_skew,
)
from pipeline.ladder import load_records

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "inference_v1.json"
FRAGILITY_SUBSAMPLE_START = "2023-09-01"


def run_specs(rows: list[dict], records: list[dict]) -> dict:
    return {
        "n": len(rows),
        "spec3_surprise_on_lagged_index": spec3_surprise_on_lagged_index(rows),
        "spec3_surprise_on_lagged_index_and_skew": spec3_surprise_on_lagged_index_and_skew(rows),
        "spec2_ordered_logit_lr_test": spec2_ordered_logit_lr_test(rows, records),
    }


def result_notes(full_sample: dict, fragility: dict) -> str:
    convergence = fragility["spec2_ordered_logit_lr_test"]["converged"]
    status = "converged" if convergence else "did not converge; its LR test is not computed"
    return (
        f"Published specifications on {full_sample['n']} scheduled meetings (full sample) / "
        f"{fragility['n']} (later subsample). Lagged index and skew use the previous meeting, "
        "as in ladder L3. The later subsample overlaps the full sample and is not an "
        f"independent replication. Its ordered-logit fit {status}. See DECISIONS.md "
        "2026-07-11 and the interpretation correction dated 2026-10-10."
    )


def main() -> None:
    rows = load_surprises_with_lags()
    records = load_records()

    full_sample = run_specs(rows, records)

    fragility_rows = [r for r in rows if r["date"] >= FRAGILITY_SUBSAMPLE_START]
    fragility = run_specs(fragility_rows, records)

    payload = {
        "schema": "inference-v1",
        "newey_west_maxlags": NEWEY_WEST_MAXLAGS,
        "full_sample": full_sample,
        "fragility_check_subsample": {
            "start_date": FRAGILITY_SUBSAMPLE_START,
            "results": fragility,
        },
        "notes": result_notes(full_sample, fragility),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"wrote {OUT}")
    fs3 = full_sample["spec3_surprise_on_lagged_index"]["coefficients"]["lagged_index"]
    print(f"\nFull sample (n={full_sample['n']}): Spec 3 lagged_index coef={fs3['coef']} t={fs3['t']} p={fs3['p']}")
    lr = full_sample["spec2_ordered_logit_lr_test"]
    print(f"Full sample: Spec 2 LR={lr.get('lr_statistic')} p={lr.get('p_value')} (converged={lr.get('converged')})")

    frag3 = fragility["spec3_surprise_on_lagged_index"]["coefficients"]["lagged_index"]
    print(f"\nFragility subsample (n={fragility['n']}, from {FRAGILITY_SUBSAMPLE_START}): "
          f"Spec 3 lagged_index coef={frag3['coef']} t={frag3['t']} p={frag3['p']}")
    frag_lr = fragility["spec2_ordered_logit_lr_test"]
    print(f"Fragility subsample: Spec 2 converged={frag_lr.get('converged')} "
          f"({frag_lr.get('note', 'ok')})")


if __name__ == "__main__":
    main()
