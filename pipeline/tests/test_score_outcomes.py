import pytest

from pipeline.predict.score_outcomes import brier_score, fill_outcome, log_score

PERFECT_HIKE = {"p_hike": 1.0, "p_hold": 0.0, "p_cut": 0.0}
UNIFORM = {"p_hike": 1 / 3, "p_hold": 1 / 3, "p_cut": 1 / 3}


def test_brier_score_perfect_forecast_is_zero():
    assert brier_score(PERFECT_HIKE, "hike") == 0.0


def test_brier_score_worst_forecast_is_two():
    assert brier_score(PERFECT_HIKE, "cut") == pytest.approx(2.0)


def test_log_score_perfect_forecast_is_zero():
    assert log_score(PERFECT_HIKE, "hike") == pytest.approx(0.0, abs=1e-8)


def test_log_score_penalises_confident_wrong_call():
    assert log_score(PERFECT_HIKE, "cut") > log_score(UNIFORM, "cut")


def test_fill_outcome_rejects_bad_outcome():
    with pytest.raises(ValueError):
        fill_outcome({"m0_market_only": PERFECT_HIKE}, "sideways")


def test_fill_outcome_scores_both_forecasts():
    payload = {"m0_market_only": {"p_hike": 0.6, "p_hold": 0.4, "p_cut": 0.0}}
    result = fill_outcome(payload, "hike")
    assert result["outcome"] == "hike"
    assert "m0_market_only" in result["scores"]
    assert "always_hold_reference" in result["scores"]
    # m0 gave hike more weight than the always-hold reference did, so it
    # should score better (lower Brier) when hike is the actual outcome.
    assert result["scores"]["m0_market_only"]["brier_score"] < result["scores"]["always_hold_reference"]["brier_score"]


def test_existing_scores_are_idempotent_and_cannot_be_replaced():
    payload = fill_outcome({"m0_market_only": PERFECT_HIKE}, "hold")
    assert fill_outcome(payload, "hold") == payload
    with pytest.raises(ValueError, match="do not overwrite"):
        fill_outcome(payload, "hike")
    assert payload["outcome"] == "hold"


def test_rescoring_does_not_rewrite_file(tmp_path, monkeypatch):
    import json
    from pipeline.predict import score_outcomes

    path = tmp_path / "lock.json"
    original = json.dumps(fill_outcome({"m0_market_only": PERFECT_HIKE}, "hold"))
    path.write_text(original)
    monkeypatch.setattr(score_outcomes.sys, "argv", ["score", str(path), "hold"])
    score_outcomes.main()
    assert path.read_text() == original


@pytest.mark.parametrize("probs", [
    {"p_hike": float('nan'), "p_hold": 1, "p_cut": 0},
    {"p_hike": 1.1, "p_hold": -0.1, "p_cut": 0},
    {"p_hike": 0.4, "p_hold": 0.4, "p_cut": 0},
])
def test_invalid_probabilities_cannot_be_scored(probs):
    for score in [brier_score, log_score]:
        with pytest.raises(ValueError, match="HARD STOP"):
            score(probs, "hold")


def test_scoring_rejects_unrecognised_outcome():
    for score in [brier_score, log_score]:
        with pytest.raises(ValueError, match="outcome"):
            score(PERFECT_HIKE, "sideways")
