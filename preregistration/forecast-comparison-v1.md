# Diebold-Mariano Forecast Comparison: Analysis Plan v1

**Status: DRAFT - pending author approval; not registered and not run.**
Prepared 12 October 2026. Intended for review and registration before the
3 November 2026 lock, with registration preceding all calculations below.
The choices in this draft are proposals, not an amendment to the v1 models.

## Question and Scope

Do the fixed historical forecast sequences have different average Brier losses
from the OIS-based proxy? This compares forecasts, not structural models or
causal effects. L3 adds tone and vote skew jointly; it does not isolate tone.
L4 uses votes, not tone.

The historical forecasts, outcomes and mean losses have already been published
and inspected. Registration before calculating these test statistics cannot
turn those observations into unseen data. This is a retrospective robustness
analysis, not a new prospective confirmation. It does not resolve the proxy's
first-node clipping, vintage-availability, roster or model-fallback limitations.

## Frozen Inputs

- Repository snapshot: `225f3bf16fbf36edd0ec81eab820c30cca301579`.
- File: `data/ladder_v1.json` from that snapshot, not a later regenerated file.
- SHA-256: `946c119655677d9280b9ff7ce61db16fb67fc67a87b3f37905b88e159c9ddde2`.
- Use every `per_meeting` record with `scheduled == true`, in date order.
  The fixed sample is 62 scheduled meetings from 7 February 2019 through
  17 September 2026. Validate the count and dates before analysis.
- Retain all recorded fallbacks to L1, including their zero loss differences.
  Do not refit models, rebuild the market benchmark, change probabilities,
  tune a dictionary or drop inconvenient meetings.
- The two special meetings are outside this inference sample. Keep their
  published descriptive scores separate; do not run a test on two observations.

If validation fails, stop and publish the reason. No substitution, imputation,
post hoc exclusion or silent change of sample is permitted.

## Comparisons and Loss

The fixed family contains three comparisons: L2 minus L1, L3 minus L1 and
L4 minus L1. L0 and any future risk-management model are not in this family.

Use each record's probabilities and actual class, not rounded headline means.
For classes `cut`, `hold`, `hike`, compute the existing summed Brier loss:

```text
Brier(model, t) = sum_c (p(model, t, c) - 1{actual_t = c})^2
d(model, t) = Brier(model, t) - Brier(L1, t)
```

Positive mean `d` means the competitor is worse. For each comparison, the null
is `E[d] = 0`; the alternative is two-sided. Do not select the tail from the
observed sign. The horizon is one next scheduled decision, not a fixed number
of calendar days.

## Inference Rules

Primary inference uses a Diebold-Mariano-style asymptotic statistic with a
Bartlett/Newey-West estimate of the long-run variance of the loss difference.
The proposed bandwidth is fixed at four scheduled-meeting lags, matching the
existing inference module's lag count but applied here to a different series.
It is not selected from the observed loss autocorrelations.

For `n` differences and their sample mean `dbar`:

```text
gamma(k) = sum_{t=k+1..n} (d_t-dbar)(d_{t-k}-dbar) / n
LRV = gamma(0) + 2 * sum_{k=1..4} (1-k/5) * gamma(k)
SE(dbar) = sqrt(LRV/n)
DM = dbar / SE(dbar)
p = 2 * (1 - Phi(abs(DM)))
```

Use the standard-normal reference distribution; no unreported small-sample
correction, degrees-of-freedom adjustment or data-driven bandwidth is applied.
Report the mean difference, long-run variance, standard error, statistic,
raw p-value and marginal normal-reference 95% interval for each comparison.
Those intervals are not simultaneous family-wise intervals.

For the three primary p-values, apply Holm's step-down adjustment at family-wise
alpha 0.05. Sort the three raw p-values ascending; multiply them by 3, 2, 1,
take running maxima, cap at 1 and restore the original comparison order.
Report raw and adjusted values together. No claim of a significant primary
difference is based on an unadjusted p-value alone.

Publish bandwidths 0, 1 and 8 as labelled exploratory sensitivity analyses,
alongside the primary bandwidth 4, for all three comparisons. They do not
replace the primary analysis or create additional confirmatory claims.
No sample split, alternative loss or bootstrap test is added in v1.

If a loss is invalid, the sample is insufficient for the specified lag, or the
long-run variance is non-finite or non-positive, return an explicit undefined
result for that comparison. Never replace its variance by an epsilon. For
the primary Holm family, assign such a comparison p=1 for adjustment only,
while keeping its reported test statistic and raw p-value null with a reason.

## Interpretation and Release

The normal approximation and stable, weakly dependent loss-difference
assumptions may be poor in this small, changing-policy sample. Expanding-window
estimation and frequent identical fallback forecasts require particular care.
A nonsignificant result does not establish equivalence or calibration, and a
significant result does not validate a text-only mechanism or a tradable signal.

After approval, record the date in DECISIONS and push an immutable
`prereg-dm-v1` tag pointing to this plan before computing losses or test
statistics. Preserve the tagged draft/review history. Any later change requires
a new dated version before rerunning, not an edit to the registered version.

The implementation must write separate versioned output, never overwrite
`data/ladder_v1.json`, `data/inference_v1.json` or any locked call. Publish all
comparisons, sensitivity results, undefined cases, the input hash, code commit,
run time and software versions regardless of their signs or p-values. Do not
append later meetings to this frozen analysis under the same registration.

## Sources

- [Diebold and Mariano (1995)](https://doi.org/10.1080/07350015.1995.10524599).
- [Diebold: use and abuse of DM tests](https://economics.sas.upenn.edu/sites/default/files/filevault/12-035.pdf).
- [Holm (1979)](https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf).
