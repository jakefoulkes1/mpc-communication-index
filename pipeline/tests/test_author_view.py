"""The current view and the forecast record agree with the locked files.

data/author_view.json is kept by hand. These tests make sure what it says
cannot drift from the locked calls it summarises: the meeting, the call, the
vote forecast, the outcome word and the scores the author worked out by hand.
Locked files are only read here, never changed.
"""
import json
import re
from pathlib import Path

import pytest

from pipeline.predict.score_outcomes import brier_score

ROOT = Path(__file__).resolve().parents[2]
VIEW = json.loads((ROOT / "data" / "author_view.json").read_text())
LOCKS = {
    f.stem: json.loads(f.read_text())
    for f in sorted((ROOT / "data" / "predictions").glob("lock-*.json"))
}
NEWEST = LOCKS[sorted(LOCKS)[-1]]


def test_current_view_is_about_the_newest_locked_call():
    assert VIEW["current"]["meeting"] == NEWEST["meeting_announcement"]


def test_current_view_matches_the_locked_rationale():
    cur = VIEW["current"]
    assert cur["vote_forecast"] in NEWEST["rationale"]
    assert cur["call"].split()[-1] in NEWEST["rationale"]
    assert len(cur["reasons"]) == 3


def test_current_probability_is_a_distribution_and_matches_the_stated_hike_figure():
    p = VIEW["current"]["my_probability"]
    assert abs(sum(p.values()) - 1) < 1e-9
    assert f"{p['hike'] * 100:.2f}%" in NEWEST["rationale"]


def test_every_locked_call_has_a_record_row():
    mine = {r["meeting"] for r in VIEW["record"]}
    assert mine == {lock["meeting_announcement"] for lock in LOCKS.values()}


@pytest.mark.parametrize("row", VIEW["record"], ids=lambda r: r["meeting"])
def test_record_result_agrees_with_the_locked_outcome(row):
    lock = next(v for v in LOCKS.values() if v["meeting_announcement"] == row["meeting"])
    if lock["outcome"] is None:
        assert row["result"] is None
    else:
        assert row["result"].lower().startswith(lock["outcome"])


def test_hand_scored_september_brier_recomputes():
    row = next(r for r in VIEW["record"] if r["meeting"] == "2026-09-17")
    probs = {"p_cut": 0.0, "p_hold": 1 - row["my_hike"], "p_hike": row["my_hike"]}
    assert round(brier_score(probs, "hold"), 4) == row["my_brier"]


def test_page_shows_the_current_view_before_the_evidence():
    html = (ROOT / "index.html").read_text()
    assert html.index('id="current-view"') < html.index('id="summary"')
    assert html.index('id="about"') < html.index('id="current-view"')
    block = re.search(r'id="current-view".*?</section>', html, re.S).group(0)
    assert VIEW["current"]["vote_forecast"] in block
    assert "read the original locked rationale" in block


def test_locked_rationale_appears_unchanged_on_the_page():
    html = (ROOT / "index.html").read_text()
    first_paragraph = NEWEST["rationale"].split("\n\n")[1]
    # The page writes typographic characters as entities, so compare on plain text.
    plain = re.sub(r"<[^>]+>", "", html).replace("&minus;", "−")
    assert first_paragraph[:120] in plain


@pytest.mark.parametrize("sheet", ["site/site.css", "site/dashboard.css"])
def test_font_sizes_are_relative(sheet):
    css = (ROOT / sheet).read_text()
    assert not re.search(r"font-size:\s*[0-9.]+px", css), (
        f"{sheet} sets a fixed pixel font size, so browser text-size settings would not apply"
    )
